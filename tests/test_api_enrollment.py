"""080 HTTP authorization, strict previews and the transactional RPC boundary."""

import unittest
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.repositories.supabase.season_admin import (
    SeasonAdminRejected,
    SupabaseSeasonAdminRepository,
)

SID, TID, PID, DAY = (str(uuid4()) for _ in range(4))
HASH = "a" * 64
PREVIEW = {
    "season_id": SID,
    "season_name": "ChampionsLocke",
    "eligible_trainers": [{"id": TID, "display_name": "Elena"}],
    "first_matchday_number": 2,
    "matchday_id": DAY,
    "matchday_status": "open",
    "closed_matchdays": 1,
    "initial_coins": 10,
    "initial_points": "0",
    "new_matchups": 5,
    "preview_hash": HASH,
}
RECEIPT = {
    "operation_id": str(uuid4()),
    "resource_id": PID,
    "season_id": SID,
    "event_id": str(uuid4()),
    "replayed": False,
    "state": "active",
    "setup_revision": 7,
    "roster_revision": 6,
    "config_revision": 1,
}


class Repository:
    def __init__(self):
        self.calls = []
        self.preview = deepcopy(PREVIEW)
        self.failure = None

    def execute(self, operation, request):
        self.calls.append((operation, request))
        if self.failure:
            raise self.failure
        return deepcopy(self.preview if operation == "enrollment_preview" else RECEIPT)


class EnrollmentApiTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.principals = Repository(), FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    season_admin_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.path = f"/v1/admin/seasons/{SID}/enrollment"
        self.headers = {"Authorization": "Bearer x", "Idempotency-Key": "enroll-1"}

    def confirm(self, body=None, headers=None):
        return self.client.post(
            self.path,
            headers=self.headers if headers is None else headers,
            json=body
            if body is not None
            else {"trainer_id": TID, "preview_hash": HASH},
        )

    def test_anonymous_and_non_admin_cannot_read_or_enroll(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.assertEqual(self.confirm(headers={}).status_code, 401)
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.assertEqual(
            self.client.get(self.path, headers=self.headers).status_code, 403
        )
        self.assertEqual(self.confirm().status_code, 403)
        self.assertEqual(self.repo.calls, [])

    def test_preview_and_confirmation_forward_only_authenticated_authority(self):
        preview = self.client.get(self.path, headers=self.headers)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json(), PREVIEW)
        confirmed = self.confirm()
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(
            self.repo.calls,
            [
                (
                    "enrollment_preview",
                    {"actor_trainer_id": TRAINER_ID, "season_id": SID},
                ),
                (
                    "enrollment_confirm",
                    {
                        "actor_trainer_id": TRAINER_ID,
                        "season_id": SID,
                        "idempotency_key": "enroll-1",
                        "body": {"trainer_id": TID, "preview_hash": HASH},
                    },
                ),
            ],
        )

    def test_no_arbitrary_coins_points_or_identity_and_key_required(self):
        for extra in (
            "initial_coins",
            "initial_points",
            "first_matchday_number",
            "is_admin",
            "actor_trainer_id",
        ):
            with self.subTest(extra=extra):
                self.assertEqual(
                    self.confirm(
                        dict(trainer_id=TID, preview_hash=HASH, **{extra: 99})
                    ).status_code,
                    422,
                )
        self.assertEqual(
            self.confirm(headers={"Authorization": "Bearer x"}).status_code, 422
        )
        for body in (
            {"trainer_id": "invalid", "preview_hash": HASH},
            {"trainer_id": TID, "preview_hash": "old"},
            {"trainer_id": TID, "preview_hash": True},
        ):
            self.assertEqual(self.confirm(body).status_code, 422)
        self.assertFalse(self.repo.calls)

    def test_foreign_inconsistent_or_private_preview_answers_fail_closed(self):
        for changes in (
            {"season_id": str(uuid4())},
            {"initial_points": "10"},
            {"initial_coins": -1},
            {"closed_matchdays": 0},
            {"matchday_id": None},
            {"eligible_trainers": PREVIEW["eligible_trainers"] * 2},
            {"auth_user_id": "private"},
        ):
            with self.subTest(changes=changes):
                self.repo.preview = dict(PREVIEW, **changes)
                result = self.client.get(self.path, headers=self.headers)
                self.assertEqual(result.status_code, 503, result.text)
                self.assertNotIn("private", result.text)

    def test_sql_refusals_are_actionable_and_do_not_expose_database_details(self):
        for code in (
            "enrollment_preview_stale",
            "enrollment_not_supported",
            "enrollment_history_unproven",
            "enrollment_championship_closed",
            "participant_exists",
            "trainer_unavailable",
            "season_not_active",
        ):
            with self.subTest(code=code):
                self.repo.failure = SeasonAdminRejected(code.upper(), 409)
                result = self.confirm()
                self.assertEqual(result.status_code, 409)
                self.assertEqual(result.json()["detail"]["code"], code.upper())

    def test_each_operation_uses_the_same_atomic_service_rpc(self):
        calls = []
        client = SimpleNamespace(
            rpc=lambda name, params: (
                calls.append((name, params))
                or SimpleNamespace(execute=lambda: SimpleNamespace(data={}))
            )
        )
        repo = SupabaseSeasonAdminRepository(client)
        for operation, sql_op in (
            ("enrollment_preview", "preview"),
            ("enrollment_confirm", "confirm"),
        ):
            repo.execute(operation, {"actor_trainer_id": TRAINER_ID, "season_id": SID})
            self.assertEqual(
                calls[-1],
                (
                    "api_admin_league_enrollment",
                    {
                        "p_request": {
                            "operation": sql_op,
                            "request": {
                                "actor_trainer_id": TRAINER_ID,
                                "season_id": SID,
                            },
                        }
                    },
                ),
            )
