"""Pure renderer safety; transaction behavior is proved with real PostgreSQL."""

from copy import deepcopy
from decimal import Decimal
import unittest

from tools.phase11_sql import render_batch, render_prepare, render_verify


def sample_plan():
    run_id = "2f646d35-fd87-563f-ae89-c7f2f51d8410"
    return {
        "run": {
            "id": run_id,
            "source_ref": "fdtytpeyfzyssfrsulxd",
            "capture_hash": "a" * 64,
            "mapping_version": "test/v1",
            "plan_hash": "b" * 64,
            "captured_at": "2026-10-09T00:00:00Z",
            "manifest": {"private": "O'Brien $$ $phase11$ \\ ' ; COMMIT; --"},
            "status": "prepared",
        },
        "batches": [{
            "ordinal": 1,
            "hash": "c" * 64,
            "tables": {
                "records": [{
                    "run_id": run_id,
                    "id": "b0f9bd03-e3dc-5bd2-9d86-7e6662b58fca",
                    "source_table": "public.purchases",
                    "source_key": "1",
                    "payload": {"amount": Decimal("12345678901234567890.123456789")},
                }],
            },
        }],
    }


class Phase11SqlTests(unittest.TestCase):
    def test_exact_decimal_and_private_literals_stay_data(self):
        sql = render_prepare(sample_plan())
        self.assertIn('12345678901234567890.123456789', sql)
        self.assertNotIn('"12345678901234567890.123456789"', sql)
        self.assertIn("O''Brien $$ $phase11$", sql)
        self.assertIn("SET LOCAL standard_conforming_strings = on", sql)
        self.assertNotIn("DO $$", sql)

    def test_unrecognized_tables_and_columns_rejected_before_render(self):
        for table in ("public.seasons", "runs", "batches", "records; COMMIT;"):
            with self.subTest(table=table):
                plan = sample_plan()
                plan["batches"][0]["tables"][table] = []
                with self.assertRaisesRegex(ValueError, "table"):
                    render_batch(plan, 1)
        plan = sample_plan()
        plan["batches"][0]["tables"]["records"][0]["status"] = "arbitrary"
        with self.assertRaisesRegex(ValueError, "column"):
            render_prepare(plan)

    def test_wrong_capture_and_duplicate_identity_rejected(self):
        plan = sample_plan()
        row = plan["batches"][0]["tables"]["records"][0]
        row["run_id"] = "a3f3eb5a-4763-4431-8833-6d8695108447"
        with self.assertRaisesRegex(ValueError, "another capture"):
            render_prepare(plan)
        plan = sample_plan()
        plan["batches"][0]["tables"]["records"].append(
            deepcopy(plan["batches"][0]["tables"]["records"][0])
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            render_prepare(plan)

    def test_inexact_and_nonfinite_numbers_rejected(self):
        for amount in (0.1, float("nan"), Decimal("Infinity"), Decimal("NaN")):
            plan = sample_plan()
            plan["batches"][0]["tables"]["records"][0]["payload"]["amount"] = amount
            with self.subTest(amount=str(amount)), self.assertRaises(ValueError):
                render_batch(plan, 1)

    def test_read_only_verification_does_not_import_or_certify(self):
        sql = render_verify(sample_plan())
        for forbidden in ("INSERT INTO", "UPDATE ", "DELETE FROM", "CREATE "):
            self.assertNotIn(forbidden, sql)
        self.assertIn("EXCEPT ALL", sql)
        self.assertIn("v1_shadow.wallets", sql)
        self.assertIn("v1_shadow.cup_matches", sql)
        self.assertIn("completed_at IS NULL", sql)
        self.assertIn("coalesce(max(ordinal), 0)", sql)

    def test_complete_certification_and_atomic_batch(self):
        plan = sample_plan()
        self.assertIn("SET status = 'reconciled'", render_verify(plan, finalize=True))
        sql = render_batch(plan, 1, fail_after_table="records")
        self.assertTrue(sql.startswith("BEGIN;"))
        self.assertTrue(sql.endswith("COMMIT;\n"))
        self.assertLess(sql.index("phase11_forced_failure"), sql.index("INSERT INTO v1_shadow.batches"))
        self.assertEqual(sql.count("AS phase11_state_matches;"), 2)
        self.assertNotIn("public.", sql.replace("public.purchases", ""))

    def test_invalid_ordinals_and_failure_injection_rejected(self):
        for ordinal in (0, 2, -1, True, "1; COMMIT;"):
            with self.subTest(ordinal=ordinal), self.assertRaises(ValueError):
                render_batch(sample_plan(), ordinal)
        with self.assertRaisesRegex(ValueError, "Failure injection"):
            render_batch(sample_plan(), 1, fail_after_table="records; DROP SCHEMA public;")
        plan = sample_plan()
        plan["batches"][0]["ordinal"] = 2
        with self.assertRaisesRegex(ValueError, "contiguous"):
            render_prepare(plan)

    def test_render_is_deterministic_without_local_time_or_random_ids(self):
        plan = sample_plan()
        self.assertEqual(render_batch(plan, 1), render_batch(deepcopy(plan), 1))
        self.assertEqual(render_prepare(plan), render_prepare(deepcopy(plan)))

    def test_large_evidence_is_transmitted_once_with_transaction_local_reuse(self):
        plan = sample_plan()
        evidence = "ab12cd" * 180_000
        plan["batches"][0]["tables"]["records"][0]["payload"]["large_evidence"] = evidence
        sql = render_batch(plan, 1)
        self.assertEqual(sql.count(evidence), 1)
        self.assertLess(len(sql.encode("utf-8")), 1_200_000)
        self.assertIn("CREATE TEMP TABLE phase11_expected_plan", sql)
        self.assertIn("ON COMMIT DROP", sql)
        self.assertEqual(sql.count("AS phase11_state_matches;"), 2)
        self.assertIn("payload -> 'batches' -> 0 -> 'tables' -> 'records'", sql)
        self.assertNotIn("CREATE TABLE", sql)
        self.assertNotIn("CREATE FUNCTION", sql)


if __name__ == "__main__":
    unittest.main()
