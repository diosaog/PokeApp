"""Current-game projection, separate from historical sporting/economic facts."""

from copy import deepcopy
from dataclasses import replace
from unittest import TestCase
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.frontend_reads import FrontendReads
from app.application.progress import progress_read
from test_api_frontend_reads import ReadStore, PID, SID
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID


def observation(flags=None, champion=None, game="B2"):
    regions = ["johto", "kanto"] if game == "HG" else ["unova"]
    return dict(
        id=PID,
        trainer_id=TRAINER_ID,
        game=game,
        observed_at="2026-10-08T12:00:00Z",
        progress=dict(
            schema_version=1,
            primary_region=regions[0],
            regions=[
                dict(region=r, badge_flags=flags if flags is not None else [False] * 8)
                for r in regions
            ],
            champion_defeated=champion,
        ),
    )


class ProgressTests(TestCase):
    def setUp(self):
        self.store = ReadStore()
        self.row = observation()
        self.calls = []

        def observed(sid, tid=None):
            self.calls.append((sid, tid))
            return [deepcopy(self.row)]

        self.store.observed_progress = observed
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
        self.path = f"/v1/read/seasons/{SID}/progress"
        self.headers = {"Authorization": "Bearer validated"}

    def get(self, suffix=""):
        return self.client.get(self.path + suffix, headers=self.headers)

    def test_unknown_is_not_observed_zero_or_false(self):
        self.row.update(game=None, observed_at=None, progress=None)
        unknown = self.get().json()
        self.assertEqual(unknown["state"], "unknown")
        for key in ("badges_count", "regions", "champion_defeated", "observed_at"):
            self.assertIsNone(unknown[key])
        self.row = observation(champion=False)
        zero = self.get().json()
        self.assertEqual(zero["state"], "observed")
        self.assertEqual(zero["badges_count"], 0)
        self.assertEqual(zero["regions"][0]["earned_badges"], [])
        self.assertIs(zero["champion_defeated"], False)

    def test_champion_three_states_never_from_eight_badges(self):
        for champion in (True, False, None):
            self.row = observation([True] * 8, champion)
            result = self.get().json()
            self.assertEqual(result["badges_count"], 8)
            self.assertIs(result["champion_defeated"], champion)

    def test_sparse_and_second_region_preserve_identity(self):
        self.row = observation([False, True, False, True] + [False] * 4, game="HG")
        result = self.get().json()
        self.assertEqual(result["primary_region"], "johto")
        self.assertEqual(result["badges_count"], 4)
        self.assertEqual(
            result["regions"],
            [dict(region=r, earned_badges=[2, 4]) for r in ("johto", "kanto")],
        )
        self.assertNotIn("badge_flags", str(result))

    def test_legacy_overview_ignores_default_and_manual_counters(self):
        self.store.data["public_season_players"] = [
            dict(id=PID, trainer_id=TRAINER_ID, season_id=SID, status="active")
        ]
        self.store.data["public_season_player_stats"] = [
            dict(season_player_id=PID, season_id=SID, badges_count=8)
        ]
        self.row.update(game=None, observed_at=None, progress=None)
        result = FrontendReads(self.store).overview(SID, TRAINER_ID)
        self.assertIsNone(result.players[0].badges_count)
        self.assertEqual(result.players[0].progress.state, "unknown")
        self.assertFalse(
            any(c[0] == "public_season_player_stats" for c in self.store.calls)
        )

    def test_regression_reflects_current_evidence_without_mutation(self):
        for count in (6, 2, 0):
            self.row = observation([i < count for i in range(8)])
            self.assertEqual(self.get().json()["badges_count"], count)
        self.assertEqual(self.calls, [(SID, TRAINER_ID)] * 3)
        self.assertEqual(self.store.calls, [])

    def test_jwt_owner_and_no_progress_attestation(self):
        self.assertEqual(self.get().status_code, 200)
        self.assertEqual(self.calls, [(SID, TRAINER_ID)])
        for query in (
            "trainer_id=" + str(uuid4()),
            "badges_count=8",
            "champion_defeated=true",
        ):
            self.assertEqual(self.get("?" + query).status_code, 422)
        self.assertEqual(
            self.client.post(
                self.path, headers=self.headers, json={"champion_defeated": True}
            ).status_code,
            405,
        )
        self.assertEqual(len(self.calls), 1)

    def test_auth_and_disabled_guard(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(self.get().status_code, 403)
        self.assertEqual(self.calls, [])

    def test_foreign_owner_and_invalid_neutral_evidence_fail_closed(self):
        for key, value in (
            ("trainer_id", str(uuid4())),
            ("game", "unsupported"),
            ("observed_at", None),
            ("progress", True),
        ):
            self.row = observation()
            self.row[key] = value
            self.assertEqual(self.get().status_code, 503)
        self.row = observation()
        self.row["progress"]["champion_defeated"] = "true"
        self.assertEqual(self.get().status_code, 503)

    def test_old_reader_missing_completion_remains_unknown(self):
        self.row["progress"].pop("champion_defeated")
        self.assertIsNone(self.get().json()["champion_defeated"])

    def test_scope_and_missing_observation(self):
        self.store.observed_progress = lambda *args: None
        self.assertEqual(self.get().status_code, 404)
        self.store.observed_progress = lambda *args: []
        self.assertEqual(self.get().json()["state"], "unknown")
        self.store.observed_progress = lambda *args: [self.row, self.row]
        self.assertEqual(self.get().status_code, 503)

    def test_allowlist_drops_private_outer_evidence(self):
        self.row.update(
            source_hash="SECRET", save_file_id="SECRET", parser_version="SECRET"
        )
        result = progress_read(self.row).model_dump_json()
        self.assertNotIn("SECRET", result)
        self.assertNotIn("schema_version", result)
