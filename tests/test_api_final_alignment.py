"""Final alignment routes retain verified actors, strict bodies and SQL authority."""

from dataclasses import replace
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID
from test_api_season_admin import FakeRepository as AdminRepo, SID as ADMIN_SID
from test_api_matchdays import FakeRepository as DaysRepo, SID as DAY_SID, DID
from test_api_season_lifecycle import FakeLifecycle, SID
from test_api_championship import review


class FinalAlignmentApiTests(unittest.TestCase):
    def setUp(self):
        self.admin, self.days, self.life = AdminRepo(), DaysRepo(), FakeLifecycle()
        self.principals = FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    season_admin_repository=self.admin,
                    matchday_repository=self.days,
                    season_lifecycle_repository=self.life,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.headers = {
            "Authorization": "Bearer validated",
            "Idempotency-Key": "final-key",
        }

    def test_rules_current_zero_strict_write_scope_and_admin_only(self):
        path = f"/v1/admin/seasons/{ADMIN_SID}/rules"
        self.admin.response = dict(
            season_id=ADMIN_SID,
            revision=0,
            config_revision=3,
            badge_reward_coins=0,
            game_completion_reward_coins=12,
            effective_at=None,
            editable=True,
        )
        self.assertEqual(
            self.client.get(path, headers=self.headers).json()["badge_reward_coins"], 0
        )
        self.admin.response["season_id"] = str(uuid4())
        self.assertEqual(self.client.get(path, headers=self.headers).status_code, 503)
        self.admin.response = AdminRepo().response
        body = dict(
            expected_revision=0,
            expected_config_revision=3,
            badge_reward_coins=5,
            game_completion_reward_coins=12,
        )
        self.assertEqual(
            self.client.put(path, headers=self.headers, json=body).status_code, 200
        )
        self.assertEqual(self.admin.calls[-1][1]["actor_trainer_id"], TRAINER_ID)
        for bad in (True, "5", -1, 0.2, 2147483648):
            self.assertEqual(
                self.client.put(
                    path, headers=self.headers, json=dict(body, badge_reward_coins=bad)
                ).status_code,
                422,
            )
        for extra in ("effective_at", "actor_trainer_id", "total_matchdays"):
            self.assertEqual(
                self.client.put(
                    path, headers=self.headers, json=dict(body, **{extra: "forged"})
                ).status_code,
                422,
            )
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.assertEqual(self.client.get(path, headers=self.headers).status_code, 403)
        self.assertEqual(
            self.client.put(path, headers=self.headers, json=body).status_code, 403
        )

    def test_participant_normal_operations_use_verified_actor_and_sql_eligibility(self):
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        base = f"/v1/seasons/{DAY_SID}/matchdays/{DID}"
        for op, body, state in [
            ("open", {"expected_revision": 0}, "open"),
            ("close", {"expected_results_revision": 1}, "closed"),
        ]:
            self.days.response["state"] = state
            response = self.client.post(
                base + "/" + op, headers=self.headers, json=body
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.days.calls[-1][1]["actor_trainer_id"], TRAINER_ID)
            self.assertEqual(
                self.client.post(base + "/" + op, json=body).status_code, 401
            )
            self.assertEqual(
                self.client.post(
                    base + "/" + op,
                    headers=self.headers,
                    json=dict(body, actor_trainer_id=str(uuid4())),
                ).status_code,
                422,
            )
        self.assertEqual(
            self.client.post(
                base + "/close",
                headers=self.headers,
                json={"expected_results_revision": 1, "tie_resolution": {}},
            ).status_code,
            422,
        )
        for code in (
            "PARTICIPANT_REQUIRED",
            "PARTICIPANT_INACTIVE",
            "PARTICIPANT_INELIGIBLE",
        ):
            self.days.failure = SeasonAdminRejected(code, 403)
            self.assertEqual(
                self.client.post(
                    base + "/open", headers=self.headers, json={"expected_revision": 0}
                ).status_code,
                403,
            )

    def test_participant_review_finish_and_exceptional_boundary(self):
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        base = f"/v1/seasons/{SID}"
        self.life.response = review()
        self.assertEqual(
            self.client.get(base + "/championship", headers=self.headers).status_code,
            200,
        )
        self.life.response = FakeLifecycle().response
        self.assertEqual(
            self.client.post(
                base + "/finish",
                headers=self.headers,
                json={"expected_revision": 9, "input_hash": "a" * 64},
            ).status_code,
            200,
        )
        self.assertEqual(self.life.calls[-1][1]["actor_trainer_id"], TRAINER_ID)
        for op in ("championship/residual", "championship/bo3"):
            self.assertEqual(
                self.client.post(
                    f"/v1/admin/seasons/{SID}/" + op,
                    headers=self.headers,
                    json={
                        "expected_revision": 9,
                        "input_hash": "a" * 64,
                        "winner_season_player_id": str(uuid4()),
                        "reason": "External",
                    },
                ).status_code,
                403,
            )

    def test_residual_strict_audited_contract_and_source_candidates(self):
        data = review()
        data["players"].append(
            dict(
                data["players"][0],
                season_player_id=str(uuid4()),
                trainer_id=str(uuid4()),
            )
        )
        data.update(
            state="residual_required",
            champion_trainer_id=None,
            resolution_type=None,
            tied_player_ids=[p["season_player_id"] for p in data["players"]],
        )
        self.life.response = data
        path = f"/v1/admin/seasons/{SID}/championship"
        self.assertEqual(self.client.get(path, headers=self.headers).status_code, 200)
        self.life.response = dict(
            FakeLifecycle().response, operation="championship_residual", state="active"
        )
        body = dict(
            expected_revision=9,
            input_hash="a" * 64,
            winner_season_player_id=data["tied_player_ids"][1],
            reason="External decision",
        )
        self.assertEqual(
            self.client.post(
                path + "/residual", headers=self.headers, json=body
            ).status_code,
            200,
        )
        self.assertEqual(self.life.calls[-1][0], "championship_residual")
        for bad in ("", "  ", "x" * 501):
            self.assertEqual(
                self.client.post(
                    path + "/residual",
                    headers=self.headers,
                    json=dict(body, reason=bad),
                ).status_code,
                422,
            )
