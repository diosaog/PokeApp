"""Owner decision 2026-10-26: one daily restore point per save, kept 30 days."""

import json
import os
import stat
import tempfile
import unittest
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from app.launcher.write_engine import PreparedNative, WriteIntent
from app.launcher.write_files import WriteSafetyError
from tests.test_phase22_write_engine import SOURCE, TRAINER, engine_at

DAY = date(2026, 10, 26)


class ChainNative:
    """Synthetic writer that accepts its own outputs, so writes can be chained."""

    def validate_original(self, source, intent):
        if not source.startswith(SOURCE[:33]) or intent.trainer_key != TRAINER:
            raise ValueError("invalid isolated source")

    def prepare(self, source, intent):
        self.validate_original(source, intent)
        output = source[:-1] + bytes(((source[-1] + 1) % 256,))
        return PreparedNative(
            output,
            intent.game,
            TRAINER,
            sha256(source).hexdigest(),
            sha256(output).hexdigest(),
            {"marking": [0, 1], "preserved_unrelated": True},
            {"writer_version": "test-only"},
        )

    def verify(self, original, persisted, intent, prepared):
        if persisted != self.prepare(original, intent).output:
            raise ValueError("unintended semantic difference")


@unittest.skipUnless(os.name == "nt", "requires real Windows NTFS")
class DailyBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-daily-")
        self.root = Path(self.tmp.name)
        self.target = self.root / "main"
        self.target.write_bytes(SOURCE)
        self.today = DAY
        self.engine = self.fresh()
        self.counter = 0

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                p.chmod(stat.S_IREAD | stat.S_IWRITE)
        self.tmp.cleanup()

    def fresh(self, **kwargs):
        engine = engine_at(self.root, native=ChainNative(), **kwargs)
        engine.today = lambda: self.today
        return engine

    def intent(self):
        self.counter += 1
        return WriteIntent.create(
            expected_sha256=sha256(self.target.read_bytes()).hexdigest(),
            game="X",
            trainer_key=TRAINER,
            mutation={"kind": "test_marking", "new_value": self.counter},
        )

    def apply(self, engine=None):
        engine = engine or self.engine
        i = self.intent()
        engine.prepare(engine.enroll(self.target), i, closed_emulator_confirmed=True)
        receipt = engine.confirm(i.operation_id, closed_emulator_confirmed=True)
        self.assertEqual(receipt.status, "APPLIED_VERIFIED")
        return i.operation_id

    def folder(self):
        return self.engine._daily_folder(self.target)

    def daily(self):
        return {
            row["date"]: row
            for row in self.engine.backups_for(self.target)
            if row["role"] == "daily"
        }

    def transactional(self):
        return [
            row["operation_id"]
            for row in self.engine.backups_for(self.target)
            if row["role"] == "original"
        ]

    def test_several_writes_in_one_day_keep_the_first_state_and_latest_backup(self):
        before = [self.target.read_bytes()]
        ops = []
        for _ in range(3):
            ops.append(self.apply())
            before.append(self.target.read_bytes())
        point = self.folder() / f"{DAY.isoformat()}.sav"
        self.assertEqual(point.read_bytes(), SOURCE)  # never overwritten later
        self.assertEqual(list(self.daily()), [DAY.isoformat()])
        self.assertEqual(self.transactional(), [ops[-1]])  # latest good copy kept
        latest = self.engine._load(ops[-1])
        self.assertEqual(self.engine._backup_bytes(latest), before[2])
        for op in ops[:2]:
            record = self.engine._load(op)
            self.assertEqual(record["backup_retired"], "RETIRED")
            self.assertFalse(self.engine._backup_path(record).exists())
            # History stays terminal, never escalates to a recovery.
            self.assertEqual(self.engine.reconcile(op).status, "APPLIED_VERIFIED")
            with self.assertRaises(WriteSafetyError) as refused:
                self.engine.restore(op, closed_emulator_confirmed=True)
            self.assertEqual(str(refused.exception), "BACKUP_RETIRED_USE_DAILY_POINT")
        self.assertEqual(self.engine.pending(), ())
        # The day's point can be exported; the latest write can still be undone.
        copy = self.root / "export" / "daily.sav"
        copy.parent.mkdir()
        row = self.daily()[DAY.isoformat()]
        self.engine.export_backup(row["operation_id"], destination=copy, role="daily")
        self.assertEqual(copy.read_bytes(), SOURCE)
        restored = self.engine.restore(ops[-1], closed_emulator_confirmed=True)
        self.assertEqual(restored.status, "RESTORED_VERIFIED")
        self.assertEqual(self.target.read_bytes(), before[2])
        self.assertEqual(
            sorted(p.name for p in self.root.iterdir()),
            [
                "export",
                "main",
                "profile",
            ],
        )

    def test_date_change_creates_the_next_day_point_from_the_current_state(self):
        self.apply()
        self.apply()
        end_of_day = self.target.read_bytes()
        self.today = DAY + timedelta(days=1)
        self.apply()
        self.assertEqual(
            (self.folder() / f"{DAY.isoformat()}.sav").read_bytes(), SOURCE
        )
        self.assertEqual(
            (self.folder() / f"{self.today.isoformat()}.sav").read_bytes(), end_of_day
        )
        self.assertEqual(list(self.daily()), [self.today.isoformat(), DAY.isoformat()])
        self.assertEqual(len(self.transactional()), 1)

    def test_points_last_30_days_and_never_the_newest(self):
        self.apply()
        self.today = DAY + timedelta(days=29)
        self.apply()
        self.assertIn(DAY.isoformat(), self.daily())  # 29 days old: kept
        self.today = DAY + timedelta(days=30)
        self.apply()
        self.assertEqual(
            sorted(self.daily()),
            [(DAY + timedelta(days=29)).isoformat(), self.today.isoformat()],
        )
        self.assertFalse((self.folder() / f"{DAY.isoformat()}.json").exists())
        # A clock moved back never deletes the newest (future-dated) point.
        newest = self.today.isoformat()
        self.today = DAY + timedelta(days=2)
        self.apply()
        self.assertIn(newest, self.daily())
        self.assertIn(self.today.isoformat(), self.daily())

    def test_pending_failed_and_pre_policy_backups_are_never_retired(self):
        self.engine._apply_retention = lambda _op: None  # a run before the policy
        legacy = self.apply()
        self.engine = self.fresh(fault_hook=self.fail_at("before_park"))
        failed = self.intent()
        self.engine.prepare(
            self.engine.enroll(self.target), failed, closed_emulator_confirmed=True
        )
        receipt = self.engine.confirm(
            failed.operation_id, closed_emulator_confirmed=True
        )
        self.assertIn(receipt.status, ("REJECTED", "RECOVERY_REQUIRED"))
        self.assertEqual(
            self.target.read_bytes(),
            self.engine._backup_bytes(self.engine._load(failed.operation_id)),
        )
        self.engine = self.fresh()
        first = self.apply()
        waiting = self.intent()  # prepared, never confirmed
        self.engine.prepare(
            self.engine.enroll(self.target), waiting, closed_emulator_confirmed=True
        )
        self.apply()
        kept = set(self.transactional())
        self.assertTrue(
            {legacy, failed.operation_id, first, waiting.operation_id} <= kept
        )
        for op in (legacy, failed.operation_id, first, waiting.operation_id):
            record = self.engine._load(op)
            self.assertNotIn("backup_retired", record)
            self.assertTrue(self.engine._backup_path(record).exists())

    def fail_at(self, stage):
        def hook(current):
            if current == stage:
                raise WriteSafetyError("INJECTED_" + stage.upper())

        return hook

    def test_unrecognized_or_changed_files_are_never_cleaned(self):
        first = self.apply()
        folder = self.folder()
        foreign = {
            "notes.txt": b"user",
            "2026-01-01.sav": b"no manifest",
            "2026-01-02.sav": b"tampered",
            "2026-01-02.json": json.dumps({"date": "2026-01-02"}).encode(),
        }
        for name, data in foreign.items():
            (folder / name).write_bytes(data)
        record = self.engine._load(first)
        backup = self.engine._backup_path(record)
        backup.chmod(stat.S_IREAD | stat.S_IWRITE)
        backup.write_bytes(b"X" + SOURCE[1:])  # changed outside PokeApp
        self.today = DAY + timedelta(days=60)
        self.apply()
        for name, data in foreign.items():
            self.assertEqual((folder / name).read_bytes(), data)
        self.assertNotIn("2026-01-02", self.daily())
        self.assertEqual(backup.read_bytes(), b"X" + SOURCE[1:])
        self.assertNotIn("backup_retired", self.engine._load(first))

    def test_interrupted_retirement_is_completed_after_restart(self):
        first = self.apply()
        real_unlink = Path.unlink

        def crash(path, *args, **kwargs):
            if path.suffix == ".original":
                raise OSError("simulated crash")
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", crash):
            self.apply()
        record = self.engine._load(first)
        self.assertEqual(record["backup_retired"], "INTENT")
        self.assertTrue(self.engine._backup_path(record).exists())
        self.assertEqual(self.engine.reconcile(first).status, "APPLIED_VERIFIED")
        self.engine = self.fresh()  # restart
        self.apply()
        record = self.engine._load(first)
        self.assertEqual(record["backup_retired"], "RETIRED")
        self.assertFalse(self.engine._backup_path(record).exists())

    def test_interrupted_daily_point_keeps_every_transactional_backup(self):
        real = self.engine.files.create_verified

        def crash(path, data, **kwargs):
            if path.suffix == ".json":
                raise OSError("simulated crash")
            return real(path, data, **kwargs)

        with patch.object(self.engine.files, "create_verified", crash):
            first = self.apply()
        self.assertEqual(
            self.engine._load(first)["retention_error"], "RETENTION_SKIPPED"
        )
        self.engine = self.fresh()
        second = self.apply()
        self.assertEqual(self.daily(), {})  # unrecognized half point, kept as is
        self.assertTrue((self.folder() / f"{DAY.isoformat()}.sav").exists())
        self.assertEqual(set(self.transactional()), {first, second})
        self.assertEqual(self.engine._backup_bytes(self.engine._load(first)), SOURCE)

    def test_restored_records_keep_their_backups(self):
        self.apply()
        second = self.apply()
        self.engine.restore(second, closed_emulator_confirmed=True)
        self.apply()
        record = self.engine._load(second)
        self.assertEqual(record["status"], "RESTORED_VERIFIED")
        self.assertNotIn("backup_retired", record)
        self.assertTrue(self.engine._backup_path(record).exists())
        self.assertTrue(self.engine._backup_path(record, "before_restore").exists())


if __name__ == "__main__":
    unittest.main()
