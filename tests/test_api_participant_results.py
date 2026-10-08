"""Verified identity/strict DTO/transport boundary for participant League results."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.repositories.supabase.matchdays import SupabaseMatchdayRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_matchdays import FakeRepository, SID, DID, MID
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID


class ParticipantResultApiTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.principals, self.tokens = (
            FakeRepository(),
            FakePrincipalRepository(),
            FakeTokenVerifier(),
        )
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=self.tokens,
                    principal_repository=self.principals,
                    matchday_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.base = f"/v1/seasons/{SID}/matchdays/{DID}"
        self.headers = {
            "Authorization": "Bearer validated",
            "Idempotency-Key": "participant-test",
        }
        self.body = dict(
            expected_results_revision=1,
            results=[dict(match_id=MID, winner_season_player_id=str(uuid4()))],
        )

    def put(self, **kw):
        return self.client.put(
            self.base + "/results",
            json=kw.get("body", self.body),
            headers=kw.get("headers", self.headers),
        )

    def test_anon_invalid_and_unmapped_identity(self):
        self.assertEqual(self.put(headers={}).status_code, 401)
        self.tokens.fail = InvalidSessionError()
        self.assertEqual(self.put().status_code, 401)
        self.tokens.fail = None
        self.principals.trainer = None
        self.assertEqual(self.put().status_code, 401)
        self.assertEqual(self.repo.calls, [])

    def test_disabled_identity_denied_before_sql(self):
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(self.put().status_code, 403)
        self.assertEqual(self.repo.calls, [])

    def test_non_admin_and_third_party_request_uses_verified_actor(self):
        self.assertEqual(self.put().status_code, 200)
        op, r = self.repo.calls[0]
        self.assertEqual(op, "participant_results")
        self.assertEqual(r["actor_trainer_id"], TRAINER_ID)
        self.assertNotEqual(
            r["body"]["results"][0]["winner_season_player_id"], TRAINER_ID
        )

    def test_authority_injection_and_missing_key_rejected(self):
        for name in ("actor_trainer_id", "is_admin", "season_id", "operation", "plan"):
            self.assertEqual(
                self.put(body=dict(self.body, **{name: TRAINER_ID})).status_code, 422
            )
        self.assertEqual(
            self.put(headers={"Authorization": "Bearer validated"}).status_code, 422
        )
        self.assertEqual(self.repo.calls, [])

    def test_strict_revision_clear_and_no_general_privileged_command(self):
        for value in (None, True, -1, "1", 1.5):
            self.assertEqual(
                self.put(
                    body=dict(self.body, expected_results_revision=value)
                ).status_code,
                422,
            )
        self.body["results"][0]["winner_season_player_id"] = None
        self.assertEqual(self.put().status_code, 200)
        for op in ("open", "close"):
            self.assertEqual(self.client.post(self.base + "/" + op, json=self.body, headers=self.headers).status_code, 422)
        for op in ("correct", "cancel-editing"):
            self.assertEqual(
                self.client.post(
                    self.base + "/" + op, json=self.body, headers=self.headers
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.post(
                f"/v1/admin/seasons/{SID}/matchdays/{DID}/correct",
                json={
                    "expected_snapshot_revision": 1,
                    "reason": "x",
                    "results": [dict(match_id=MID, winner_season_player_id=TRAINER_ID)],
                },
                headers=self.headers,
            ).status_code,
            403,
        )

    def test_read_whitelist_scope_and_explicit_rejections(self):
        self.repo.response.update(matches=[], private_payload="SECRET")
        response = self.client.get(self.base, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("SECRET", response.text)
        self.assertEqual(self.repo.calls[0][0], "participant_state")
        for code in (
            "PARTICIPANT_REQUIRED",
            "PARTICIPANT_INACTIVE",
            "PARTICIPANT_INELIGIBLE",
        ):
            self.repo.failure = SeasonAdminRejected(code, 403)
            self.assertEqual(self.put().json()["detail"]["code"], code)
        self.repo.failure = None
        self.repo.response["matchday_id"] = str(uuid4())
        self.assertEqual(self.put().status_code, 503)

    def test_adapter_routes_only_participant_operations_without_plan_or_retry(self):
        calls = []

        def rpc(name, args):
            calls.append((name, args))
            return SimpleNamespace(
                execute=lambda: SimpleNamespace(data={"replayed": True})
            )

        repo = SupabaseMatchdayRepository(SimpleNamespace(rpc=rpc))
        for op in ("participant_state", "participant_results"):
            self.assertTrue(
                repo.execute(op, {"actor_trainer_id": TRAINER_ID})["replayed"]
            )
        self.assertEqual([c[0] for c in calls], ["api_participant_matchday"] * 2)
        self.assertEqual(
            [c[1]["p_request"]["operation"] for c in calls], ["state", "results"]
        )
