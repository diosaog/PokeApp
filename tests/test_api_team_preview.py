"""H: JWT-owned private locks; spectator/public projection; 079 labelled provisional parties."""

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

    def test_first_fixation_status_survives_private_projection_and_legacy_flags(self):
        for status in ('on_time', 'late', 'unknown'):
            self.store.data['public_team_locks'][0]['timing_status'] = status
            self.store.data['team_locks'][0]['is_late'] = status != 'late'
            response = self.get(mode='battle', trainer_id=TRAINER_ID)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['teams'][0]['lock']['timing_status'], status)

    def test_locks_stored_without_item_table_are_named_with_the_league_game(self):
        # Locks fixed before 2026-11-11 kept "Item #287" without its table: the
        # web could only say «Objeto sin identificar». The participant's League
        # save game (public in the overview) names it; a stored value wins.
        games = {RIVAL: "X", THIRD: None}
        self.store.observed_progress = lambda season_id, trainer_id=None: [
            {"trainer_id": t, "game": g} for t, g in games.items()
        ]
        for row in self.store.data["public_team_locks"]:
            for mon in row["public_team_snapshot"]:
                mon["item"] = "Item #287"
        self.store.data["public_team_locks"][2]["public_team_snapshot"][0][
            "item"
        ] = ""
        response = self.get(trainer_id=RIVAL, second_trainer_id=THIRD)
        self.assert_public(response)
        rival, third = (t["lock"]["team"] for t in response.json()["teams"])
        self.assertEqual([m["item_generation"] for m in rival], [6] * 6)
        self.assertEqual([m["item"] for m in rival], ["Item #287"] * 6)
        # No League game known: nothing is guessed.
        self.assertEqual([m["item_generation"] for m in third], [None] * 6)
        # A snapshot that already names its table keeps it.
        for mon in self.store.data["public_team_locks"][1]["public_team_snapshot"]:
            mon["item_generation"] = 7
        rival = self.get(trainer_id=RIVAL).json()["teams"][0]["lock"]["team"]
        self.assertEqual([m["item_generation"] for m in rival], [7] * 6)
        self.assertFalse(
            {"team_locks", "save_files", "parsed_saves"}.intersection(
                c[0] for c in self.store.calls
            )
        )

    def test_own_private_lock_without_item_table_is_named_in_battle(self):
        # Batallas › own Team Lock «tus detalles privados»: Garra Rápida (#217)
        # and Baya Zidra (#158) read «Objeto sin identificar» on locks fixed
        # before 2026-11-11, while the live Equipo view named them.
        self.store.observed_progress = lambda season_id, trainer_id=None: [
            {"trainer_id": TRAINER_ID, "game": "OR"}
        ]
        own = self.store.data["team_locks"][0]["private_team_snapshot"]
        for mon, item in zip(own, ("Item #217", "Item #158", "", "Item #217", "Item #158", "")):
            mon["item"] = item
        response = self.get(mode="battle", trainer_id=TRAINER_ID)
        self.assertEqual(response.status_code, 200, response.text)
        entry = response.json()["teams"][0]
        self.assertEqual(entry["visibility"], "self")
        self.assertEqual(
            [m["item_generation"] for m in entry["lock"]["team"]],
            [6, 6, None, 6, 6, None],
        )
        self.assertEqual(entry["lock"]["team"][0]["ability"], "OWN_ABILITY")

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

    def seed_current_parties(self):
        """RIVAL has a synchronized League save; THIRD has never synchronized."""
        rival_save = str(uuid4())
        private = dict(species="Meowstic", form=1, nickname="Live", level=31, item="Item #1",
                       moves=[dict(name="Psychic", pp=10)], ability="RIVAL_ABILITY",
                       nature="RIVAL_NATURE", gender="F", identity_evidence="RAW_SECRET",
                       ivs={k: 30 for k in ("hp", "atk", "defense", "spa", "spd", "spe")})
        self.store.data["season_players"] += [
            dict(id=str(uuid4()), season_id=SID, trainer_id=RIVAL, status="active",
                 current_save_file_id=rival_save),
            dict(id=str(uuid4()), season_id=SID, trainer_id=THIRD, status="active",
                 current_save_file_id=None),
        ]
        self.store.data["save_files"].append(dict(
            id=rival_save, season_id=SID, trainer_id=RIVAL, deleted_at=None, parser_status="parsed",
            parser_version="v1", uploaded_at="2026-11-04T12:00:00Z", sha256="b" * 64))
        self.store.data["parsed_saves"].append(dict(
            save_file_id=rival_save, parser_version="v1", status="parsed", schema_version=1,
            payload=dict(save_record_id=rival_save, trainer_id=RIVAL, source_hash="b" * 64,
                         party=[dict(slot_number=2, pokemon=deepcopy(private)),
                                dict(slot_number=1, pokemon=dict(private, nickname="First"))],
                         boxes=[dict(box_number=1, slots=[dict(slot_number=1, pokemon=private)])])))
        self.store.data["trainers"] = [dict(id=THIRD, globally_enabled=True)]

    def test_missing_lock_shows_labelled_provisional_party_never_old_day_lock(self):
        self.seed_current_parties()
        for row in self.store.data["public_team_locks"] + self.store.data["team_locks"]:
            row["matchday_id"] = str(uuid4())
        response = self.get(trainer_id=RIVAL, second_trainer_id=THIRD)
        self.assert_public(response)
        rival, third = response.json()["teams"]
        self.assertIsNone(rival["lock"])
        self.assertEqual(rival["provisional"]["source"], "league")
        # Party only (never boxes), in slot order, public allowlist only.
        self.assertEqual([p["nickname"] for p in rival["provisional"]["team"]], ["First", "Live"])
        self.assertEqual(rival["provisional"]["team"][0]["form"], 1)
        self.assertNotIn("RIVAL_", response.text)
        self.assertNotIn("gender", rival["provisional"]["team"][0])
        self.assertEqual((third["lock"], third["provisional"], third["unavailable_reason"]),
                         (None, None, "no_synced_save"))
        # The owner's own battle view: their private details, still provisional.
        own = self.get(mode="battle", trainer_id=TRAINER_ID).json()["teams"][0]
        self.assertEqual((own["visibility"], own["lock"]), ("self", None))
        self.assertEqual(own["provisional"]["team"][0]["ability"], "Static")
        self.assertNotIn("SECRET", str(own))
        # The rival in battle mode stays public, even for the viewer's own request.
        self.assert_public(self.get(mode="battle", trainer_id=RIVAL))
        self.assertNotIn("public_matches", [c[0] for c in self.store.calls])

    def test_finished_season_without_lock_never_shows_a_live_party(self):
        self.seed_current_parties()
        self.store.data["seasons"][0]["status"] = "finished"
        for row in self.store.data["public_team_locks"] + self.store.data["team_locks"]:
            row["matchday_id"] = str(uuid4())
        response = self.get(trainer_id=RIVAL, second_trainer_id=THIRD)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([(t["provisional"], t["unavailable_reason"]) for t in response.json()["teams"]],
                         [(None, "no_team_lock")] * 2)
        self.assertFalse({"save_files", "parsed_saves"}.intersection(c[0] for c in self.store.calls))

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

    def test_missing_day_still_previews_current_parties_and_empty_roster_is_explicit(self):
        # No prepared J1 yet: Team Preview stays available with current parties.
        self.seed_current_parties()
        self.store.data["seasons"][0]["current_matchday_id"] = None
        response = self.get(trainer_id=RIVAL, second_trainer_id=TRAINER_ID)
        self.assert_public(response)
        body = response.json()
        self.assertIsNone(body["day"])
        self.assertEqual([t["trainer_id"] for t in body["teams"]], [RIVAL, TRAINER_ID])
        self.assertTrue(all(t["lock"] is None and t["provisional"] for t in body["teams"]))
        self.assertNotIn("team_locks", [c[0] for c in self.store.calls])
        self.assertNotIn("public_team_locks", [c[0] for c in self.store.calls])
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
