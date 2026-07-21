from __future__ import annotations

from dataclasses import replace
import unittest

from app.season.config import default_season_version
from app.season.validation import (
    has_blocking_issues,
    season_version_changes,
    validate_season_version,
)


class SeasonValidationTests(unittest.TestCase):
    def test_valid_default_season_has_no_blocking_issues(self) -> None:
        version = default_season_version(
            players=[
                "Anto",
                "Victor",
                "Samu",
                "Rober",
                "Aaron",
                "Miguel",
                "Daviry",
                "Iker",
                "Barto",
                "Sergio",
            ]
        )

        issues = validate_season_version(version)

        self.assertFalse(has_blocking_issues(issues))
        self.assertEqual(issues[0]["level"], "ok")

    def test_division_sizes_must_match_player_count(self) -> None:
        version = replace(
            default_season_version(players=["Anto", "Victor", "Samu"]),
            division_sizes=[2, 2],
        )

        issues = validate_season_version(version)

        self.assertTrue(has_blocking_issues(issues))
        self.assertTrue(any(issue["title"] == "Reparto descuadrado" for issue in issues))

    def test_rewards_must_cover_active_positions(self) -> None:
        version = replace(
            default_season_version(players=["Anto", "Victor", "Samu"]),
            division_sizes=[2, 1],
            points_by_position={1: 9, 2: 8},
            coins_by_position={1: 15, 2: 14, 3: 12},
        )

        issues = validate_season_version(version)

        self.assertTrue(has_blocking_issues(issues))
        self.assertTrue(any(issue["title"] == "Puntos incompletos" for issue in issues))

    def test_change_summary_only_returns_modified_fields(self) -> None:
        current = default_season_version(players=["Anto", "Victor"])
        proposed = replace(current, max_rounds=5, movement_count=1)

        changes = season_version_changes(current, proposed)

        self.assertEqual([change[0] for change in changes], ["Jornadas", "Ascensos/descensos"])


if __name__ == "__main__":
    unittest.main()
