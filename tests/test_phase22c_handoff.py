"""New 22C boundaries on actual disposable Windows files; synthetic codec only."""

import errno
import json
import stat
import subprocess
import sys
import unittest
from dataclasses import replace
from queue import Queue
from unittest.mock import patch

import test_phase22_write_engine as fixtures
from test_phase22_write_engine import SOURCE, engine_at

from app.launcher.runtime import LauncherRuntime
from app.launcher.save_activity import SaveActivityGate, SaveBusy
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import LocalWriteEngine
from app.launcher.write_files import WriteSafetyError


class HandoffTests(unittest.TestCase):
    setUp = fixtures.TransactionTests.setUp
    tearDown = fixtures.TransactionTests.tearDown
    prepared = fixtures.TransactionTests.prepared
    applied = fixtures.TransactionTests.applied

    def test_verified_backup_and_intent_precede_native_preparation(self):
        calls = []
        native = self.engine.native.prepare

        def prepare(data, intent):
            record = self.engine._load(intent.operation_id)
            self.assertTrue(record["backup_verified"])
            self.assertEqual("BACKUP_VERIFIED", record["handoff_phase"])
            self.assertEqual(SOURCE, self.engine._backup_bytes(record))
            self.assertEqual(SOURCE, data)
            calls.append(True)
            return native(data, intent)

        with patch.object(self.engine.native, "prepare", side_effect=prepare):
            self.prepared()
        self.assertTrue(calls)

    def test_enospc_never_reaches_native_prepare_or_changes_source(self):
        with (
            patch.object(
                self.engine.files,
                "create_verified",
                side_effect=OSError(errno.ENOSPC, "full"),
            ),
            patch.object(self.engine.native, "prepare") as prepare,
        ):
            with self.assertRaises(WriteSafetyError):
                self.prepared()
            prepare.assert_not_called()
        self.assertEqual(SOURCE, self.target.read_bytes())
        self.assertFalse(self.engine.backups_for(self.target)[0]["verified"])

    def test_process_death_mid_backup_leaves_invalid_copy_and_original(self):
        script = """import os,sys
from pathlib import Path
from test_phase22_write_engine import engine_at,intent
root=Path(sys.argv[1]); engine=engine_at(root)
def partial(path,data,immutable=False):
    with path.open('xb') as f: f.write(data[:10]); f.flush(); os.fsync(f.fileno())
    os._exit(79)
engine.files.create_verified=partial
engine.prepare(engine.enroll(root/'main'),intent(),closed_emulator_confirmed=True)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(self.root)],
            capture_output=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(79, result.returncode, result.stderr)
        fresh = engine_at(self.root)
        self.assertFalse(fresh.backups_for(self.target)[0]["verified"])
        self.assertEqual(
            "RECOVERY_REQUIRED", fresh.reconcile(self.intent.operation_id).status
        )
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_copy_is_native_free_source_independent_and_never_overwrites(self):
        self.applied()
        self.target.unlink()  # Disposable target deliberately absent.
        offline = LocalWriteEngine(self.root / "profile", None)
        history = offline.backups_for(self.target)
        self.assertTrue(history[0]["verified"])
        self.assertFalse(history[0]["can_restore"])
        copy = self.root / "my-copy.sav"
        offline.export_backup(self.intent.operation_id, destination=copy)
        self.assertEqual(SOURCE, copy.read_bytes())
        with self.assertRaisesRegex(WriteSafetyError, "DESTINATION_OCCUPIED"):
            offline.export_backup(self.intent.operation_id, destination=copy)
        with self.assertRaisesRegex(WriteSafetyError, "UNSAFE_BACKUP_DESTINATION"):
            offline.export_backup(self.intent.operation_id, destination=self.target)
        self.assertFalse(self.target.exists())

    def test_corrupt_backup_cannot_export_or_restore(self):
        self.applied()
        path = self.engine._backup_path(self.engine._load(self.intent.operation_id))
        path.chmod(stat.S_IWRITE | stat.S_IREAD)
        path.write_bytes(b"corrupt")
        self.assertFalse(self.engine.backups_for(self.target)[0]["verified"])
        current = self.target.read_bytes()
        with self.assertRaisesRegex(WriteSafetyError, "BACKUP_INVALID"):
            self.engine.export_backup(
                self.intent.operation_id, destination=self.root / "copy"
            )
        self.assertEqual(
            "RECOVERY_REQUIRED",
            self.engine.restore(
                self.intent.operation_id, closed_emulator_confirmed=True
            ).status,
        )
        self.assertEqual(current, self.target.read_bytes())

    def test_restore_preserves_candidate_as_second_exportable_backup(self):
        self.applied()
        candidate = self.target.read_bytes()
        self.assertEqual(
            "RESTORED_VERIFIED",
            self.engine.restore(
                self.intent.operation_id, closed_emulator_confirmed=True
            ).status,
        )
        rows = self.engine.backups_for(self.target)
        self.assertEqual({"original", "before_restore"}, {r["role"] for r in rows})
        self.assertTrue(all(r["verified"] for r in rows))
        self.engine.export_backup(
            self.intent.operation_id,
            destination=self.root / "candidate-copy",
            role="before_restore",
        )
        self.assertEqual(candidate, (self.root / "candidate-copy").read_bytes())
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_restore_native_identity_mismatch_rejected_before_namespace_change(self):
        self.applied()
        current = self.target.read_bytes()
        with patch.object(
            self.engine.native,
            "validate_original",
            side_effect=ValueError("wrong game/trainer"),
        ):
            self.assertEqual(
                "RECOVERY_REQUIRED",
                self.engine.restore(
                    self.intent.operation_id, closed_emulator_confirmed=True
                ).status,
            )
        self.assertEqual(current, self.target.read_bytes())

    def test_three_restore_process_deaths_reconcile_before_resume(self):
        script = """import os,sys
