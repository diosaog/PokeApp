"""H: JWT-owned private locks; spectator/public projection and no save fallback."""

from copy import deepcopy
from dataclasses import replace
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from test_api_frontend_reads import ReadStore, SID, DAY
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

RIVAL, THIRD = str(uuid4()), str(uuid4())


class TeamPreviewTests(unittest.TestCase):
    def setUp(self):
        self.store = ReadStore()
        self.principals = FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    frontend_read_repository=self.store,
                ),
                config=APIConfig(),
            )
        )
        self.addCleanup(self.client.close)
        self.headers = {"Authorization": "Bearer valid"}
        self.path = f"/v1/read/seasons/{SID}/team-preview"
        self.store.data["public_season_players"] = [
            dict(season_id=SID, trainer_id=t, status="active")
            for t in (TRAINER_ID, RIVAL, THIRD)
        ]
        self.store.data["public_trainers"] = [
            dict(id=t, display_name=name)
            for t, name in (
                (TRAINER_ID, "Antonio"),
                (RIVAL, "Lucía"),
                (THIRD, "Marcos"),
            )
        ]
        self.store.data["public_matchdays"] = [
            dict(id=DAY, season_id=SID, number=1, status="open")
        ]
        mon = dict(
            species="Pikachu",
            nickname="Fijado",
            level=20,
            types=["Electric"],
            item="Berry",
            moves=[dict(name="Thunder", pp=10, metadata="RAW_SECRET")],
            ability="OWN_ABILITY",
            nature="OWN_NATURE",
            ivs={k: 31 for k in ("hp", "atk", "defense", "spa", "spd", "spe")},
            evs={k: 0 for k in ("hp", "atk", "defense", "spa", "spd", "spe")},
            identity_evidence="RAW_SECRET",
            original_trainer="RAW_SECRET",
            metadata="RAW_SECRET",
        )
        self.store.data["public_team_locks"] = [
            dict(
                season_id=SID,
                trainer_id=t,
                matchday_id=DAY,
                locked_at="2026-10-07T10:00:00Z",
                is_late=False,
                public_team_snapshot=[deepcopy(mon) for _ in range(6)],
            )
            for t in (TRAINER_ID, RIVAL, THIRD)
        ]
        self.store.data["team_locks"] = [
            dict(row, private_team_snapshot=deepcopy(row["public_team_snapshot"]))
            for row in self.store.data["public_team_locks"]
        ]
        self.before = deepcopy(self.store.data)

    def get(self, /, **query):
        return self.client.get(self.path, params=query, headers=self.headers)

    def assert_public(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        for field in (
            "ability",
            "nature",
            "ivs",
            "evs",
            "identity_evidence",
            "metadata",
            "original_trainer",
        ):
            self.assertNotIn(field, response.text)
        self.assertNotIn("OWN_", response.text)
        self.assertNotIn("RAW_SECRET", response.text)
        self.assertTrue(
            all(t["visibility"] == "public" for t in response.json()["teams"])
        )

    def test_spectator_independent_unscheduled_trainers_public_only(self):
        response = self.get(trainer_id=RIVAL, second_trainer_id=THIRD)
        self.assert_public(response)
        self.assertEqual(
            [t["trainer_id"] for t in response.json()["teams"]], [RIVAL, THIRD]
        )
        self.assertEqual(len(response.json()["teams"][0]["lock"]["team"]), 6)
        self.assertEqual(self.store.data, self.before)
        self.assertNotIn("public_matches", [c[0] for c in self.store.calls])

    def test_spectator_self_stays_public_without_private_query(self):
        self.assert_public(self.get(trainer_id=TRAINER_ID, second_trainer_id=RIVAL))
        self.assertNotIn("team_locks", [c[0] for c in self.store.calls])

    def test_battle_rival_stays_public_even_for_admin(self):
        self.principals.trainer = replace(self.principals.trainer, is_admin=True)
        self.assert_public(self.get(mode="battle", trainer_id=RIVAL))
        self.assertEqual(
            len(self.get(mode="battle", trainer_id=RIVAL).json()["teams"]), 1
        )
        self.assertNotIn("team_locks", [c[0] for c in self.store.calls])

    def test_battle_self_private_whitelist_jwt_and_exact_scope(self):
        response = self.get(mode="battle", trainer_id=TRAINER_ID)
        self.assertEqual(response.status_code, 200, response.text)
        entry = response.json()["teams"][0]
        self.assertEqual(entry["visibility"], "self")
        self.assertEqual(entry["lock"]["team"][0]["ability"], "OWN_ABILITY")
        self.assertEqual(entry["lock"]["team"][0]["ivs"]["hp"], 31)
        self.assertNotIn("RAW_SECRET", response.text)
        calls = [c for c in self.store.calls if c[0] == "team_locks"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0][2], dict(season_id=SID, matchday_id=DAY, trainer_id=TRAINER_ID)
        )
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_spoofed_authority_and_invalid_modes_rejected_before_read(self):
        for params in (
            {"viewer_id": RIVAL},
            {"self": "true"},
            {"private": "true"},
            {"participant_id": RIVAL},
            {"actor_trainer_id": RIVAL},
            {"mode": "private"},
            {"mode": "battle", "second_trainer_id": RIVAL},
            {"trainer_id": RIVAL, "second_trainer_id": RIVAL},
            {"trainer_id": "bad"},
        ):
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 422)
        self.assertEqual(self.store.calls, [])

    def test_auth_invalid_disabled_rejected_before_read(self):
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

    def test_missing_lock_null_never_live_save_or_old_day_fallback(self):
        for row in self.store.data["public_team_locks"] + self.store.data["team_locks"]:
            row["matchday_id"] = str(uuid4())
        for mode in ("spectator", "battle"):
            response = self.get(mode=mode, trainer_id=TRAINER_ID)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(all(t["lock"] is None for t in response.json()["teams"]))
        forbidden = {
            "save_files",
            "parsed_saves",
            "pokemon_observations",
            "pokemon_entities",
            "public_matches",
        }
        self.assertFalse(forbidden.intersection(c[0] for c in self.store.calls))

    def test_wrong_season_and_outsider_cannot_retrieve_private(self):
        self.assertEqual(
            self.get(mode="battle", trainer_id=str(uuid4())).status_code, 404
        )
        self.store.data["team_locks"][0]["season_id"] = str(uuid4())
        self.assertIsNone(
            self.get(mode="battle", trainer_id=TRAINER_ID).json()["teams"][0]["lock"]
        )
        self.store.data["seasons"][0]["status"] = "discarded"
        self.assertEqual(self.get().status_code, 404)

    def test_missing_day_and_empty_roster_are_explicit(self):
        self.store.data["seasons"][0]["current_matchday_id"] = None
        response = self.get().json()
        self.assertIsNone(response["day"])
        self.assertEqual(response["teams"], [])
        self.assertNotIn("team_locks", [c[0] for c in self.store.calls])
        self.store.data["public_season_players"] = []
        self.assertEqual(self.get().json()["trainers"], [])

    def test_malformed_or_ambiguous_lock_fails_closed(self):
        for team in ([], [dict(species="Pikachu")] * 5, [dict(species="")] * 6, "bad"):
            with self.subTest(team=team):
                self.store.data["public_team_locks"][0]["public_team_snapshot"] = team
                self.assertEqual(self.get().status_code, 503)
        self.store.data["public_team_locks"] = deepcopy(
            self.before["public_team_locks"]
        )
        self.store.data["public_team_locks"].append(
            deepcopy(self.store.data["public_team_locks"][0])
        )
        self.assertEqual(self.get().status_code, 503)

    def test_no_private_cache_leak_between_modes_or_selectors(self):
        self.assertIn(
            "OWN_ABILITY", self.get(mode="battle", trainer_id=TRAINER_ID).text
        )
        self.assert_public(self.get(mode="spectator", trainer_id=TRAINER_ID))
        self.assert_public(self.get(mode="battle", trainer_id=RIVAL))

    def test_historical_season_uses_only_frozen_lock_and_bounded_reads(self):
        self.store.data["seasons"][0]["status"] = "archived"
        self.store.data["public_matchdays"][0]["status"] = "closed"
        response = self.get(mode="battle", trainer_id=TRAINER_ID)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["teams"][0]["lock"]["team"][0]["nickname"], "Fijado"
        )
        self.assertEqual(len(self.store.calls), 6)
        self.assertFalse(
            {"hall_of_fame_entries", "league_finalizations"}.intersection(
                c[0] for c in self.store.calls
            )
        )


if __name__ == "__main__":
    unittest.main()
