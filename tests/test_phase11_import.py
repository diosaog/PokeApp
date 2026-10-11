"""Bounded legacy mapping proofs with synthetic, credential-free fixtures."""

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.phase11_import import (
    SOURCE_REF,
    SOURCE_TABLES,
    build_plan,
    canonical_json,
    identity,
    loads,
    money,
    validate_plan,
)


class Phase11ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="phase11-mapper-unit-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.content = b"Synthetic fixture only; not a Pokemon save"
        self.filename = "synthetic.sav"
        (self.directory / self.filename).write_bytes(self.content)
        self.content_hash = sha256(self.content).hexdigest()
        self.names = ["Owner", "Other", "NoSave", "Fourth"]
        self.league = {
            "tramo": 1,
            "active": False,
            "divisions": {"A": self.names[:2], "B": self.names[2:]},
            "matches": {},
            "results": {},
            "movements": {},
            "round_snapshots": {},
        }
        self.cup = {
            "players": self.names,
            "round": 1,
            "max_rounds": 7,
            "wins": dict.fromkeys(self.names, 0),
            "losses": dict.fromkeys(self.names, 0),
            "byes": dict.fromkeys(self.names, 0),
            "history": [],
            "results": {},
            "current": {"pairs": [self.names[:2], self.names[2:]], "bye": None},
        }
        self.settings = {
            "league_state": self.league,
            "copa_swiss_state": self.cup,
            "trainer_flags": {"Other": {"robbed": True, "note": "Legacy note"}},
            "current_save:Owner": 434,
            "badges_count:Owner": 8,
            "pin:Owner": "synthetic-credential-not-for-migration",
            "discord_notify:example": "synthetic-notification-cache",
        }
        self.table_rows = {name: [] for name in SOURCE_TABLES}
        self.table_rows["public.saves"] = [{
            "id": 434,
            "user": "Owner",
            "sha256": self.content_hash,
            "filename": self.filename,
            "created_at": "2025-12-09 14:00:00",
        }]
        self.table_rows["public.purchases"] = [
            {"id": index, "user": "Owner", "item": item, "price": Decimal("12"),
             "status": "pending", "redeemed_at": None, "discount_id": None,
             "jornada": 1, "created_at": "2025-12-09 15:00:00"}
            for index, item in ((206, "Revivir Pokemon"), (207, "Robar Pokemon"))
        ]
        self.table_rows["storage.buckets"] = [{"id": "saves", "name": "saves"}]
        self.table_rows["storage.objects"] = [{
            "id": "61425973-86cb-4ab5-97d6-27124b3b24f2",
            "bucket_id": "saves", "name": self.filename,
            "metadata": {"size": len(self.content)},
        }]
        self.observed = {
            "game": "W2", "generation": 5,
            "trainer": {"name": "GAME", "tid": 1, "sid": 2, "gender": 0},
            "party": [None] * 6,
            "boxes": [{"number": number, "slots": [None] * 30} for number in range(1, 9)],
            "progress": {"schema_version": 1, "primary_region": "unova",
                         "regions": [{"region": "unova", "badge_flags": [True] * 8}],
                         "champion_defeated": False},
        }
        self.summary = {
            "source_copy_hash": self.content_hash, "source_size": len(self.content),
            "progress": self.observed["progress"], "game": "W2", "physical_save_write": False,
            "visible_dead_count": 0, "parser_version": "synthetic-reader/3",
            "observed_at": "2026-10-09T01:00:00Z",
        }
        self.project = {"id": SOURCE_REF}
        self.candidates = [{"display_name": "Owner", "id": "74ca9d55-c70b-4514-a0f7-779d76ce580e"}]

    def write(self, name, value):
        (self.directory / name).write_text(canonical_json(value), encoding="utf-8")

    def build(self):
        self.table_rows["public.settings"] = [
            {"key": key, "value": canonical_json(value)} for key, value in self.settings.items()
        ]
        self.write("project.json", self.project)
        self.write("capture.json", [{
            "captured_at": "2026-10-09T00:00:00Z", "snapshot": "synthetic-snapshot",
            "tables": [{"name": name, "count": len(rows), "rows": rows}
                       for name, rows in sorted(self.table_rows.items())],
        }])
        self.write("parsed.json", self.observed)
        self.write("parsed-save-summary.json", self.summary)
        self.write("candidates.json", self.candidates)
        return build_plan(self.directory / "capture.json", self.directory / "parsed.json",
                          self.directory, self.directory / "candidates.json")

    @staticmethod
    def rows(plan, table):
        return [row for batch in plan["batches"] for row in batch["tables"].get(table, [])]

    def test_unknown_and_observed_zero_remain_distinct(self):
        self.observed["progress"]["regions"][0]["badge_flags"] = [False] * 8
        self.settings["badges_count:Owner"] = 0
        plan = self.build()
        progress = {row["trainer_id"]: row for row in self.rows(plan, "progress")}
        owner = progress[identity("trainers", "Owner")]
        self.assertEqual(owner["badge_count"], 0)
        self.assertEqual(owner["visible_deaths"], 0)
        self.assertIs(owner["champion_defeated"], False)
        self.assertIsNotNone(owner["save_id"])
        for name in self.names[1:]:
            row = progress[identity("trainers", name)]
            for field in ("badge_count", "visible_deaths", "champion_defeated", "save_id"):
                self.assertIsNone(row[field])
            self.assertEqual(row["source_kind"], "unobserved")
        wallets = {row["trainer_id"]: row for row in self.rows(plan, "wallets")}
        self.assertEqual(wallets[owner["trainer_id"]]["balance"], Decimal(0))
        self.assertIsNone(wallets[identity("trainers", "Other")]["balance"])

    def test_eight_badges_never_become_completion_or_modern_rewards(self):
        plan = self.build()
        owner = next(row for row in self.rows(plan, "wallets") if row["known"])
        self.assertEqual(owner["badge_earnings"], Decimal(32))
        self.assertEqual(owner["spend"], Decimal(24))
        self.assertEqual(owner["balance"], Decimal(8))
        self.assertEqual(owner["completion_earnings"], Decimal(0))
        self.assertEqual(owner["badge_high_water"], 8)
        self.assertTrue(all(row["winner_id"] is None for row in self.rows(plan, "cup_matches")))
        self.assertEqual(self.rows(plan, "saves")[0]["content"], "\\x" + self.content.hex())

    def test_unknown_champion_stays_unknown(self):
        self.observed["progress"]["champion_defeated"] = None
        owner = next(row for row in self.rows(self.build(), "progress") if row["save_id"] is not None)
        self.assertIsNone(owner["champion_defeated"])

    def test_decimals_survive_exactly_and_plan_round_trips(self):
        self.table_rows["public.purchases"][0]["price"] = Decimal("0.1000000000000000001")
        self.table_rows["public.purchases"][1]["price"] = Decimal("0.2000000000000000002")
        plan = self.build()
        wallet = next(row for row in self.rows(plan, "wallets") if row["known"])
        self.assertEqual(wallet["spend"], Decimal("0.3000000000000000003"))
        self.assertEqual(wallet["balance"], Decimal("31.6999999999999999997"))
        decoded = loads(canonical_json(plan))
        validate_plan(decoded)
        self.assertEqual(plan, decoded)
        for value in (True, 0.1, Decimal("NaN"), Decimal("-1")):
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                money(value)

    def test_deterministic_namespaced_identities_without_identity_merge(self):
        first, second = self.build(), self.build()
        self.assertEqual(canonical_json(first), canonical_json(second))
        owner = next(row for row in self.rows(first, "trainers") if row["name"] == "Owner")
        self.assertEqual(owner["v2_candidate_id"], self.candidates[0]["id"])
        self.assertNotEqual(owner["id"], owner["v2_candidate_id"])
        self.assertTrue(all(row["trainer_id"] != owner["v2_candidate_id"]
                            for row in self.rows(first, "participants")))

    def test_credentials_and_operational_cache_values_are_excluded(self):
        plan = self.build()
        serialized = canonical_json(plan)
        self.assertNotIn("synthetic-credential-not-for-migration", serialized)
        self.assertNotIn("synthetic-notification-cache", serialized)
        exclusions = self.rows(plan, "exclusions")
        self.assertEqual(len(exclusions), 2)
        self.assertTrue(all(row["payload"] == {} for row in exclusions))
        self.assertFalse(any(row["source_key"].startswith(("pin:", "discord_notify:"))
                             for row in self.rows(plan, "records")))

    def test_no_invented_lifecycle_dates_or_history(self):
        plan = self.build()
        season = self.rows(plan, "seasons")[0]
        self.assertIsNone(season["started_at"])
        self.assertEqual(season["effective_status"], "active")
        self.assertIn("runtime default", season["status_provenance"])
        self.assertFalse(season["day_open"])
        self.assertIsNone(season["configuration"]["stored_configuration"])
        self.assertIsNone(self.rows(plan, "cups")[0]["rules_version"])
        self.assertEqual(self.rows(plan, "purchases")[0]["source_created_at"], "2025-12-09 15:00:00")
        self.assertNotIn("team_locks", {name for batch in plan["batches"] for name in batch["tables"]})

    def test_new_surviving_history_is_not_silently_ignored(self):
        for table in ("public.redemptions", "public.team_locks", "auth.users"):
            self.table_rows[table] = [{"id": "new"}]
            with self.subTest(table=table), self.assertRaisesRegex(ValueError, "New surviving domain"):
                self.build()
            self.table_rows[table] = []
        self.league["results"] = {"1": "winner"}
        with self.assertRaisesRegex(ValueError, "Surviving League history"):
            self.build()

    def test_wrong_source_or_save_bytes_or_progress_conflict_fail_closed(self):
        self.project["id"] = "another-project"
        with self.assertRaises(ValueError):
            self.build()
        self.project["id"] = SOURCE_REF
        (self.directory / self.filename).write_bytes(self.content + b"changed")
        with self.assertRaisesRegex(ValueError, "bytes differ"):
            self.build()
        (self.directory / self.filename).write_bytes(self.content)
        self.settings["badges_count:Owner"] = 7
        with self.assertRaisesRegex(ValueError, "mapping conflict"):
            self.build()

    def test_missing_box_eight_is_not_observed_zero(self):
        self.observed["boxes"] = self.observed["boxes"][:1]
        with self.assertRaises(ValueError):
            self.build()

    def test_unbound_summary_or_additional_progress_is_rejected(self):
        self.summary["source_copy_hash"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "not bound"):
            self.build()
        self.summary["source_copy_hash"] = self.content_hash
        self.settings["badges_count:Other"] = 0
        with self.assertRaisesRegex(ValueError, "Additional legacy progress"):
            self.build()

    def test_plan_changes_are_detected_before_execution(self):
        plan = self.build()
        edited = deepcopy(plan)
        edited["batches"][0]["tables"]["seasons"][0]["started_at"] = "2020-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "Batch content fingerprint"):
            validate_plan(edited)
        edited = deepcopy(plan)
        edited["run"]["manifest"]["semantics"] = "tampered"
        with self.assertRaisesRegex(ValueError, "Plan content fingerprint"):
            validate_plan(edited)


if __name__ == "__main__":
    unittest.main()
