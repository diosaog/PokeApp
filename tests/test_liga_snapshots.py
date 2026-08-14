from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.liga import coins, ranking, state
from app.liga.permissions import LeaguePermissionError, require_league_admin
from app.liga.snapshots import (
    ROUND_SNAPSHOTS_STATE_KEY,
    build_matchday_snapshot,
    normalize_round_snapshots,
    snapshot_awards_for_user,
    snapshot_standings,
)
from app.season.config import default_season_version


class Session(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


def _season(version_id: str, *, points: dict[int, int], coins_: dict[int, int]):
    return replace(
        default_season_version(players=["Anto", "Victor"], effective_round=1),
        id=version_id,
        points_by_position=points,
        coins_by_position=coins_,
        division_sizes=[1, 1],
        movement_count=1,
    )


def _snapshot():
    return build_matchday_snapshot(
        round_no=1,
        division_snapshot={"A": ["Anto"], "B": ["Victor"]},
        rank_a=["Anto"],
        rank_b=["Victor"],
        season_version=_season(
            "v1",
            points={1: 9, 2: 8},
            coins_={1: 15, 2: 14},
        ),
        penalties_by_user={
            "Anto": {"dead_count": 2, "points_reduction": 1.5},
            "Victor": {"dead_count": 0},
        },
        closed_at=1000,
    )


class LigaSnapshotTests(unittest.TestCase):
    def test_snapshot_freezes_config_version_points_and_coins(self) -> None:
        snapshot = _snapshot()
        _v2 = _season("v2", points={1: 12, 2: 10}, coins_={1: 30, 2: 20})

        self.assertEqual(snapshot["season_config_version"]["id"], "v1")
        self.assertEqual(snapshot["points_awarded"], {"Anto": 9, "Victor": 8})
        self.assertEqual(snapshot["coins_awarded"], {"Anto": 15, "Victor": 14})
        self.assertEqual(snapshot["penalties"]["Anto"]["dead_count"], 2)

    def test_snapshot_first_points_ignore_later_dynamic_config(self) -> None:
        session = Session(
            {
                "league_results": {"Anto": {1: 1}},
                ROUND_SNAPSHOTS_STATE_KEY: {1: _snapshot()},
            }
        )

        with (
            patch.object(ranking, "st", SimpleNamespace(session_state=session)),
            patch.object(
                ranking,
                "_visible_league_users",
                return_value={"Anto": "a07", "Victor": "v42"},
            ),
            patch.object(ranking, "points_for_league_position", return_value=12),
        ):
            self.assertEqual(ranking.points_from_league("Anto"), 9)

    def test_snapshot_first_coins_ignore_later_dynamic_config(self) -> None:
        session = Session(
            {
                "league_results": {"Anto": {1: 1}},
                ROUND_SNAPSHOTS_STATE_KEY: {1: _snapshot()},
            }
        )

        with (
            patch.object(coins, "st", SimpleNamespace(session_state=session)),
            patch.object(
                coins,
                "_visible_league_users",
                return_value={"Anto": "a07", "Victor": "v42"},
            ),
            patch("app.liga.state.restore_state", return_value=False),
            patch.object(coins, "coins_for_league_position", return_value=30),
        ):
            self.assertEqual(coins.coins_from_league("Anto"), 15)

    def test_closed_standings_are_read_from_snapshot(self) -> None:
        standings = snapshot_standings({1: _snapshot()}, 1)

        self.assertEqual([row["user"] for row in standings], ["Anto", "Victor"])
        self.assertEqual([row["position"] for row in standings], [1, 2])

    def test_open_or_legacy_round_keeps_dynamic_behavior(self) -> None:
        session = Session(
            {
                "league_results": {"Anto": {1: 1}},
                ROUND_SNAPSHOTS_STATE_KEY: {},
            }
        )

        with (
            patch.object(ranking, "st", SimpleNamespace(session_state=session)),
            patch.object(
                ranking,
                "_visible_league_users",
                return_value={"Anto": "a07", "Victor": "v42"},
            ),
            patch.object(ranking, "points_for_league_position", return_value=12),
        ):
            self.assertEqual(ranking.points_from_league("Anto"), 12)

    def test_legacy_league_state_without_snapshots_loads_without_error(self) -> None:
        session = Session()
        legacy = {
            "tramo": 1,
            "active": False,
            "divisions": {"A": ["Anto"], "B": ["Victor"]},
            "matches": {},
            "results": {"Anto": {"1": 1}},
            "movements": {},
        }

        with (
            patch.object(state, "st", SimpleNamespace(session_state=session)),
            patch.object(
                state,
                "league_users_for_round",
                return_value={"Anto": "a07", "Victor": "v42"},
            ),
            patch.object(state, "division_a_size_for_count", return_value=1),
        ):
            state._apply_serialized_state(legacy)

        self.assertEqual(session[ROUND_SNAPSHOTS_STATE_KEY], {})
        self.assertEqual(normalize_round_snapshots(None), {})

    def test_finalize_rejects_existing_round_snapshot(self) -> None:
        session = Session({ROUND_SNAPSHOTS_STATE_KEY: {1: _snapshot()}})

        with patch.object(ranking, "st", SimpleNamespace(session_state=session)):
            with self.assertRaises(ValueError):
                ranking.finalize(1, admin_user="Anto")

    def test_finalize_rejects_legacy_recorded_results_without_snapshot(self) -> None:
        session = Session(
            {
                "league_results": {"Anto": {1: 1}},
                ROUND_SNAPSHOTS_STATE_KEY: {},
            }
        )

        with patch.object(ranking, "st", SimpleNamespace(session_state=session)):
            with self.assertRaises(ValueError):
                ranking.finalize(1, admin_user="Anto")

    def test_non_admin_cannot_finalize(self) -> None:
        with self.assertRaises(LeaguePermissionError):
            ranking.finalize(1, admin_user="Victor")

    def test_admin_permission_guard_accepts_only_anto(self) -> None:
        require_league_admin("Anto")
        with self.assertRaises(LeaguePermissionError):
            require_league_admin("Samu")


if __name__ == "__main__":
    unittest.main()
