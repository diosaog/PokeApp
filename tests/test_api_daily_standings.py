"""Modern shared positions remain explicit while legacy snapshots stay frozen."""

from copy import deepcopy
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.daily_ranking import RULE, LEGACY_RULE
from test_api_frontend_reads import DAY, PID, SID, ReadStore
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier


def standing(player_id, allocation=4):
    return dict(
        trainer_id=player_id,
        division_id="B",
        position=4,
        division_position=1,
        points_awarded=2,
        score="1.60",
        penalties={"PRIVATE": "judicial"},
        metadata=dict(
            ranking_rule=RULE,
            allocation_position=allocation,
            position_end=6,
            tie_status="unresolved_neutral",
            tie_size=3,
            wins=1,
            adjusted_deaths=2,
            private_save="PRIVATE",
        ),
    )


class DailyStandingsReadTests(unittest.TestCase):
    def setUp(self):
        self.store = ReadStore()
        self.players = [PID, str(uuid4()), str(uuid4())]
        self.snapshot = dict(
            schema_version=2,
            inputs=dict(
                ranking=dict(
                    rule=RULE,
                    input_hash="a" * 64,
                    resolutions=[dict(reason="PRIVATE", player_ids=self.players)],
                ),
                private_save="PRIVATE",
            ),
            standings=[
                standing(pid, index + 4) for index, pid in enumerate(self.players)
            ],
        )
        self.store.data["public_matchday_snapshots"] = [
            dict(
                season_id=SID,
                matchday_id=DAY,
                revision=1,
                closed_at="2026-10-01T12:00:00Z",
                snapshot=self.snapshot,
            )
        ]
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=FakePrincipalRepository(),
                    frontend_read_repository=self.store,
                )
            )
        )
        self.addCleanup(self.client.close)

    def get(self):
        return self.client.get(
            f"/v1/read/seasons/{SID}/overview",
            headers={"Authorization": "Bearer validated"},
        )

    def test_neutral_group_has_shared_sporting_positions_and_no_technical_order_leak(
        self,
    ):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        rows = response.json()["snapshots"][0]["standings"]
        self.assertEqual([row["position"] for row in rows], [4, 4, 4])
        self.assertEqual([row["division_position"] for row in rows], [1, 1, 1])
        self.assertEqual([row["position_end"] for row in rows], [6, 6, 6])
        self.assertEqual({row["tie_status"] for row in rows}, {"unresolved_neutral"})
        self.assertEqual({row["season_player_id"] for row in rows}, set(self.players))
        self.assertEqual({row["score"] for row in rows}, {"1.60"})
        for secret in (
            "PRIVATE",
            "allocation_position",
            "input_hash",
            "resolutions",
            "adjusted_deaths",
        ):
            self.assertNotIn(secret, response.text)

    def test_read_does_not_recompute_positions_from_transport_order_or_names(self):
        before = self.get().json()["snapshots"][0]["standings"]
        self.snapshot["standings"].reverse()
        self.store.data["public_trainers"][0]["display_name"] = "Renamed trainer"
        after = self.get().json()["snapshots"][0]["standings"]
        def key(row):
            return row["season_player_id"]
        self.assertEqual(sorted(before, key=key), sorted(after, key=key))

    def test_legacy_snapshot_keeps_its_recorded_position_without_modern_inference(self):
        self.snapshot["standings"] = [standing(PID)]
        row = self.snapshot["standings"][0]
        row.update(position=6, division_position=3)
        for inputs in (None, "PRIVATE", {}, {"ranking": {"rule": LEGACY_RULE}}):
            with self.subTest(inputs=inputs):
                self.snapshot["inputs"] = inputs
                response = self.get()
                self.assertEqual(response.status_code, 200)
                result = response.json()["snapshots"][0]["standings"][0]
                self.assertEqual(result["position"], 6)
                self.assertEqual(result["division_position"], 3)
                self.assertIsNone(result["position_end"])
                self.assertIsNone(result["tie_status"])

    def test_unique_and_external_resolution_display_the_official_position_only(self):
        self.snapshot["standings"] = [standing(PID)]
        row = self.snapshot["standings"][0]
        for status, size in (("unique", 1), ("externally_resolved", 3)):
            with self.subTest(status=status):
                row["metadata"].update(position_end=4, tie_status=status, tie_size=size)
                response = self.get()
                self.assertEqual(response.status_code, 200)
                result = response.json()["snapshots"][0]["standings"][0]
                self.assertEqual(
                    (result["position"], result["position_end"], result["tie_status"]),
                    (4, 4, status),
                )
                self.assertNotIn("PRIVATE", response.text)

    def test_unknown_rule_and_missing_modern_metadata_fail_closed(self):
        original = deepcopy(self.snapshot)
        mutations = (
            lambda snapshot: snapshot["inputs"].update(ranking="PRIVATE"),
            lambda snapshot: snapshot["inputs"]["ranking"].update(rule="PRIVATE"),
            lambda snapshot: snapshot["standings"][0].pop("metadata"),
            lambda snapshot: snapshot["standings"][0]["metadata"].update(
                ranking_rule=LEGACY_RULE
            ),
        )
        for mutate in mutations:
            self.snapshot.clear()
            self.snapshot.update(deepcopy(original))
            mutate(self.snapshot)
            response = self.get()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("PRIVATE", response.text)

    def test_inconsistent_sporting_metadata_is_not_silently_rendered(self):
        row = self.snapshot["standings"][0]
        original = deepcopy(row)
        invalid = (
            {"position_end": 3},
            {"position_end": 5},
            {"position_end": True},
            {"position_end": "6"},
            {"tie_size": 2},
            {"tie_size": 3.0},
            {"tie_status": "alphabetical"},
            {"tie_status": "unique"},
            {"tie_status": "externally_resolved"},
        )
        for change in invalid:
            with self.subTest(change=change):
                row.clear()
                row.update(deepcopy(original))
                row["metadata"].update(change)
                self.assertEqual(self.get().status_code, 503)
