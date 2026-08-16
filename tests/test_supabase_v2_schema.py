from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
V2_DIR = ROOT / "supabase" / "v2"
MIGRATIONS_DIR = V2_DIR / "migrations"


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _all_sql() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in _migration_files())


class SupabaseV2SchemaTests(unittest.TestCase):
    def test_expected_migration_set_is_versioned_and_ordered(self) -> None:
        names = [path.name for path in _migration_files()]

        self.assertEqual(
            names,
            [
                "001_core.sql",
                "002_seasons.sql",
                "003_league.sql",
                "004_shop.sql",
                "005_saves.sql",
                "006_activity_hall.sql",
                "007_competitions.sql",
                "008_indexes.sql",
                "009_seed.sql",
            ],
        )
        for path in _migration_files():
            source = path.read_text(encoding="utf-8").strip().lower()
            self.assertIn("begin;", source, path)
            self.assertTrue(source.endswith("commit;"), path)

    def test_tables_cover_greenfield_model_without_legacy_settings_blob(self) -> None:
        sql = _all_sql()
        tables = set(re.findall(r"create table public\.([a-z_]+)", sql))

        expected = {
            "activity_events",
            "app_settings",
            "coin_transactions",
            "cup_matches",
            "cup_participants",
            "cup_standings",
            "cups",
            "division_memberships",
            "divisions",
            "hall_of_fame_entries",
            "matchday_movements",
            "matchday_snapshots",
            "matchdays",
            "matches",
            "parsed_saves",
            "penalties",
            "pokemon_flags",
            "purchases",
            "redemptions",
            "save_files",
            "season_archive_snapshots",
            "season_config_versions",
            "season_player_stats",
            "season_players",
            "seasons",
            "shop_items",
            "shop_promotions",
            "team_locks",
            "trainers",
            "trainer_flags",
            "trial_cases",
            "trial_votes",
        }

        self.assertEqual(expected - tables, set())
        self.assertNotIn("create table public.settings", sql)
        self.assertNotIn("create table public.shop_discounts", sql)
        self.assertNotIn("create table public.saves", sql)

    def test_identity_and_season_scoping_are_explicit(self) -> None:
        sql = _all_sql().lower()

        self.assertIn("create extension if not exists pgcrypto", sql)
        self.assertGreaterEqual(sql.count("default gen_random_uuid()"), 25)
        self.assertNotRegex(sql, r'\b"user"\b')
        self.assertNotRegex(sql, r"\bjornada\s")
        self.assertNotRegex(sql, r"\btramo\s")

        season_scoped_tables = [
            "season_players",
            "season_config_versions",
            "divisions",
            "matchdays",
            "matches",
            "matchday_snapshots",
            "shop_promotions",
            "purchases",
            "redemptions",
            "coin_transactions",
            "save_files",
            "team_locks",
            "hall_of_fame_entries",
            "trainer_flags",
            "pokemon_flags",
            "penalties",
        ]
        for table in season_scoped_tables:
            pattern = rf"create table public\.{table} \((?P<body>.*?)\n\);"
            body = re.search(pattern, sql, flags=re.S)
            self.assertIsNotNone(body, table)
            self.assertIn("season_id uuid", body.group("body"), table)

    def test_critical_constraints_and_indexes_are_present(self) -> None:
        sql = _all_sql().lower()

        for token in [
            "uq_seasons_one_active",
            "uq_season_players_season_trainer",
            "uq_matchdays_season_number",
            "uq_matchday_snapshots",
            "uq_team_locks_matchday_trainer",
            "uq_shop_promotions_dedupe_key",
            "uq_activity_events_dedupe_key",
            "uq_hall_of_fame_season_competition",
            "stock_used <= stock_total",
            "winner_id is null or winner_id = player_a_id or winner_id = player_b_id",
            "total_price integer generated always as",
            "amount <> 0",
            "on delete restrict",
        ]:
            self.assertIn(token, sql)

    def test_privacy_ready_columns_and_no_plaintext_pin_seed(self) -> None:
        sql = _all_sql().lower()

        for token in [
            "auth_user_id uuid unique",
            "visibility text not null default 'public'",
            "private_team_snapshot jsonb",
            "storage_bucket text not null default 'raw-saves'",
            "storage_key text not null unique",
        ]:
            self.assertIn(token, sql)

        self.assertNotRegex(sql, r"\bpin\b")
        self.assertNotRegex(sql, r"\bpins\b")
        self.assertNotRegex(sql, r"\bpassword\b")
        self.assertIn("'chapa_dorada'", sql)
        self.assertIn('"promotion_blocked": true', sql)

    def test_reset_dev_is_destructive_and_separate(self) -> None:
        reset = (V2_DIR / "reset_dev.sql").read_text(encoding="utf-8").lower()

        self.assertIn("destructive development reset", reset)
        self.assertIn("do not run this against production", reset)
        self.assertIn("drop table if exists public.team_locks", reset)
        self.assertIn("drop table if exists public.trainers", reset)
        self.assertNotIn("drop schema public", reset)


if __name__ == "__main__":
    unittest.main()
