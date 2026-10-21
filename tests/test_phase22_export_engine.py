"""Focused durable journal tests for verified new-file export."""

from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
import unittest

from app.launcher.write_engine import EngineeringCapability, LocalWriteEngine
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from test_phase22_write_engine import SOURCE, TestNative, intent


@unittest.skipUnless(os.name == "nt", "requires real Windows NTFS")
class ExportEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-phase22-export-engine-")
        self.root = Path(self.tmp.name)
        self.source = self.root / "main"
        self.source.write_bytes(SOURCE)
        self.destination = self.root / "exports"
        self.destination.mkdir()
        self.engine = LocalWriteEngine(
            self.root / "profile",
            TestNative(),
            files=WindowsWriteFiles(process_names=lambda: []),
            engineering_capability=EngineeringCapability.for_fixture_root(self.root),
        )
        self.intent = intent()
        self.target = self.engine.enroll(self.source)

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                path.chmod(stat.S_IWRITE | stat.S_IREAD)
        self.tmp.cleanup()

    def test_export_journal_is_distinct_and_source_is_unchanged(self):
        prepared = self.engine.prepare_export(
            self.target,
            self.intent,
            destination_directory=self.destination,
            closed_emulator_confirmed=True,
        )
        self.assertEqual("AWAITING_CONFIRMATION", prepared.status)
        self.assertEqual("export", prepared.mode)
        self.assertEqual(SOURCE, self.source.read_bytes())
        result = self.engine.confirm(
            prepared.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("EXPORTED_VERIFIED", result.status, result.error)
        self.assertFalse(result.applied_to_source)
        self.assertEqual(SOURCE, self.source.read_bytes())
        self.assertTrue(Path(result.export_path).is_file())
        self.assertEqual((), self.engine.pending())

    def test_replay_is_idempotent_and_occupied_name_fails_closed(self):
        self.engine.prepare_export(
            self.target,
            self.intent,
            destination_directory=self.destination,
            closed_emulator_confirmed=True,
        )
        first = self.engine.confirm(
            self.intent.operation_id, closed_emulator_confirmed=True
        )
        replay = self.engine.prepare_export(
            self.target,
            self.intent,
            destination_directory=self.destination,
            closed_emulator_confirmed=True,
        )
        self.assertEqual(first.status, replay.status)
        self.assertEqual(first.export_path, replay.export_path)
        self.assertEqual(1, len(list(self.destination.glob("export-*.save"))))

    def test_confirmation_is_explicit(self):
        with self.assertRaises(WriteSafetyError) as caught:
            self.engine.prepare_export(
                self.target,
                self.intent,
                destination_directory=self.destination,
                closed_emulator_confirmed=False,
            )
        self.assertEqual("CLOSE_EMULATOR_CONFIRMATION_REQUIRED", caught.exception.code)

    def test_partial_stage_never_becomes_export_receipt(self):
        def interrupt(stage):
            if stage == "export_stage_created":
                raise RuntimeError("simulated interruption")

        engine = LocalWriteEngine(
            self.root / "other-profile",
            TestNative(),
            files=WindowsWriteFiles(process_names=lambda: []),
            engineering_capability=EngineeringCapability.for_fixture_root(self.root),
            fault_hook=interrupt,
        )
        engine.prepare_export(
            self.target,
            self.intent,
            destination_directory=self.destination,
            closed_emulator_confirmed=True,
        )
        receipt = engine.confirm(
            self.intent.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("RECOVERY_REQUIRED", receipt.status)
        self.assertNotEqual("EXPORTED_VERIFIED", receipt.status)
        self.assertEqual(SOURCE, self.source.read_bytes())
