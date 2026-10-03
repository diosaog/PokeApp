from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.repositories.supabase.season_lifecycle import SupabaseSeasonLifecycleRepository
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID
from test_api_season_lifecycle import FakeLifecycle, SID


def review():
    return dict(
        season_id=SID,
        state="ready",
        setup_revision=9,
        input_hash="a" * 64,
        players=[
            dict(
                season_player_id=str(uuid4()),
                trainer_id=TRAINER_ID,
                display_name="Antonio",
                total_points="-1.250000000000000001",
                adjusted_deaths=3,
            )
        ],
        tied_player_ids=[],
        champion_trainer_id=TRAINER_ID,
        resolution_type="unique_points",
        finalist_status="OWNER_DECISION_REQUIRED",
        blocking_reason=None,
    )


class ChampionshipApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeLifecycle()
        self.principals = FakePrincipalRepository()
        self.tokens = FakeTokenVerifier()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=self.tokens,
                    principal_repository=self.principals,
                    season_lifecycle_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.path = f"/v1/admin/seasons/{SID}/championship"
        self.headers = {
            "Authorization": "Bearer validated",
            "Idempotency-Key": "title-key",
        }

    def test_read_authority_and_verified_scope(self):
        self.repo.response = review()
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.assertEqual(
            self.client.get(self.path, headers=self.headers).status_code, 403
        )
        self.assertFalse(self.repo.calls)
        self.principals.trainer = replace(self.principals.trainer, is_admin=True)
        response = self.client.get(self.path, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["players"][0]["total_points"], "-1.250000000000000001"
        )
        self.assertEqual(
            self.repo.calls,
            [("championship", dict(actor_trainer_id=TRAINER_ID, season_id=SID))],
        )

    def test_read_invalid_backend_scope_and_facts_fail_closed(self):
        base = review()
        changes = [
            dict(season_id=str(uuid4())),
            dict(champion_trainer_id=str(uuid4())),
            dict(tied_player_ids=[str(uuid4())]),
            dict(players=base["players"] * 2),
            dict(players=[dict(base["players"][0], total_points=1.25)]),
            dict(players=[dict(base["players"][0], total_points="NaN")]),
            dict(players=[dict(base["players"][0], adjusted_deaths=True)]),
            dict(players=[dict(base["players"][0], adjusted_deaths=-1)]),
            dict(state="ready", input_hash=None),
            dict(state="bo3_required"),
            dict(state="owner_decision_required"),
            dict(private_team_snapshot=["PRIVATE"]),
        ]
        for change in changes:
            with self.subTest(change=change):
                self.repo.response = dict(deepcopy(base), **change)
                response = self.client.get(self.path, headers=self.headers)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("PRIVATE", response.text)

    def test_unknown_adjusted_deaths_remain_null(self):
        self.repo.response = review()
        self.repo.response["players"][0]["adjusted_deaths"] = None
        response = self.client.get(self.path, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["players"][0]["adjusted_deaths"])

    def test_finish_digest_is_strict_but_archive_does_not_accept_it(self):
        base = f"/v1/admin/seasons/{SID}"
        for value in ("x", "A" * 64, 4):
            response = self.client.post(
                base + "/finish",
                headers=self.headers,
                json=dict(expected_revision=9, input_hash=value),
            )
            self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.post(
                base + "/archive",
                headers=self.headers,
                json=dict(expected_revision=9, input_hash="a" * 64),
            ).status_code,
            422,
        )
        self.assertFalse(self.repo.calls)

    def test_hashless_finish_only_replays_the_exact_successful_legacy_body(self):
        path = f"/v1/admin/seasons/{SID}/finish"
        self.repo.response["replayed"] = True
        for body in (
            dict(expected_revision=9),
            dict(expected_revision=9, input_hash=None),
        ):
            response = self.client.post(path, headers=self.headers, json=body)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["replayed"])
            self.assertEqual(self.repo.calls[-1][1]["body"], dict(expected_revision=9))
            self.assertEqual(self.repo.calls[-1][1]["idempotency_key"], "title-key")
        # A new hashless command reaches the authoritative SQL gate and is denied.
        self.repo.failure = SeasonAdminRejected("INVALID_REQUEST", 422)
        response = self.client.post(
            path, headers=self.headers, json=dict(expected_revision=9)
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_REQUEST")

    def test_bo3_strict_body_verified_actor_and_idempotency(self):
        winner = str(uuid4())
        body = dict(
            expected_revision=9,
            input_hash="a" * 64,
            winner_season_player_id=winner,
            reason="  Externally played 2-1  ",
        )
        self.repo.response.update(operation="championship_bo3", state="active")
        response = self.client.post(self.path + "/bo3", headers=self.headers, json=body)
        self.assertEqual(response.status_code, 200)
        op, request = self.repo.calls[-1]
        self.assertEqual(op, "championship_bo3")
        self.assertEqual(request["actor_trainer_id"], TRAINER_ID)
        self.assertEqual(request["idempotency_key"], "title-key")
        self.assertEqual(request["body"], dict(body, reason="Externally played 2-1"))
        self.repo.response["replayed"] = True
        self.assertTrue(
            self.client.post(
                self.path + "/bo3", headers=self.headers, json=body
            ).json()["replayed"]
        )
        self.assertEqual(self.repo.calls[-1], self.repo.calls[-2])
        for field, value in [
            ("reason", " "),
            ("reason", "x" * 501),
            ("winner_season_player_id", "bad"),
            ("expected_revision", True),
            ("input_hash", "short"),
            ("actor_trainer_id", TRAINER_ID),
            ("rankings", []),
        ]:
            with self.subTest(field=field):
                self.assertEqual(
                    self.client.post(
                        self.path + "/bo3",
                        headers=self.headers,
                        json=dict(body, **{field: value}),
                    ).status_code,
                    422,
                )
        self.assertEqual(
            self.client.post(
                self.path + "/bo3",
                headers={"Authorization": "Bearer validated"},
                json=body,
            ).status_code,
            422,
        )

    def test_bo3_rejects_non_admin_before_repository(self):
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        response = self.client.post(
            self.path + "/bo3",
            headers=self.headers,
            json=dict(
                expected_revision=9,
                input_hash="a" * 64,
                winner_season_player_id=str(uuid4()),
                reason="External BO3",
            ),
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.repo.calls)

    def test_bo3_receipt_cannot_claim_finish_or_hall(self):
        body = dict(
            expected_revision=9,
            input_hash="a" * 64,
            winner_season_player_id=str(uuid4()),
            reason="External BO3",
        )
        self.repo.response.update(operation="championship_bo3", state="finished")
        self.assertEqual(
            self.client.post(
                self.path + "/bo3", headers=self.headers, json=body
            ).status_code,
            503,
        )
        self.repo.response.update(state="active", hall_id=str(uuid4()))
        self.assertEqual(
            self.client.post(
                self.path + "/bo3", headers=self.headers, json=body
            ).status_code,
            503,
        )


class ChampionshipAdapterTests(unittest.TestCase):
    def test_read_uses_dedicated_read_rpc_without_operation_injection(self):
        client = Mock()
        client.rpc.return_value.execute.return_value.data = review()
        request = dict(actor_trainer_id=TRAINER_ID, season_id=SID)
        SupabaseSeasonLifecycleRepository(client).execute("championship", request)
        client.rpc.assert_called_once_with(
            "api_admin_championship_read", {"p_request": request}
        )

    def test_bo3_unknown_outcome_never_retries(self):
        client = Mock()
        client.rpc.return_value.execute.side_effect = Exception("PRIVATE")
        with self.assertRaises(PersistenceError):
            SupabaseSeasonLifecycleRepository(client).execute(
                "championship_bo3", {"season_id": SID}
            )
        self.assertEqual(client.rpc.call_count, 1)