from pathlib import Path
from test_phase22_write_engine import engine_at,intent
engine=engine_at(Path(sys.argv[1]),fault_hook=lambda at: os._exit(78) if at==sys.argv[2] else None)
engine.restore(intent().operation_id,closed_emulator_confirmed=True)
"""
        for point in ("before_restore", "restore_after_park", "after_restore"):
            root = self.root / point
            root.mkdir()
            target = root / "main"
            target.write_bytes(SOURCE)
            engine = engine_at(root)
            engine.prepare(
                engine.enroll(target), self.intent, closed_emulator_confirmed=True
            )
            engine.confirm(self.intent.operation_id, closed_emulator_confirmed=True)
            died = subprocess.run(
                [sys.executable, "-c", script, str(root), point],
                capture_output=True,
                check=False,
                timeout=20,
            )
            self.assertEqual(78, died.returncode, died.stderr)
            fresh = engine_at(root)
            if point == "restore_after_park":
                self.assertFalse(target.exists())
            receipt = fresh.restore(
                self.intent.operation_id, closed_emulator_confirmed=True
            )
            self.assertEqual("RESTORED_VERIFIED", receipt.status, receipt.error)
            self.assertEqual(SOURCE, target.read_bytes())

    def test_independent_writer_and_renamer_denied_at_real_engine_barriers(self):
        results = []

        def attempt(at):
            if at not in ("before_park", "after_publish"):
                return
            code = """from pathlib import Path
import sys,os,json
p=Path(sys.argv[1]); other=p.parent/'external'; other.write_bytes(b'external')
r=[]
for mode in ('write','replace'):
 try:
  if mode=='write': p.write_bytes(b'external')
  else: os.replace(other,p)
  r.append(False)
 except OSError: r.append(True)
print(json.dumps(r))
"""
            run = subprocess.run(
                [sys.executable, "-c", code, str(self.target)],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            results.extend(json.loads(run.stdout))

        self.engine.fault_hook = attempt
        self.assertEqual("APPLIED_VERIFIED", self.applied().status)
        self.assertEqual([True] * 4, results)

    def test_profile_selection_confirmation_and_sync_boundary(self):
        self.applied()
        gate = SaveActivityGate()
        selected = [str(self.target)]
        control = LocalWriteController(gate, lambda: selected[0], self.engine)
        control.refresh_backups()
        with self.assertRaisesRegex(WriteSafetyError, "RESTORE_CONFIRMATION_REQUIRED"):
            control.restore_backup(
                self.intent.operation_id,
                closed_emulator_confirmed=True,
                restore_confirmed=False,
            )
        with gate.reading(), self.assertRaises(SaveBusy):
            control.restore_backup(
                self.intent.operation_id,
                closed_emulator_confirmed=True,
                restore_confirmed=True,
            )
        selected[0] = str(self.root / "another-save")
        self.assertEqual([], control.state()["backups"])
        with self.assertRaisesRegex(WriteSafetyError, "BACKUP_SELECTION_CHANGED"):
            control.export_backup(self.intent.operation_id, str(self.root / "copy"))
        other = LocalWriteEngine(self.root / "other-profile", None)
        with self.assertRaisesRegex(WriteSafetyError, "WRITE_OPERATION_NOT_FOUND"):
            other.export_backup(
                self.intent.operation_id, destination=self.root / "copy"
            )

    def test_independent_launcher_processes_cannot_enter_during_handoff(self):
        outcomes = []
        script = """import sys
from pathlib import Path
from test_phase22_write_engine import TestNative,intent
from app.launcher.write_engine import LocalWriteEngine,EngineeringCapability
from app.launcher.write_files import WindowsWriteFiles,WriteSafetyError
root=Path(sys.argv[1]); profile=root/sys.argv[2]
engine=LocalWriteEngine(profile,TestNative(),files=WindowsWriteFiles(process_names=list),engineering_capability=EngineeringCapability.for_fixture_root(root))
try:
 engine.prepare(engine.enroll(root/'main'),intent(),closed_emulator_confirmed=True)
 print('UNEXPECTED_ENTRY')
except WriteSafetyError as error: print(error.code)
"""

        def attempt(point):
            if point != "before_park":
                return
            for profile in ("profile", "second-profile"):
                result = subprocess.run(
                    [sys.executable, "-c", script, str(self.root), profile],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=15,
                )
                outcomes.append(result.stdout.strip())

        self.engine.fault_hook = attempt
        self.assertEqual("APPLIED_VERIFIED", self.applied().status)
        self.assertEqual(["WRITE_ALREADY_RUNNING", "WRITE_ALREADY_RUNNING"], outcomes)

    def test_ipc_refuses_false_or_missing_restore_confirmation(self):
        runtime = object.__new__(LauncherRuntime)
        runtime.write_commands = Queue(maxsize=1)
        for values in (
            {},
            {"closed_emulator_confirmed": True},
            {"closed_emulator_confirmed": True, "restore_confirmed": "true"},
        ):
            with self.assertRaises(ValueError):
                runtime.command(
                    "backup_restore",
                    {"operation_id": self.intent.operation_id, **values},
                )
        self.assertTrue(runtime.write_commands.empty())

    def test_source_owner_mismatch_denied_before_backup(self):
        invalid = replace(self.intent, trainer_key="0" * 64)
        with self.assertRaises(WriteSafetyError):
            self.engine.prepare(self.enrolled, invalid, closed_emulator_confirmed=True)
        self.assertEqual([], list(self.engine.artifacts.iterdir()))


if __name__ == "__main__":
    unittest.main()
