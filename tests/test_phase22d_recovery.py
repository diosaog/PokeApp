"""New 22D boundaries only; disposable Windows files, not emulator certification."""

import os
import subprocess
import sys
import unittest

import test_phase22_write_engine as fixtures

from app.launcher.save_activity import SaveActivityGate
from app.launcher.write_control import LocalWriteController
from app.launcher.write_files import WriteSafetyError
from tools.phase22b_cooperative_lifecycle_probe import _readline

# Keep a writable view alive AFTER closing both original file and mapping handles.
# Python mmap retains another file handle; that would test the wrong boundary.
MAPPED_CHILD = r"""import ctypes,sys
from ctypes import wintypes as w
from app.launcher.write_files import _kernel
k=_kernel()
k.CreateFileMappingW.argtypes=(w.HANDLE,w.LPVOID,w.DWORD,w.DWORD,w.DWORD,w.LPCWSTR)
k.CreateFileMappingW.restype=w.HANDLE
k.MapViewOfFile.argtypes=(w.HANDLE,w.DWORD,w.DWORD,w.DWORD,ctypes.c_size_t)
k.MapViewOfFile.restype=w.LPVOID
k.UnmapViewOfFile.argtypes=(w.LPCVOID,);k.UnmapViewOfFile.restype=w.BOOL
k.FlushViewOfFile.argtypes=(w.LPCVOID,ctypes.c_size_t);k.FlushViewOfFile.restype=w.BOOL
f=k.CreateFileW(sys.argv[1],0xC0000000,7,None,3,0,None)
assert f!=ctypes.c_void_p(-1).value,ctypes.get_last_error()
m=k.CreateFileMappingW(f,None,4,0,0,None)
assert m,ctypes.get_last_error()
view=k.MapViewOfFile(m,2,0,0,0)
assert view,ctypes.get_last_error()
assert k.CloseHandle(m) and k.CloseHandle(f)
try:
 b=ctypes.c_ubyte.from_address(view)
 original=b.value;b.value=original^1
 assert k.FlushViewOfFile(view,1)
 assert b.value==original^1
 b.value=original;assert k.FlushViewOfFile(view,1)
 print('VIEW_READY_HANDLES_CLOSED',flush=True)
 assert sys.stdin.readline().strip()=='CLOSE'
finally:
 assert k.UnmapViewOfFile(view)
"""


@unittest.skipUnless(os.name == "nt", "actual Windows required")
class RecoveryTests(unittest.TestCase):
    setUp = fixtures.TransactionTests.setUp
    tearDown = fixtures.TransactionTests.tearDown
    prepared = fixtures.TransactionTests.prepared
    applied = fixtures.TransactionTests.applied

    def test_writable_views_with_closed_handles_deny_handoff(self):
        self.prepared()
        record = self.engine._load(self.intent.operation_id)
        stage = self.engine._handoff_path(record, ".stage")
        for target in (self.target, stage):
            with self.subTest(target=target.name):
                expected = target.read_bytes()
                child = subprocess.Popen(
                    [sys.executable, "-c", MAPPED_CHILD, str(target)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    self.assertEqual("VIEW_READY_HANDLES_CLOSED", _readline(child))
                    self.assertEqual(expected, target.read_bytes())
                    with self.assertRaisesRegex(
                        WriteSafetyError, "FILE_LOCKED_OR_ACCESS_DENIED"
                    ):
                        with self.engine.handoff.held(target):
                            self.fail("writable mapped object admitted")
                finally:
                    if child.poll() is None:
                        child.stdin.write("CLOSE\n")
                        child.stdin.flush()
                    _, errors = child.communicate(timeout=10)
                    self.assertEqual(0, child.returncode, errors)
                self.assertEqual(expected, target.read_bytes())
                # Positive control: releasing the view admits the same object.
                with self.engine.handoff.held(target):
                    pass
        self.assertEqual(fixtures.SOURCE, self.target.read_bytes())
        self.assertEqual(fixtures.SOURCE, self.engine._backup_bytes(record))

    def test_external_file_in_restore_gap_is_preserved_after_restart(self):
        self.applied()
        candidate = self.target.read_bytes()

        def collide(point):
            if point == "restore_after_park":
                subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from pathlib import Path;import sys;Path(sys.argv[1]).open('xb').write(b'EXTERNAL RESTORE COLLISION')",
                        str(self.target),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )

        self.engine.fault_hook = collide
        result = self.engine.restore(
            self.intent.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("RECOVERY_REQUIRED", result.status)
        self.assertEqual("DESTINATION_OCCUPIED", result.error)
        fresh = fixtures.engine_at(self.root)
        result = fresh.restore(self.intent.operation_id, closed_emulator_confirmed=True)
        self.assertEqual("RECOVERY_REQUIRED", result.status)
        self.assertEqual(b"EXTERNAL RESTORE COLLISION", self.target.read_bytes())
        control = LocalWriteController(
            SaveActivityGate(), lambda: str(self.target), fresh
        )
        self.assertTrue(control.state()["restart_blocked_by_recovery"])
        self.assertFalse(control.state()["emulator_restart_allowed"])
        self.assertFalse(control.state()["emulator_qualified"])
        fresh.export_backup(
            self.intent.operation_id, destination=self.root / "original-copy"
        )
        fresh.export_backup(
            self.intent.operation_id,
            destination=self.root / "candidate-copy",
            role="before_restore",
        )
        self.assertEqual(fixtures.SOURCE, (self.root / "original-copy").read_bytes())
        self.assertEqual(candidate, (self.root / "candidate-copy").read_bytes())

    def test_identical_external_copy_is_not_mistaken_for_applied_identity(self):
        self.applied()
        candidate = self.target.read_bytes()
        external = self.root / "same-bytes-different-file"
        external.write_bytes(candidate)
        os.replace(external, self.target)
        fresh = fixtures.engine_at(self.root)
        prior = fresh.reconcile(self.intent.operation_id)
        self.assertEqual("APPLIED_VERIFIED", prior.status)
        self.assertFalse(prior.current_matches_receipt)
        denied = fresh.restore(self.intent.operation_id, closed_emulator_confirmed=True)
        self.assertEqual("RECOVERY_REQUIRED", denied.status)
        self.assertEqual(candidate, self.target.read_bytes())
        self.assertEqual(
            fixtures.SOURCE, fresh._backup_bytes(fresh._load(self.intent.operation_id))
        )


if __name__ == "__main__":
    unittest.main()
