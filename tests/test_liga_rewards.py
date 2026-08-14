from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from app.liga.divisions import division_a_size_for_count, next_divisions_from_rankings
from app.liga.ranking import MAX_JORNADAS, max_jornadas
from app.liga.rewards import coins_for_league_position, points_for_league_position
from app.season.config import default_season_version


class LigaRewardsTests(unittest.TestCase):
    def test_current_season_ends_after_round_four(self) -> None:
        self.assertEqual(MAX_JORNADAS, 4)

    def test_max_jornadas_uses_active_season_config(self) -> None:
        with patch("app.liga.ranking.max_rounds", return_value=6):
            self.assertEqual(max_jornadas(1), 6)

    def test_current_rewards_apply_from_round_one(self) -> None:
        expected_points = [9, 8, 7, 6, 5, 5, 4, 3, 2, 1]
        expected_coins = [15, 14, 12, 11, 10, 11, 9, 8, 6, 4]

        self.assertEqual(
            [points_for_league_position(1, pos) for pos in range(1, 11)],
            expected_points,
        )
        self.assertEqual(
            [coins_for_league_position(1, pos) for pos in range(1, 11)],
            expected_coins,
        )
        self.assertEqual(points_for_league_position(4, 6, field_size=8), 5)
        self.assertEqual(coins_for_league_position(4, 10, field_size=8), 4)

    def test_divisions_stay_five_player_a_league(self) -> None:
        self.assertEqual(division_a_size_for_count(8, 3), 5)
        self.assertEqual(division_a_size_for_count(8, 4), 5)
        self.assertEqual(division_a_size_for_count(10, 4), 5)

        self.assertEqual(
            next_divisions_from_rankings(
                ["A1", "A2", "A3", "A4", "A5"],
                ["B1", "B2", "B3"],
                round_no=3,
            ),
            (
                ["A1", "A2", "B1", "B2", "B3"],
                ["A3", "A4", "A5"],
                ["B1", "B2", "B3"],
                ["A3", "A4", "A5"],
            ),
        )
        self.assertEqual(
            next_divisions_from_rankings(
                ["A1", "A2", "A3", "A4", "A5"],
                ["B1", "B2", "B3", "B4", "B5"],
                round_no=4,
            ),
            (
                ["A1", "A2", "B1", "B2", "B3"],
                ["A3", "A4", "A5", "B4", "B5"],
                ["B1", "B2", "B3"],
                ["A3", "A4", "A5"],
            ),
        )

    def test_division_sizes_and_movements_come_from_config(self) -> None:
        version = replace(
            default_season_version(players=["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]),
            division_sizes=[4, 4],
            movement_count=1,
        )

        with patch("app.season.config.current_season_version", return_value=version):
            self.assertEqual(division_a_size_for_count(8, 1), 4)
            self.assertEqual(
                next_divisions_from_rankings(
                    ["A1", "A2", "A3", "A4"],
                    ["B1", "B2", "B3", "B4"],
                    round_no=1,
                ),
                (
                    ["A1", "A2", "A3", "B1"],
                    ["A4", "B2", "B3", "B4"],
                    ["B1"],
                    ["A4"],
                ),
            )


if __name__ == "__main__":
    unittest.main()
