"""Final-title transport is authenticated, explicit, exact and independent of points."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.season_lifecycle_models import ChampionshipRead, ChampionshipTiebreakBody
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.repositories.supabase.season_lifecycle import SupabaseSeasonLifecycleRepository
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID
from test_api_season_lifecycle import FakeLifecycle, SID


def tied_review():
    players = [dict(season_player_id=str(uuid4()), trainer_id=tid,
                    display_name=f"Trainer {index}", total_points="10.500000000000000001",
                    adjusted_deaths=penalty, actual_deaths=actual)
               for index, (tid, penalty, actual) in enumerate(
                   zip((TRAINER_ID, str(uuid4()), str(uuid4())), (20, 4, 7), (5, 3, 3)))]
    return dict(season_id=SID, state="tiebreak_required", setup_revision=9,
                input_hash="a" * 64, players=players,
                tied_player_ids=[p["season_player_id"] for p in players],
                champion_trainer_id=None, resolution_type=None, tiebreak_method=None,
                finalist_status="OWNER_DECISION_REQUIRED", blocking_reason=None)


class ChampionshipTiebreakApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeLifecycle()
        self.repo.response.update(operation="championship_tiebreak", state="active")
        self.principals = FakePrincipalRepository()
        self.client = TestClient(create_app(container=ApiContainer(
            token_verifier=FakeTokenVerifier(), principal_repository=self.principals,
            season_lifecycle_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.path = f"/v1/admin/seasons/{SID}/championship/tiebreak"
        self.headers = {"Authorization": "Bearer validated", "Idempotency-Key": "title-076"}
        self.body = dict(expected_revision=9, input_hash="a"*64, confirmation=True,
                         method="total_actual_deaths", reason="  Confirm the actual historical deaths  ")

    def post(self, body=None, headers=None):
        return self.client.post(self.path, json=self.body if body is None else body,
                                headers=self.headers if headers is None else headers)

    def battle_body(self):
        a, b, c = (str(uuid4()) for _ in range(3))
        return dict(self.body, method="championship_1v1", winner_season_player_id=a,
                    battles=[dict(player_a_id=a, player_b_id=b, winner_id=a,
                                  played_at="2026-01-01T12:00:00+02:00", evidence="Actual recorded final"),
                             dict(player_a_id=b, player_b_id=c, winner_id=b,
                                  played_at="2026-01-01T09:00:00Z", evidence="Actual earlier recorded result")])

    def test_authority_before_repository_and_no_participant_mutation_route(self):
        self.assertEqual(self.post(headers={"Idempotency-Key": "title-076"}).status_code, 401)
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.client.post(self.path.replace("/admin/", "/"),
                                         json=self.body, headers=self.headers).status_code, 404)
        self.assertFalse(self.repo.calls)
        self.principals.trainer = replace(self.principals.trainer, is_admin=True, globally_enabled=False)
        self.assertEqual(self.post().status_code, 403)
        self.assertFalse(self.repo.calls)

    def test_deaths_confirmation_binds_actor_scope_revision_hash_and_retry(self):
        self.assertEqual(self.post().status_code, 200)
        operation, request = self.repo.calls[-1]
        self.assertEqual(operation, "championship_tiebreak")
        self.assertEqual(request["actor_trainer_id"], TRAINER_ID)
        self.assertEqual(request["season_id"], SID)
        self.assertEqual(request["idempotency_key"], "title-076")
        self.assertEqual(request["body"], dict(self.body,
            reason="Confirm the actual historical deaths", winner_season_player_id=None, battles=None))
        self.repo.response["replayed"] = True
        self.assertTrue(self.post().json()["replayed"])
        self.assertEqual(self.repo.calls[-1], self.repo.calls[-2])

    def test_confirmation_and_command_fields_are_strict(self):
        for changes in (dict(confirmation=False), dict(confirmation=1), dict(confirmation="true"),
                        dict(expected_revision=True), dict(input_hash="A"*64), dict(method="bo3"),
                        dict(reason=" "), dict(reason="x"*501), dict(actor_trainer_id=TRAINER_ID),
                        dict(points_awarded=1), dict(dead_count=0), dict(round_robin_wins=99)):
            with self.subTest(changes=changes):
                self.assertEqual(self.post({**self.body, **changes}).status_code, 422)
        missing = dict(self.body)
        del missing["confirmation"]
        self.assertEqual(self.post(missing).status_code, 422)
        self.assertEqual(self.post(headers={"Authorization": "Bearer validated"}).status_code, 422)
        self.assertFalse(self.repo.calls)

    def test_deaths_method_cannot_choose_its_winner_or_fabricate_battles(self):
        battle = self.battle_body()
        for changes in (dict(winner_season_player_id=str(uuid4())), dict(battles=battle["battles"]),
                        dict(battles=[])):
            with self.subTest(changes=changes):
                self.assertEqual(self.post({**self.body, **changes}).status_code, 422)
        self.assertFalse(self.repo.calls)

    def test_actual_battle_transport_has_canonical_pairs_and_aware_utc_time(self):
        body = self.battle_body()
        self.assertEqual(self.post(body).status_code, 200)
        first = self.repo.calls[-1][1]["body"]
        self.assertEqual(first["winner_season_player_id"], body["winner_season_player_id"])
        self.assertEqual(first["method"], "championship_1v1")
        self.assertIn("2026-01-01T10:00:00Z", [b["played_at"] for b in first["battles"]])
        reordered = deepcopy(body)
        reordered["battles"].reverse()
        self.assertEqual(self.post(reordered).status_code, 200)
        self.assertEqual(first, self.repo.calls[-1][1]["body"])

    def test_battle_requires_result_evidence_valid_time_and_no_duplicate_pair(self):
        body = self.battle_body()
        for changes in (dict(winner_season_player_id=None), dict(battles=None), dict(battles=[]),
                        dict(winner_season_player_id=str(uuid4()))):
            self.assertEqual(self.post({**body, **changes}).status_code, 422)
        for key, value in (("winner_id", str(uuid4())), ("evidence", " "),
                           ("played_at", "2026-01-01T10:00:00"), ("played_at", 0),
                           ("played_at", (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()),
                           ("score", 1)):
            changed = deepcopy(body)
            changed["battles"][0][key] = value
            self.assertEqual(self.post(changed).status_code, 422, key)
        same = deepcopy(body)
        same["battles"][0]["player_b_id"] = same["battles"][0]["player_a_id"]
        self.assertEqual(self.post(same).status_code, 422)
        duplicate = deepcopy(body)
        duplicate["battles"].append({**duplicate["battles"][0],
            "player_a_id":duplicate["battles"][0]["player_b_id"],
            "player_b_id":duplicate["battles"][0]["player_a_id"]})
        self.assertEqual(self.post(duplicate).status_code, 422)
        self.assertFalse(self.repo.calls)

    def test_receipt_must_remain_provisional_in_same_scope(self):
        for changes in (dict(operation="finish"), dict(state="finished"),
                        dict(actor_trainer_id=str(uuid4())), dict(season_id=str(uuid4())),
                        dict(hall_id=str(uuid4())), dict(archive_id=str(uuid4()))):
            original = deepcopy(self.repo.response)
            self.repo.response.update(changes)
            self.assertEqual(self.post().status_code, 503)
            self.repo.response = original

    def test_actionable_sql_refusals_are_preserved(self):
        for code in ("CHAMPIONSHIP_REVIEW_STALE", "CHAMPIONSHIP_BATTLE_REQUIRED",
                     "CHAMPIONSHIP_DEATHS_UNAVAILABLE", "CHAMPIONSHIP_BATTLE_AMBIGUOUS",
                     "CHAMPIONSHIP_RESOLUTION_CONFLICT"):
            self.repo.failure = SeasonAdminRejected(code, 409)
            response = self.post()
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["detail"]["code"], code)

    def test_read_separates_actual_history_from_adjusted_units_for_trainers_too(self):
        self.repo.response = tied_review()
        self.principals.trainer = replace(self.principals.trainer, is_admin=False)
        response = self.client.get(f"/v1/seasons/{SID}/championship", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["players"][0]["actual_deaths"], 5)
        self.assertEqual(response.json()["players"][0]["adjusted_deaths"], 20)
        self.assertEqual(response.json()["players"][0]["total_points"], "10.500000000000000001")
        self.assertIsNone(response.json()["champion_trainer_id"])

    def test_read_unresolved_scope_and_real_history_are_not_silently_defaulted(self):
        base = tied_review()
        for changes in (dict(state="battle_required"), dict(tied_player_ids=[]),
                        dict(champion_trainer_id=TRAINER_ID), dict(input_hash=None),
                        dict(players=[{**base["players"][0], "actual_deaths":True}, *base["players"][1:]]),
                        dict(players=[{**base["players"][0], "actual_deaths":-1}, *base["players"][1:]])):
            self.repo.response = {**deepcopy(base), **changes}
            self.assertEqual(self.client.get(self.path.removesuffix("/tiebreak"),
                                             headers=self.headers).status_code, 503)
        self.repo.response = {**base, "state":"battle_required", "tiebreak_method":"total_actual_deaths"}
        self.assertEqual(self.client.get(self.path.removesuffix("/tiebreak"), headers=self.headers).status_code, 200)
        self.repo.response["players"][0]["actual_deaths"] = None
        response = self.client.get(self.path.removesuffix("/tiebreak"), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["players"][0]["actual_deaths"])

    def test_new_ready_and_frozen_titles_bind_final_method_and_winner(self):
        base = tied_review()
        for state in ("ready", "frozen"):
            for method in ("total_actual_deaths", "championship_1v1"):
                valid = {**deepcopy(base), "state":state, "champion_trainer_id":TRAINER_ID,
                         "resolution_type":method, "tiebreak_method":method}
                self.assertEqual(ChampionshipRead.model_validate(valid).resolution_type, method)
                with self.assertRaises(ValueError):
                    ChampionshipRead.model_validate({**valid, "tiebreak_method":None})


class ChampionshipTiebreakRepositoryTests(unittest.TestCase):
    def test_new_command_uses_existing_atomic_rpc_once_and_preserves_input(self):
        client = Mock()
        client.rpc.return_value.execute.return_value.data = {"replayed":False}
        request = dict(actor_trainer_id=TRAINER_ID, season_id=SID, idempotency_key="t076",
                       body=dict(method="total_actual_deaths", confirmation=True))
        SupabaseSeasonLifecycleRepository(client).execute("championship_tiebreak", request)
        client.rpc.assert_called_once_with("api_admin_season_lifecycle",
            {"p_request":dict(request, operation="championship_tiebreak")})
        self.assertNotIn("operation", request)

    def test_uncertain_outcome_is_not_automatically_retried(self):
        client = Mock()
        client.rpc.return_value.execute.side_effect = Exception("PRIVATE")
        with self.assertRaises(PersistenceError):
            SupabaseSeasonLifecycleRepository(client).execute("championship_tiebreak", {})
        self.assertEqual(client.rpc.call_count, 1)

    def test_sql_validation_codes_map_to_actionable_conflicts(self):
        for message in ("championship_tiebreak_not_required", "championship_battle_required",
                        "championship_deaths_unavailable", "championship_resolution_conflict",
                        "championship_battle_invalid", "championship_battle_ambiguous"):
            client = Mock()
            error = Exception()
            error.message, error.code = message, "PT409"
            client.rpc.return_value.execute.side_effect = error
            with self.assertRaises(SeasonAdminRejected) as raised:
                SupabaseSeasonLifecycleRepository(client).execute("championship_tiebreak", {})
            self.assertEqual(raised.exception.code, message.upper())


if __name__ == "__main__":
    unittest.main()
