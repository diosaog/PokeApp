from __future__ import annotations

from dataclasses import replace
import unittest

from app.season.config import (
    DEFAULT_COINS_BY_POSITION,
    DEFAULT_POINTS_BY_POSITION,
    coerce_season_document,
    default_season_version,
    season_version_for_round,
    season_version_to_dict,
)


class SeasonConfigTests(unittest.TestCase):
    def test_versioned_rules_apply_only_from_effective_round(self) -> None:
        base = default_season_version(players=["Anto", "Victor"], effective_round=1)
        later = default_season_version(players=["Anto", "Victor"], effective_round=3)
        later = replace(
            later,
            id="custom",
            name="Custom",
            points_by_position={1: 99, 2: 1},
            coins_by_position={1: 42, 2: 1},
        )
        document = coerce_season_document(
            {
                "active_version_id": "custom",
                "versions": [
                    season_version_to_dict(base),
                    season_version_to_dict(later),
                ],
            }
        )

        round_two = season_version_for_round(document, 2)
        round_three = season_version_for_round(document, 3)

        self.assertEqual(round_two.points_by_position, DEFAULT_POINTS_BY_POSITION)
        self.assertEqual(round_two.coins_by_position, DEFAULT_COINS_BY_POSITION)
        self.assertEqual(round_three.points_by_position[1], 99)
        self.assertEqual(round_three.coins_by_position[1], 42)


if __name__ == "__main__":
    unittest.main()
