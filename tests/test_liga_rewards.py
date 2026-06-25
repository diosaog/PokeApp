from __future__ import annotations

import unittest

from app.liga.divisions import division_a_size_for_count, next_divisions_from_rankings
from app.liga.ranking import MAX_JORNADAS
from app.liga.rewards import coins_for_league_position, points_for_league_position


class LigaRewardsTests(unittest.TestCase):
    def test_current_season_ends_after_round_four(self) -> None:
        self.assertEqual(MAX_JORNADAS, 4)

    def test_eight_player_rewards_start_on_round_four(self) -> None:
        self.assertEqual(points_for_league_position(1, 1, field_size=10), 9)
        self.assertEqual(points_for_league_position(1, 6, field_size=10), 5)
        self.assertEqual(points_for_league_position(3, 8, field_size=10), 3)
        self.assertEqual(coins_for_league_position(3, 8, field_size=10), 8)

        self.assertEqual(
            [points_for_league_position(4, pos, field_size=8) for pos in range(1, 9)],
            [7, 6, 5, 4, 4, 3, 2, 1],
        )
        self.assertEqual(
            [coins_for_league_position(4, pos, field_size=8) for pos in range(1, 9)],
            [15, 13, 11, 10, 11, 9, 7, 5],
        )

    def test_eight_player_divisions_start_on_round_four(self) -> None:
        self.assertEqual(division_a_size_for_count(8, 3), 5)
        self.assertEqual(division_a_size_for_count(8, 4), 4)
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
                ["A1", "A2", "A3", "A4"],
                ["B1", "B2", "B3", "B4"],
                round_no=4,
            ),
            (
                ["A1", "A2", "B1", "B2"],
                ["A3", "A4", "B3", "B4"],
                ["B1", "B2"],
                ["A3", "A4"],
            ),
        )


if __name__ == "__main__":
    unittest.main()
