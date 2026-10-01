"""Daily tie decisions stay behind real route/auth and adapter boundaries."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.daily_ranking import RankingDecisionRequired
from app.repositories.errors import PersistenceError
from app.repositories.supabase.matchdays import SupabaseMatchdayRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_matchdays import DID, MID, SID, FakeRepository
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID


PLAYERS = sorted(str(uuid4()) for _ in range(4))
DIGEST = "a" * 64


def review():
    return dict(
        input_hash=DIGEST,
        groups=[
            dict(
                division="A",
                player_ids=PLAYERS[:2],
                position=1,
                position_end=2,
                wins=2,
                adjusted_deaths=4,
                consequences=["podium", "points", "movement"],
            )
        ],
    )


def resolution():
    return dict(
        input_hash=DIGEST,
        orders=[
            dict(player_ids=list(reversed(PLAYERS[:2])), reason="Recorded decision")
        ],
    )


class DailyRankingApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepository()
        self.principals = FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    matchday_repository=self.repo,
                )
            )
        )
        self.addCleanup(self.client.close)
        self.base = f"/v1/admin/seasons/{SID}/matchdays/{DID}"
        self.headers = {
            "Authorization": "Bearer validated",
            "Idempotency-Key": "ranking-key",
        }

    def post(self, body=None, operation="close", headers=None):
        return self.client.post(
            self.base + "/" + operation,
            json=body if body is not None else {"expected_results_revision": 2},
            headers=self.headers if headers is None else headers,
        )

    def test_external_resolution_does_not_bypass_jwt_or_admin(self):
        body = dict(expected_results_revision=2, tie_resolution=resolution())
        self.assertEqual(
            self.post(body, headers={"Idempotency-Key": "key"}).status_code, 401
        )
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        denied = self.post(body)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["detail"]["code"], "ADMIN_REQUIRED")
        self.assertFalse(self.repo.calls)

    def test_preexisting_canonical_close_and_correction_bodies_are_preserved(self):
        bodies = (
            ("close", dict(expected_results_revision=2)),
            (
                "correct",
                dict(
                    expected_snapshot_revision=1,
                    reason="Review",
                    results=[dict(match_id=MID, winner_season_player_id=TRAINER_ID)],
                ),
            ),
        )
        for operation, body in bodies:
            with self.subTest(operation=operation):
                for extra in ({}, {"tie_resolution": None}):
                    self.assertEqual(
                        self.post(dict(body, **extra), operation).status_code, 200
                    )
                    self.assertEqual(self.repo.calls[-1][1]["body"], body)

    def test_null_winner_for_result_clearing_is_not_dropped(self):
        body = dict(
            expected_results_revision=2,
            results=[dict(match_id=MID, winner_season_player_id=None)],
        )
        response = self.client.put(
            self.base + "/results", json=body, headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.repo.calls[-1][1]["body"], body)

    def test_resolution_preserves_explicit_sporting_order_and_normalizes_reason(self):
        decision = resolution()
        decision["orders"][0]["reason"] = "  External match result  "
        response = self.post(dict(expected_results_revision=2, tie_resolution=decision))
        self.assertEqual(response.status_code, 200)
        sent = self.repo.calls[-1][1]
        self.assertEqual(sent["actor_trainer_id"], TRAINER_ID)
        self.assertEqual(
            sent["body"]["tie_resolution"]["orders"][0],
            dict(
                player_ids=list(reversed(PLAYERS[:2])), reason="External match result"
            ),
        )

    def test_group_order_is_canonical_but_member_order_is_not_sorted(self):
        decision = resolution()
        second = dict(player_ids=list(reversed(PLAYERS[2:])), reason="Second group")
        decision["orders"].insert(0, second)
        self.assertEqual(
            self.post(
                dict(expected_results_revision=2, tie_resolution=decision)
            ).status_code,
            200,
        )
        sent = self.repo.calls[-1][1]["body"]["tie_resolution"]["orders"]
        self.assertEqual(
            [set(item["player_ids"]) for item in sent],
            [set(PLAYERS[:2]), set(PLAYERS[2:])],
        )
        self.assertEqual(sent[1]["player_ids"], second["player_ids"])

    def test_strict_resolution_rejects_forged_authority_and_invalid_shape(self):
        variants = []
        for digest in ("short", "A" * 64, 123):
            item = resolution()
            item["input_hash"] = digest
            variants.append(item)
        for reason in ("", "  ", 123, "x" * 501):
            item = resolution()
            item["orders"][0]["reason"] = reason
            variants.append(item)
        for ids in ([PLAYERS[0]], [PLAYERS[0], PLAYERS[0]], [PLAYERS[0], "invalid"]):
            item = resolution()
            item["orders"][0]["player_ids"] = ids
            variants.append(item)
        for key in ("actor_trainer_id", "plan", "is_admin"):
            item = resolution()
            item[key] = TRAINER_ID
            variants.append(item)
            item = resolution()
            item["orders"][0][key] = TRAINER_ID
            variants.append(item)
        item = resolution()
        item["orders"] = []
        variants.append(item)
        for item in variants:
            with self.subTest(item=item):
                self.assertEqual(
                    self.post(
                        dict(expected_results_revision=2, tie_resolution=item)
                    ).status_code,
                    422,
                )
        self.assertFalse(self.repo.calls)

    def test_expected_conflicts_expose_only_whitelisted_review_facts(self):
        for code in (
            "RANKING_TIE_UNRESOLVED",
            "RANKING_REVIEW_STALE",
            "INVALID_TIE_RESOLUTION",
        ):
            with self.subTest(code=code):
                data = review()
                data.update(
                    auth_user_id="PRIVATE", frozen_inputs={"credential": "PRIVATE"}
                )
                data["groups"][0].update(
                    reason="PRIVATE", allocation_position=1, private_save="PRIVATE"
                )
                self.repo.failure = RankingDecisionRequired(code, data)
                result = self.post()
                self.assertEqual(result.status_code, 409)
                self.assertEqual(result.json()["detail"]["code"], code)
                self.assertEqual(result.json()["detail"]["ranking"], review())
                self.assertNotIn("PRIVATE", result.text)
                self.assertNotIn("allocation_position", result.text)
        self.assertEqual(len(self.repo.calls), 3)

    def test_malformed_review_and_unknown_error_code_fail_closed(self):
        cases = []
        data = review()
        data["groups"][0]["player_ids"] = ["PRIVATE"]
        cases.append(RankingDecisionRequired("RANKING_TIE_UNRESOLVED", data))
        cases.append(RankingDecisionRequired("PRIVATE_ERROR", review()))
        for failure in cases:
            with self.subTest(code=failure.code):
                self.repo.failure = failure
                result = self.post()
                self.assertEqual(result.status_code, 503)
                self.assertEqual(
                    result.json()["detail"]["code"], "MATCHDAY_UNAVAILABLE"
                )
                self.assertNotIn("PRIVATE", result.text)

    def test_openapi_describes_the_structured_review_on_close_and_correction(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for operation in ("close", "correct"):
            response = paths[
                f"/v1/admin/seasons/{{season_id}}/matchdays/{{day_id}}/{operation}"
            ]["post"]["responses"]["409"]
            self.assertEqual(
                response["content"]["application/json"]["schema"]["$ref"],
                "#/components/schemas/RankingErrorResponse",
            )


class DailyRankingAdapterTests(unittest.TestCase):
    def adapter(self, context, failure=None):
        calls = []

        def rpc(name, arguments):
            calls.append((name, deepcopy(arguments)))
            if name == "api_admin_matchday_context":
                data = context
            elif failure:
                raise failure
            else:
                data = {"replayed": False}
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))

        return SupabaseMatchdayRepository(SimpleNamespace(rpc=rpc)), calls

    def test_replay_bypasses_planner_even_after_inputs_or_resolution_change(self):
        receipt = dict(replayed=True, operation_id=str(uuid4()))
        repo, calls = self.adapter(dict(receipt=receipt))
        for operation in ("close", "correct"):
            with patch(
                "app.repositories.supabase.matchdays.plan_close",
                side_effect=AssertionError("Do not recalculate a receipt"),
            ):
                self.assertEqual(
                    repo.execute(
                        operation, dict(body={"tie_resolution": resolution()})
                    ),
                    receipt,
                )
        self.assertEqual(
            [call[0] for call in calls], ["api_admin_matchday_context"] * 2
        )

    def test_required_decision_stops_before_mutation_without_retry(self):
        repo, calls = self.adapter(dict(context={}, input_hash="database fingerprint"))
        failure = RankingDecisionRequired("RANKING_TIE_UNRESOLVED", review())
        with patch(
            "app.repositories.supabase.matchdays.plan_close", side_effect=failure
        ):
            with self.assertRaises(RankingDecisionRequired) as raised:
                repo.execute("close", dict(body=dict(expected_results_revision=2)))
        self.assertIs(raised.exception, failure)
        self.assertEqual([call[0] for call in calls], ["api_admin_matchday_context"])

    def test_resolution_goes_to_planner_but_database_fingerprint_stays_authoritative(
        self,
    ):
        context = {"inputs": {"source": "database"}}
        decision = resolution()
        changes = [dict(match_id=MID, winner_season_player_id=TRAINER_ID)]
        repo, calls = self.adapter(
            dict(context=context, input_hash="database fingerprint")
        )
        with patch(
            "app.repositories.supabase.matchdays.plan_close",
            return_value={"ranking": "safe plan"},
        ) as planner:
            repo.execute(
                "correct", dict(body=dict(results=changes, tie_resolution=decision))
            )
        planner.assert_called_once_with(context, changes, decision)
        sent = calls[1][1]["p_request"]
        self.assertEqual(sent["input_hash"], "database fingerprint")
        self.assertEqual(sent["plan"], {"ranking": "safe plan"})
        self.assertEqual(sent["request"]["body"]["tie_resolution"], decision)

    def test_commit_conflict_is_not_retried_or_silently_replanned(self):
        failure = RuntimeError("PRIVATE")
        failure.code, failure.message = "PT409", "stale_inputs"
        repo, calls = self.adapter(
            dict(context={}, input_hash="database fingerprint"), failure
        )
        with patch(
            "app.repositories.supabase.matchdays.plan_close", return_value={}
        ) as planner:
            with self.assertRaises(SeasonAdminRejected) as raised:
                repo.execute("close", dict(body=dict(tie_resolution=resolution())))
        self.assertEqual(raised.exception.code, "STALE_INPUTS")
        self.assertEqual(planner.call_count, 1)
        self.assertEqual(
            [call[0] for call in calls],
            ["api_admin_matchday_context", "api_admin_matchday"],
        )

    def test_corrupt_authoritative_inputs_do_not_become_a_resolution_request(self):
        repo, calls = self.adapter(dict(context={}, input_hash="database fingerprint"))
        with patch(
            "app.repositories.supabase.matchdays.plan_close",
            side_effect=ValueError("PRIVATE"),
        ):
            with self.assertRaises(PersistenceError) as raised:
                repo.execute("close", dict(body={}))
        self.assertNotIn("PRIVATE", str(raised.exception))
        self.assertEqual(len(calls), 1)
