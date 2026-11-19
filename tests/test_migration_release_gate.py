"""Release gates preserve inventory and reject unproven migration/backup bytes."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from tools import phase30_apply_migrations as release


class MigrationReleaseGateTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.migration = root / "072_test.sql"
        self.migration.write_bytes(b"select 1;\n")
        self.digest = hashlib.sha256(self.migration.read_bytes()).hexdigest()
        self.archive = root / "backup.dump"
        self.archive.write_bytes(b"retained verified backup")
        manifest = {
            "captured_at": datetime.now(UTC).isoformat(),
            "archive": self.archive.name,
            "sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
        }
        self.manifest = root / "backup.manifest.json"
        self.manifest.write_text(json.dumps(manifest))
        self.rehearsal = root / "rehearsal.json"
        self.rehearsal.write_text(json.dumps({
            "archive": manifest["archive"], "archive_sha256": manifest["sha256"],
            "result": "PASS", "pending_sha256": {self.migration.name: self.digest},
        }))
        self.args = SimpleNamespace(backup=self.manifest, apply=True)
        self.reserved = 0
        self.physical = 0
        self.open_days = []
        patches = (
            patch.object(release, "PENDING", [self.migration]),
            patch.object(release, "DEPLOYED", []),
            patch.object(release, "EXPECTED_SHA256", {self.migration.name: self.digest}),
            patch.object(release, "history", return_value=[]),
            patch.object(release, "supabase_get", return_value={"status": "ACTIVE_HEALTHY"}),
            patch.object(release, "query", side_effect=self.query),
            patch.object(release.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout=self.migration.read_bytes())),
        )
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def query(self, sql):
        if "to_regclass" in sql:
            return [{"present": True}]
        if "item_deliveries" in sql:
            return [{"n": self.reserved}]
        if "opened_at::text as opened_at" in sql:
            return self.open_days
        if "a.id::text as id" in sql:
            # The in-flight operations themselves (086 release tooling).
            return [{"id": "op", "created_at": "2026-11-01T00:00:00+00:00"}]
        return [{"active_seasons": 0, "open_matchdays": len(self.open_days), "pending_purchases": 2,
                 "open_physical_authorizations": self.physical, "unsettled_transfer_legs": 0}]

    def test_owned_unused_inventory_is_preserved_without_forced_refund(self):
        self.assertEqual(release.preflight(self.args)["problems"], [])

    def test_reserved_physical_delivery_blocks_the_release(self):
        self.reserved = 1
        self.assertIn("an open matchday or reserved delivery: wait for it to finish",
                      release.preflight(self.args)["problems"])

    def test_changed_archive_is_rejected_even_if_rehearsal_says_pass(self):
        self.archive.write_bytes(b"different backup")
        self.assertIn("backup archive is missing or changed", release.preflight(self.args)["problems"])

    def test_unsettled_revive_or_robbery_blocks_the_release(self):
        self.physical = 1
        self.assertIn("an unsettled physical operation: wait for its journal to settle",
                      release.preflight(self.args)["problems"])

    def test_rehearsal_for_different_migration_bytes_is_rejected(self):
        data = json.loads(self.rehearsal.read_text())
        data["pending_sha256"][self.migration.name] = "0" * 64
        self.rehearsal.write_text(json.dumps(data))
        self.assertIn("pending migration bytes differ from this rehearsal",
                      release.preflight(self.args)["problems"])

    def test_uncommitted_migration_is_rejected(self):
        release.subprocess.run.return_value.stdout = b"older committed bytes"
        self.assertIn("072_test.sql is not the committed source", release.preflight(self.args)["problems"])

    def test_open_matchday_blocks_the_release(self):
        self.open_days = [{"id": "day", "opened_at": "2026-11-01T00:00:00+00:00"}]
        self.assertIn("an open matchday or reserved delivery: wait for it to finish",
                      release.preflight(self.args)["problems"])

    def test_named_matchday_already_open_in_the_rehearsed_backup_is_accepted(self):
        # 089: «Cancelar jornada» ships while the mistaken matchday is open.
        self.open_days = [{"id": "day", "opened_at": "2026-11-01T00:00:00+00:00"}]
        self.args.open_matchday_ok = ["day"]
        plan = release.preflight(self.args)
        self.assertEqual(plan["problems"], [])
        self.assertEqual(plan["activity"]["accepted_open_matchdays"], ["day"])

    def test_named_matchday_opened_after_the_backup_still_blocks(self):
        self.open_days = [{"id": "day", "opened_at": "2999-01-01T00:00:00+00:00"}]
        self.args.open_matchday_ok = ["day"]
        self.assertIn("an open matchday or reserved delivery: wait for it to finish",
                      release.preflight(self.args)["problems"])

    def test_naming_an_open_matchday_does_not_excuse_a_reserved_delivery(self):
        self.open_days = [{"id": "day", "opened_at": "2026-11-01T00:00:00+00:00"}]
        self.args.open_matchday_ok = ["day"]
        self.reserved = 1
        self.assertEqual(release.preflight(self.args)["problems"],
                         ["an open matchday or reserved delivery: wait for it to finish"])
