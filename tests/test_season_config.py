from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.liga.permissions import LeaguePermissionError
from app.season.config import (
    DEFAULT_COINS_BY_POSITION,
    DEFAULT_POINTS_BY_POSITION,
    coerce_season_document,
    clear_season_config_cache,
    default_season_version,
    save_season_version,
    season_version_for_round,
    season_version_to_dict,
)
from utils import league_users_for_round


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

    def test_legacy_rules_are_completed_with_defaults(self) -> None:
        base = season_version_to_dict(default_season_version(players=["Anto", "Victor"]))
        base["rules"] = {"last_b_gets_steal": "false"}

        document = coerce_season_document({"versions": [base]})
        version = season_version_for_round(document, 1)

        self.assertFalse(version.rules["last_b_gets_steal"])
        self.assertTrue(version.rules["team_lock_required"])
        self.assertTrue(version.rules["cup_is_separate"])

    def test_save_season_version_requires_anto(self) -> None:
        version = default_season_version(players=["Anto", "Victor"])

        with self.assertRaises(LeaguePermissionError):
            save_season_version(version, effective_round=1, admin_user="Victor")

    def test_save_season_version_blocks_closed_rounds(self) -> None:
        version = default_season_version(players=["Anto", "Victor"])
        league_state = '{"tramo":2,"active":false,"round_snapshots":{"1":{"round_no":1}}}'

        with (
            patch("app.season.config.settings_get", return_value=league_state),
            patch("app.season.config.st", SimpleNamespace(session_state={"user": "Anto"})),
        ):
            with self.assertRaises(ValueError):
                save_season_version(version, effective_round=1, admin_user="Anto")

    def test_save_season_version_blocks_current_open_round(self) -> None:
        version = default_season_version(players=["Anto", "Victor"])
        league_state = '{"tramo":2,"active":true,"round_snapshots":{"1":{"round_no":1}}}'

        with (
            patch("app.season.config.settings_get", return_value=league_state),
            patch("app.season.config.st", SimpleNamespace(session_state={"user": "Anto"})),
        ):
            with self.assertRaises(ValueError):
                save_season_version(version, effective_round=2, admin_user="Anto")

    def test_league_users_for_round_uses_explicit_season_roster(self) -> None:
        version = default_season_version(players=["Anto", "Victor"])
        document = coerce_season_document({"versions": [season_version_to_dict(version)]})
        raw = json.dumps(document)

        clear_season_config_cache()
        try:
            with patch("app.season.config.settings_get", return_value=raw):
                self.assertEqual(list(league_users_for_round(1).keys()), ["Anto", "Victor"])
        finally:
            clear_season_config_cache()


if __name__ == "__main__":
    unittest.main()
