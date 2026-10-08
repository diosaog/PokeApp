"""K public competitive allowlist, scope and refusal of client privacy overrides."""

from copy import deepcopy
from dataclasses import replace
import unittest
from uuid import uuid4

import test_api_team_preview as preview_tests
from test_api_team_preview import RIVAL
from test_api_frontend_reads import SID, DAY
from test_api_phase8b import TRAINER_ID, FakeTokenVerifier
from app.auth.errors import InvalidSessionError


class ScoutingTests(unittest.TestCase):
    def setUp(self):
        preview_tests.TeamPreviewTests.setUp(self)
        self.path = f"/v1/read/seasons/{SID}/scouting"

    def get(self, /, **query):
        return self.client.get(self.path, params=query, headers=self.headers)

    def test_first_fixation_status_is_public_without_private_evidence(self):
        for state in ('on_time', 'late', 'unknown'):
            self.store.data['public_team_locks'][1]['timing_status'] = state
            response = self.get(trainer_id=RIVAL)
            self.assert_public(response)
            self.assertEqual(response.json()['team_lock_status'], state)
        self.store.data['public_team_locks'] = []
        self.assertEqual(self.get(trainer_id=RIVAL).json()['team_lock_status'], 'pending')

    def assert_public(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(set(data), {"season", "day", "trainers", "trainer_id", "team", "team_lock_status"})
        for mon in data["team"] or []:
            self.assertEqual(
                set(mon), {"species", "nickname", "level", "types", "item", "moves"}
            )
            for move in mon["moves"]:
                self.assertEqual(set(move), {"name"})
        for forbidden in (
            "OWN_",
            "RAW_SECRET",
            "ability",
            "nature",
            "ivs",
            "evs",
            "metadata",
            "identity_evidence",
            "original_trainer",
            "is_shiny",
            "locked_at",
            "is_late",
            "private_team_snapshot",
            "save_file",
            '"pp"',
        ):
            self.assertNotIn(forbidden, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertFalse(
            {
                "team_locks",
                "save_files",
                "parsed_saves",
                "pokemon_observations",
                "pokemon_entities",
                "public_matches",
            }.intersection(c[0] for c in self.store.calls)
        )

    def test_approved_fields_only_and_one_bounded_public_selection(self):
        response = self.get(trainer_id=RIVAL)
        self.assert_public(response)
        self.assertEqual(response.json()["trainer_id"], RIVAL)
        self.assertEqual(len(response.json()["team"]), 6)
        self.assertEqual(
            response.json()["team"][0],
            dict(
                species="Pikachu",
                nickname="Fijado",
                level=20,
                types=["Electric"],
                item="Berry",
                moves=[dict(name="Thunder")],
            ),
        )
        self.assertEqual(len(self.store.calls), 5)
        for table, columns, filters, *_ in self.store.calls:
            self.assertNotIn("*", columns)
            if table == "public_team_locks":
                self.assertEqual(filters, dict(season_id=SID, matchday_id=DAY))
                self.assertNotIn("private", columns)
        self.assertEqual(self.store.data, self.before)

    def test_self_and_admin_never_enter_private_branch(self):
        for admin in (False, True):
            self.principals.trainer = replace(self.principals.trainer, is_admin=admin)
            self.assert_public(self.get())
            self.assert_public(self.get(trainer_id=TRAINER_ID))
            self.assert_public(self.get(trainer_id=RIVAL))

    def test_client_authority_overrides_rejected_before_repository(self):
        for field in (
            "viewer_id",
            "self",
            "private",
            "admin",
            "participant_id",
            "actor_trainer_id",
            "second_trainer_id",
            "single_public",
            "mode",
            "save_file_id",
        ):
            with self.subTest(field=field):
                self.assertEqual(self.get(**{field: "true"}).status_code, 422)
        self.assertEqual(self.get(trainer_id="invalid").status_code, 422)
        self.assertEqual(self.store.calls, [])

    def test_jwt_required_and_disabled_rejected_before_read(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.client.app.state.api_container = replace(
            self.client.app.state.api_container,
            token_verifier=FakeTokenVerifier(fail=InvalidSessionError()),
        )
        self.assertEqual(self.get().status_code, 401)
        self.client.app.state.api_container = replace(
            self.client.app.state.api_container, token_verifier=FakeTokenVerifier()
        )
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(self.get().status_code, 403)
        self.assertEqual(self.store.calls, [])

    def test_missing_lock_no_current_save_or_previous_day_fallback(self):
        self.store.data["public_team_locks"][1]["matchday_id"] = str(uuid4())
        response = self.get(trainer_id=RIVAL)
        self.assert_public(response)
        self.assertIsNone(response.json()["team"])
        self.assertEqual(response.json()["trainer_id"], RIVAL)

    def test_other_season_and_non_participant_never_supply_a_team(self):
        self.assertEqual(self.get(trainer_id=str(uuid4())).status_code, 404)
        self.store.data["public_team_locks"][1]["season_id"] = str(uuid4())
        self.assertIsNone(self.get(trainer_id=RIVAL).json()["team"])
        self.assertEqual(
            self.client.get(
                f"/v1/read/seasons/{uuid4()}/scouting", headers=self.headers
            ).status_code,
            404,
        )
        self.store.data["seasons"][0]["status"] = "discarded"
        self.assertEqual(self.get().status_code, 404)

    def test_no_day_and_empty_roster_are_explicit(self):
        self.store.data["seasons"][0]["current_matchday_id"] = None
        response = self.get(trainer_id=RIVAL)
        self.assert_public(response)
        self.assertIsNone(response.json()["day"])
        self.assertIsNone(response.json()["team"])
        self.assertEqual(response.json()["trainer_id"], RIVAL)
        self.store.data["public_season_players"] = []
        data = self.get().json()
        self.assertEqual(data["trainers"], [])
        self.assertIsNone(data["trainer_id"])
        self.assertIsNone(data["team"])

    def test_malformed_snapshots_fail_closed_with_sanitized_error(self):
        bad = [
            [],
            [{}] * 6,
            [{"species": ""}] * 6,
            [{"species": "P", "moves": [{"name": {"raw": "RAW_SECRET"}}]}] * 6,
            [{"species": "P", "level": -1}] * 6,
            [{"species": "P", "types": [{"raw": "RAW_SECRET"}]}] * 6,
            [{"species": "P", "item": {"raw": "RAW_SECRET"}}] * 6,
            "RAW_SECRET",
        ]
        for team in bad:
            with self.subTest(team=team):
                self.store.data["public_team_locks"][1]["public_team_snapshot"] = team
                response = self.get(trainer_id=RIVAL)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("RAW_SECRET", response.text)

    def test_no_fabrication_of_missing_optional_competitive_facts(self):
        self.store.data["public_team_locks"][1]["public_team_snapshot"] = [
            dict(species="Pikachu")
        ] * 6
        response = self.get(trainer_id=RIVAL)
        self.assert_public(response)
        self.assertEqual(
            response.json()["team"][0],
            dict(
                species="Pikachu", nickname="", level=None, types=[], item="", moves=[]
            ),
        )

    def test_other_unselected_malformed_team_does_not_replace_selection(self):
        self.store.data["public_team_locks"][0]["public_team_snapshot"] = "invalid"
        self.assert_public(self.get(trainer_id=RIVAL))

    def test_private_battle_cache_cannot_broaden_scouting(self):
        response = self.client.get(
            self.path.replace("/scouting", "/team-preview"),
            params=dict(mode="battle", trainer_id=TRAINER_ID),
            headers=self.headers,
        )
        self.assertIn("OWN_ABILITY", response.text)
        self.store.calls.clear()
        self.assert_public(self.get(trainer_id=TRAINER_ID))
        self.assert_public(self.get(trainer_id=RIVAL))

    def test_frozen_history_and_late_lock_remain_public_without_mutation(self):
        self.store.data["seasons"][0]["status"] = "archived"
        self.store.data["public_matchdays"][0]["status"] = "closed"
        self.store.data["public_team_locks"][1]["is_late"] = True
        self.store.data["parsed_saves"] = [
            dict(payload={"party": [{"species": "PRIVATE_CURRENT"}]})
        ]
        frozen = deepcopy(self.store.data)
        self.assert_public(self.get(trainer_id=RIVAL))
        self.assertEqual(self.store.data, frozen)

    def test_ambiguous_roster_or_lock_fails_closed(self):
        self.store.data["public_team_locks"].append(
            deepcopy(self.store.data["public_team_locks"][1])
        )
        self.assertEqual(self.get(trainer_id=RIVAL).status_code, 503)
        self.store.data = deepcopy(self.before)
        self.store.data["public_season_players"].append(
            deepcopy(self.store.data["public_season_players"][0])
        )
        self.assertEqual(self.get().status_code, 503)


if __name__ == "__main__":
    unittest.main()
