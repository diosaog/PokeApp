from __future__ import annotations

import re
from pathlib import Path
import unittest

from tools.generate_supabase_v2_bootstrap import render_bootstrap


ROOT = Path(__file__).resolve().parents[1]
V2_DIR = ROOT / "supabase" / "v2"
MIGRATIONS_DIR = V2_DIR / "migrations"
BOOTSTRAP_SQL = V2_DIR / "bootstrap.sql"


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
                "010_security_helpers.sql",
                "011_rls_policies.sql",
                "012_security_views.sql",
                "013_storage_policies.sql",
                "014_security_invoker_hardening.sql",
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
            "is_admin boolean not null default false",
            "create or replace function public.current_auth_uid()",
            "create or replace function public.current_trainer_id()",
            "create or replace function public.is_current_user_admin()",
            "create policy trainers_self_admin_read",
            "create or replace view public.public_trainers",
            "create or replace view public.public_team_locks",
            "create or replace view public.current_team_locks",
            "create or replace view public.public_coin_balances",
            "security_invoker = true",
            "revoke all on function public.current_trainer_id() from anon",
            "raw_saves_select_own_or_admin",
            "bucket_id = 'raw-saves'",
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
        self.assertIn("drop table if exists public.trainer_flags", reset)
        self.assertIn("drop table if exists public.pokemon_flags", reset)
        self.assertIn("drop table if exists public.trainers", reset)
        self.assertIn("drop function if exists public.current_auth_uid()", reset)
        self.assertIn("drop function if exists public.current_trainer_id()", reset)
        self.assertIn("drop function if exists public.is_current_user_admin()", reset)
        self.assertNotIn("drop schema public", reset)

    def test_bootstrap_is_generated_from_migrations_without_reset_sql(self) -> None:
        bootstrap = BOOTSTRAP_SQL.read_text(encoding="utf-8")
        lowered = bootstrap.lower()

        self.assertTrue(bootstrap.startswith("-- ONLY FOR EMPTY POKEAPP V2 DATABASE."))
        self.assertEqual(bootstrap, render_bootstrap())
        self.assertIn(
            "Source of truth: supabase/v2/migrations/001_core.sql through 014_security_invoker_hardening.sql",
            bootstrap,
        )
        self.assertNotIn("drop table", lowered)
        self.assertNotIn("drop schema", lowered)
        self.assertNotIn("reset_dev.sql", lowered)

        last_position = -1
        for path in _migration_files():
            begin_marker = f"-- BEGIN {path.name}"
            end_marker = f"-- END {path.name}"
            begin_position = bootstrap.index(begin_marker)
            end_position = bootstrap.index(end_marker)

            self.assertGreater(begin_position, last_position, path.name)
            self.assertGreater(end_position, begin_position, path.name)
            self.assertIn(path.read_text(encoding="utf-8").strip(), bootstrap, path.name)
            last_position = end_position

    def test_security_layer_enables_rls_on_every_v2_table(self) -> None:
        security_sql = _all_sql().lower()
        tables = set(re.findall(r"create table public\.([a-z_]+)", security_sql))

        for table in sorted(tables):
            self.assertIn(f"'{table}'", security_sql, table)

        self.assertEqual(security_sql.count("enable row level security"), 2)
        self.assertIn("alter table public.%i enable row level security", security_sql)


if __name__ == "__main__":
    unittest.main()
