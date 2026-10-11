"""Shadow must detect discrepancies, never repair or promote a private reference."""

from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import tests.test_phase11_import as fixtures
from tools.phase11_import import canonical_json, read
from tools.phase12_shadow import CLASSES, DOMAINS, TABLES, capture_sql, compare


class Phase12ShadowTests(unittest.TestCase):
    def setUp(self):
        # Reuse credential-free fixture data, not the Phase11 PG runner/proofs.
        self.fixture = fixtures.Phase11ImportTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.plan = self.fixture.build()
        self.shadow = {t: [] for t in TABLES}
        self.shadow["runs"] = [dict(self.plan["run"], status="reconciled")]
        for batch in self.plan["batches"]:
            for table, rows in batch["tables"].items():
                self.shadow[table].extend(deepcopy(rows))
            self.shadow["batches"].append(
                dict(
                    run_id=self.plan["run"]["id"],
                    ordinal=batch["ordinal"],
                    completed_at="2026-10-11T01:00:00Z",
                )
            )
        self.source = read(self.fixture.directory / "capture.json")[0]

    def compare(self):
        return compare(
            self.shadow,
            self.source,
            self.fixture.observed,
            self.fixture.summary,
            self.fixture.content,
            self.fixture.candidates,
        )

    def test_all_surviving_domains_and_explicit_absence_classified(self):
        result = self.compare()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(set(result["counts"]), set(CLASSES))
        self.assertEqual(result["counts"]["BLOCKER"], 0)
        self.assertEqual(result["counts"]["EXPECTED_DIFFERENCE"], 6)
        self.assertEqual(result["counts"]["UNKNOWN"], 10)
        self.assertEqual(result["counts"]["NOT_APPLICABLE"], 8)
        self.assertEqual(result["domains_compared"], sorted(DOMAINS))
        self.assertEqual(
            len({f["id"] for f in result["findings"]}), len(result["findings"])
        )

    def test_deterministic_and_no_input_mutation_or_row_order_dependence(self):
        original = canonical_json(self.shadow)
        first = self.compare()
        self.assertEqual(first, self.compare())
        self.assertEqual(original, canonical_json(self.shadow))
        for rows in self.shadow.values():
            rows.reverse()
        self.assertEqual(first, self.compare())

    def test_reconciled_reference_and_six_receipts_required(self):
        self.shadow["runs"][0]["status"] = "prepared"
        self.assertEqual(self.compare()["status"], "BLOCKED")
        self.shadow["runs"][0]["status"] = "reconciled"
        self.shadow["batches"].pop()
        self.assertEqual(self.compare()["status"], "BLOCKED")

    def test_missing_and_duplicate_tables_rows_fail_closed(self):
        for change in (
            lambda: self.shadow.pop("wallets"),
            lambda: self.shadow["trainers"].append(
                deepcopy(self.shadow["trainers"][0])
            ),
        ):
            original = deepcopy(self.shadow)
            change()
            self.assertEqual(self.compare()["status"], "BLOCKED")
            self.shadow = original

    def test_imported_fact_defects_are_never_expected_differences(self):
        cases = [
            ("wallets", "balance", Decimal("0")),
            ("progress", "champion_defeated", True),
            ("saves", "content", "\\x00"),
            ("participants", "division", "B"),
            ("purchases", "price", Decimal("24")),
            ("cup_matches", "winner_id", self.shadow["trainers"][0]["id"]),
            ("identities", "target_id", "00000000-0000-4000-8000-000000000000"),
        ]
        for table, field, wrong in cases:
            with self.subTest(table=table, field=field):
                old = deepcopy(self.shadow)
                self.shadow[table][0][field] = wrong
                result = self.compare()
                self.assertGreater(result["counts"]["BLOCKER"], 0)
                self.assertIn(
                    "PHASE 11 MIGRATION DEFECT",
                    {r["origin"] for r in result["findings"]},
                )
                self.shadow = old

    def test_unknown_is_not_zero_or_false(self):
        row = next(r for r in self.shadow["progress"] if r["save_id"] is None)
        for field, value in (
            ("badge_count", 0),
            ("visible_deaths", 0),
            ("champion_defeated", False),
        ):
            with self.subTest(field=field):
                row[field] = value
                self.assertEqual(self.compare()["status"], "BLOCKED")
                row[field] = None
        wallet = next(r for r in self.shadow["wallets"] if not r["known"])
        wallet["balance"] = 0
        self.assertEqual(self.compare()["status"], "BLOCKED")

    def test_observed_zero_is_distinct_from_unknown(self):
        self.fixture.observed["progress"]["regions"][0]["badge_flags"] = [False] * 8
        self.fixture.settings["badges_count:Owner"] = 0
        self.plan = self.fixture.build()
        self.source = read(self.fixture.directory / "capture.json")[0]
        for batch in self.plan["batches"]:
            for table, rows in batch["tables"].items():
                self.shadow[table] = deepcopy(rows)
        self.shadow["runs"] = [dict(self.plan["run"], status="reconciled")]
        for receipt in self.shadow["batches"]:
            receipt["run_id"] = self.plan["run"]["id"]
        result = self.compare()
        self.assertEqual(result["status"], "PASS")
        classification = {r["id"]: r["classification"] for r in result["findings"]}
        self.assertEqual(classification["progress/Owner"], "MATCH")
        self.assertEqual(classification["progress/NoSave"], "UNKNOWN")

    def test_v2_reader_defect_has_separate_origin(self):
        for fake in (
            SimpleNamespace(badges_count=0, champion_defeated=True, state="observed"),
            ValueError("private diagnostic"),
        ):
            arguments = (
                {"side_effect": fake}
                if isinstance(fake, Exception)
                else {"return_value": fake}
            )
            with patch("tools.phase12_shadow.progress_read", **arguments):
                result = self.compare()
            self.assertIn(
                "V2 INTERPRETATION DEFECT", {r["origin"] for r in result["findings"]}
            )
            self.assertNotIn("private diagnostic", canonical_json(result))

    def test_no_fake_modern_cup_certification(self):
        with patch(
            "tools.phase12_shadow.validate_modern_cup", return_value=("fake", "fake")
        ):
            result = self.compare()
        finding = next(
            f for f in result["findings"] if f["id"] == "cup/certification_boundary"
        )
        self.assertEqual(
            (finding["classification"], finding["origin"]),
            ("BLOCKER", "V2 INTERPRETATION DEFECT"),
        )

    def test_exact_fractional_difference_is_not_truncated(self):
        self.shadow["purchases"][0]["price"] = Decimal("12.0000000000000000001")
        self.assertEqual(self.compare()["status"], "BLOCKED")

    def test_timestamp_instant_and_missing_historical_time(self):
        self.shadow["runs"][0]["captured_at"] = "2026-10-09T02:00:00+02:00"
        self.assertEqual(self.compare()["status"], "PASS")
        self.shadow["seasons"][0]["started_at"] = "2026-10-09T00:00:00Z"
        self.assertEqual(self.compare()["status"], "BLOCKED")

    def test_output_does_not_leak_private_input(self):
        output = canonical_json(self.compare())
        for secret in (
            "synthetic-credential",
            self.fixture.content.hex(),
            self.fixture.content_hash,
            "badge_flags",
            "tid",
            "sid",
            "GAME",
            "Legacy note",
        ):
            self.assertNotIn('"' + secret + '"', output)
        self.shadow["exclusions"][0]["payload"] = {"credential": "do-not-output-this"}
        output = canonical_json(self.compare())
        self.assertNotIn("do-not-output-this", output)
        self.assertIn('"BLOCKED"', output)

    def test_export_is_one_private_select(self):
        sql = capture_sql().lower()
        self.assertTrue(sql.startswith("select "))
        self.assertNotIn(";", sql)
        for forbidden in (
            "public.",
            "insert ",
            "update ",
            "delete ",
            "rpc",
            "create ",
            "grant ",
        ):
            self.assertNotIn(forbidden, sql)
        self.assertEqual(sql.count("from v1_shadow."), 15)


if __name__ == "__main__":
    unittest.main()
