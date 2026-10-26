"""26D: no dangerous residue beside saves, never at the cost of recovery."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from app.launcher.write_files import WriteSafetyError
from tests.test_phase22_write_engine import SOURCE, engine_at, intent


@unittest.skipUnless(os.name == "nt", "requires real Windows NTFS")
class ResidueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-26d-")
        self.root = Path(self.tmp.name)
        self.target = self.root / "main"
        self.target.write_bytes(SOURCE)
        self.engine = engine_at(self.root)
        self.i = intent()

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                p.chmod(stat.S_IREAD | stat.S_IWRITE)
        self.tmp.cleanup()

    def beside(self):
        return sorted(p.name for p in self.root.iterdir() if p.name != "profile")

    def apply(self, engine=None):
        engine = engine or self.engine
        engine.prepare(
            engine.enroll(self.target), self.i, closed_emulator_confirmed=True
        )
        return engine.confirm(self.i.operation_id, closed_emulator_confirmed=True)

    def test_verified_apply_and_restore_leave_only_the_save(self):
        self.assertEqual(self.apply().status, "APPLIED_VERIFIED")
        self.assertEqual(self.beside(), ["main"])  # no .displaced, .stage or .lock
        record = self.engine._load(self.i.operation_id)
        self.assertEqual(record["residue"], "REMOVED")
        self.assertEqual(self.engine._backup_bytes(record), SOURCE)  # backup kept
        self.assertEqual(
            self.engine.reconcile(self.i.operation_id).status, "APPLIED_VERIFIED"
        )
        restored = self.engine.restore(
            self.i.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual(restored.status, "RESTORED_VERIFIED")
        self.assertEqual(self.target.read_bytes(), SOURCE)
        self.assertEqual(self.beside(), ["main"])  # .restored-output retired too
        record = self.engine._load(self.i.operation_id)
        self.assertNotEqual(self.engine._backup_bytes(record, "before_restore"), SOURCE)

    def test_legacy_residue_is_retired_only_when_byte_identical(self):
        self.engine._retire_residue = lambda _op: None  # behave like a pre-26D run
        self.assertEqual(self.apply().status, "APPLIED_VERIFIED")
        displaced = self.root / f".pokeapp-{self.i.operation_id}.displaced"
        self.assertTrue(displaced.exists())
        fresh = engine_at(self.root)
        self.assertEqual(
            fresh.reconcile(self.i.operation_id).status, "APPLIED_VERIFIED"
        )
        self.assertFalse(displaced.exists())
        self.assertEqual(fresh._load(self.i.operation_id)["residue"], "REMOVED")

    def test_changed_parked_copy_is_kept_as_evidence(self):
        self.engine._retire_residue = lambda _op: None
        self.apply()
        displaced = self.root / f".pokeapp-{self.i.operation_id}.displaced"
        displaced.write_bytes(b"X" + SOURCE[1:])
        fresh = engine_at(self.root)
        fresh.reconcile(self.i.operation_id)
        self.assertTrue(displaced.exists())
        self.assertEqual(fresh._load(self.i.operation_id)["residue"], "KEPT_CHANGED")
        fresh.reconcile(self.i.operation_id)  # never retried into deletion
        self.assertTrue(displaced.exists())

    def test_process_killed_during_cleanup_completes_on_restart(self):
        script = (
            "import os,sys; from pathlib import Path; sys.path.insert(0,'tests'); "
            "from test_phase22_write_engine import engine_at,intent; "
            "root=Path(sys.argv[1]); engine=engine_at(root); i=intent(); "
            "engine.handoff.delete_held=lambda s: os._exit(77); "
            "engine.prepare(engine.enroll(root/'main'),i,closed_emulator_confirmed=True); "
            "engine.confirm(i.operation_id,closed_emulator_confirmed=True)"
        )
        done = subprocess.run(
            [sys.executable, "-c", script, str(self.root)], check=False
        )
        self.assertEqual(done.returncode, 77)
        fresh = engine_at(self.root)
        record = fresh._load(self.i.operation_id)
        self.assertEqual(
            (record["status"], record["residue"]),
            ("APPLIED_VERIFIED", "REMOVAL_INTENT"),
        )
        self.assertEqual(
            fresh.reconcile(self.i.operation_id).status, "APPLIED_VERIFIED"
        )
        self.assertEqual(self.beside(), ["main"])
        self.assertEqual(fresh._load(self.i.operation_id)["residue"], "REMOVED")
        self.assertEqual(fresh._backup_bytes(record), SOURCE)

    def test_unknown_files_beside_the_save_are_never_touched(self):
        foreign = {
            "main.bak": b"emulator",
            ".pokeapp-not-in-journal.displaced": b"unknown",
        }
        for name, data in foreign.items():
            (self.root / name).write_bytes(data)
        self.apply()
        for name, data in foreign.items():
            self.assertEqual((self.root / name).read_bytes(), data)

    def test_held_lock_blocks_and_is_not_deleted_under_its_holder(self):
        key = sha256(os.path.normcase("main").encode()).hexdigest()[:32]
        lock = self.root / f".pokeapp-write-{key}.lock"
        self.engine.prepare(
            self.engine.enroll(self.target), self.i, closed_emulator_confirmed=True
        )
        other = engine_at(self.root)
        with other.files.operation_lock(lock, delete_on_close=True):
            with self.assertRaises(WriteSafetyError) as blocked:
                self.engine.confirm(self.i.operation_id, closed_emulator_confirmed=True)
            self.assertEqual(str(blocked.exception), "WRITE_ALREADY_RUNNING")
            self.assertTrue(lock.exists())
            self.assertEqual(self.target.read_bytes(), SOURCE)
        self.assertEqual(
            self.engine.confirm(
                self.i.operation_id, closed_emulator_confirmed=True
            ).status,
            "APPLIED_VERIFIED",
        )
        self.assertEqual(self.beside(), ["main"])

    def safe_either_way(self, folder, *, read_only=False):
        """Applied and verified with nothing beside the save, or refused with the
        original byte-identical: never a partial or silent change."""
        folder.mkdir(parents=True)
        target = folder / "main"
        target.write_bytes(SOURCE)
        if read_only:
            target.chmod(stat.S_IREAD)
        engine = engine_at(self.root)
        try:
            engine.prepare(
                engine.enroll(target), self.i, closed_emulator_confirmed=True
            )
            status = engine.confirm(
                self.i.operation_id, closed_emulator_confirmed=True
            ).status
        except (OSError, WriteSafetyError) as error:
            status = "REFUSED:" + type(error).__name__
        if status == "APPLIED_VERIFIED":
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ["main"])
            self.assertEqual(
                engine._backup_bytes(engine._load(self.i.operation_id)), SOURCE
            )
        else:
            self.assertEqual(target.read_bytes(), SOURCE, status)
        return status

    def test_unicode_folder(self):
        self.assertEqual(
            self.safe_either_way(self.root / "Pokémon ñ 測試 ✓"), "APPLIED_VERIFIED"
        )

    def test_path_longer_than_260_characters_is_safe(self):
        deep = self.root
        while len(str(deep)) < 300:
            deep = deep / ("carpeta_larga_" + "x" * 30)
        self.safe_either_way(deep)

    def test_read_only_original_is_safe(self):
        self.safe_either_way(self.root / "ro", read_only=True)


if __name__ == "__main__":
    unittest.main()
