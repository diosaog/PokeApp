"""Real Windows/NTFS operations on disposable copies; synthetic semantics only.

The native writer fixture gate separately proves game formats. These tests never
claim their small byte fixture is a Pokémon save or real native-format evidence.
"""

from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.launcher.write_engine import (
    EngineeringCapability,
    LocalWriteEngine,
    PreparedNative,
    WriteIntent,
)
from app.launcher.write_files import (
    WindowsWriteFiles,
    WriteSafetyError,
    windows_process_names,
)


SOURCE = b"ENGINEERING FILESYSTEM TEST ONLY:" + bytes(range(256))
TRAINER = sha256(b"fixture trainer").hexdigest()
MUTATION = {
    "kind": "test_marking",
    "location": "box",
    "box_index": 0,
    "slot_index": 0,
    "expected_original": 0,
    "new_value": 1,
}


class TestNative:
    def prepare(self, source, intent):
        if source != SOURCE or intent.game != "X" or intent.trainer_key != TRAINER:
            raise ValueError("invalid isolated source")
        output = source[:-1] + bytes((source[-1] ^ 1,))
        return PreparedNative(
            output,
            "X",
            TRAINER,
            sha256(source).hexdigest(),
            sha256(output).hexdigest(),
            {"marking": [0, 1], "preserved_unrelated": True},
            {"writer_version": "test-only"},
        )

    def verify(self, original, persisted, intent, prepared):
        expected = self.prepare(original, intent)
        if persisted != expected.output or prepared.output_hash != expected.output_hash:
            raise ValueError("unintended semantic difference")


def intent():
    return WriteIntent.create(
        expected_sha256=sha256(SOURCE).hexdigest(),
        game="X",
        trainer_key=TRAINER,
        mutation=MUTATION,
    )


def engine_at(root, *, files=None, fault_hook=None, native=None, enabled=True):
    return LocalWriteEngine(
        root / "profile",
        native or TestNative(),
        files=files or WindowsWriteFiles(process_names=lambda: []),
        engineering_capability=EngineeringCapability.for_fixture_root(root)
        if enabled
        else None,
        fault_hook=fault_hook,
    )


@unittest.skipUnless(os.name == "nt", "requires real Windows NTFS")
class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-phase22-fs-")
        self.root = Path(self.tmp.name)
        self.target = self.root / "main"
        self.target.write_bytes(SOURCE)
        self.engine = engine_at(self.root)
        self.intent = intent()
        self.enrolled = self.engine.enroll(self.target)

    def tearDown(self):
        # Exact test-owned root; readonly backup preservation is cleared only by test cleanup.
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                path.chmod(stat.S_IWRITE | stat.S_IREAD)
        self.tmp.cleanup()

    def prepared(self):
        return self.engine.prepare(
            self.enrolled, self.intent, closed_emulator_confirmed=True
        )

    def applied(self):
        self.prepared()
        return self.engine.confirm(
            self.intent.operation_id, closed_emulator_confirmed=True
        )

    def assert_error(self, code, function):
        with self.assertRaises(WriteSafetyError) as caught:
            function()
        self.assertEqual(code, caught.exception.code)

    def test_real_ntfs_write_backup_replay_and_exact_restore(self):
        receipt = self.prepared()
        self.assertEqual("AWAITING_CONFIRMATION", receipt.status)
        self.assertEqual(SOURCE, self.target.read_bytes())
        self.assertEqual((receipt,), self.engine.pending())
        result = self.engine.confirm(
            receipt.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("APPLIED_VERIFIED", result.status, result.error)
        self.assertNotEqual(SOURCE, self.target.read_bytes())
        self.assertEqual(
            SOURCE,
            (
                self.root
                / "profile/write-backups"
                / (receipt.operation_id + ".original")
            ).read_bytes(),
        )
        duplicate = self.engine.confirm(
            receipt.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual(result, duplicate)
        restored = self.engine.restore(
            receipt.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("RESTORED_VERIFIED", restored.status, restored.error)
        self.assertEqual(SOURCE, self.target.read_bytes())
        self.assertEqual(
            restored,
            self.engine.restore(receipt.operation_id, closed_emulator_confirmed=True),
        )
        self.assertEqual((), self.engine.pending())

    def test_production_capability_absent_rejects_before_artifacts(self):
        disabled = engine_at(self.root, enabled=False)
        self.assert_error(
            "PRODUCTION_WRITES_DISABLED",
            lambda: disabled.prepare(
                self.enrolled, self.intent, closed_emulator_confirmed=True
            ),
        )
        self.assertEqual(SOURCE, self.target.read_bytes())
        self.assertEqual([], list(disabled.artifacts.iterdir()))

    def test_confirmation_required_at_both_steps(self):
        self.assert_error(
            "CLOSE_EMULATOR_CONFIRMATION_REQUIRED",
            lambda: self.engine.prepare(
                self.enrolled, self.intent, closed_emulator_confirmed=False
            ),
        )
        self.prepared()
        self.assert_error(
            "CLOSE_EMULATOR_CONFIRMATION_REQUIRED",
            lambda: self.engine.confirm(
                self.intent.operation_id, closed_emulator_confirmed=False
            ),
        )
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_emulator_running_or_failed_enumeration_denied(self):
        for names, expected in [
            (lambda: ["azahar.exe"], "EMULATOR_RUNNING"),
            (
                lambda: (_ for _ in ()).throw(OSError("denied")),
                "PROCESS_CHECK_UNAVAILABLE",
            ),
        ]:
            engine = engine_at(self.root, files=WindowsWriteFiles(process_names=names))
            self.assert_error(
                expected,
                lambda: engine.prepare(
                    self.enrolled, self.intent, closed_emulator_confirmed=True
                ),
            )
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_native_process_snapshot_is_nonempty(self):
        self.assertTrue(windows_process_names())

    def test_stale_source_hash_rejected_before_backup(self):
        self.target.write_bytes(SOURCE[:-1] + b"Q")
        self.assert_error("SOURCE_HASH_CHANGED", self.prepared)
        self.assertEqual([], list(self.engine.artifacts.iterdir()))

    def test_source_edit_between_confirmation_stages_preserved(self):
        self.prepared()
        later = SOURCE[:-1] + b"Q"
        self.target.write_bytes(later)
        receipt = self.engine.confirm(
            self.intent.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("REJECTED", receipt.status)
        self.assertEqual("SOURCE_HASH_CHANGED", receipt.error)
        self.assertEqual(later, self.target.read_bytes())

    def test_wrong_game_and_trainer_rejected(self):
        for candidate in (
            replace(self.intent, game="Y"),
            replace(self.intent, trainer_key="0" * 64),
        ):
            self.assert_error(
                "NATIVE_VERIFICATION_FAILED",
                lambda: self.engine.prepare(
                    self.enrolled, candidate, closed_emulator_confirmed=True
                ),
            )
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_native_unintended_diff_and_noop_rejected(self):
        class Wrong(TestNative):
            def prepare(self, source, intent):
                result = super().prepare(source, intent)
                return replace(
                    result, output=source, output_hash=sha256(source).hexdigest()
                )

        engine = engine_at(self.root, native=Wrong())
        self.assert_error(
            "INVALID_NATIVE_RESULT",
            lambda: engine.prepare(
                self.enrolled, self.intent, closed_emulator_confirmed=True
            ),
        )

    def test_windows_writer_handle_blocks_preparation(self):
        with self.target.open("r+b"):
            self.assert_error("FILE_LOCKED_OR_ACCESS_DENIED", self.prepared)
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_windows_guard_denies_external_writer(self):
        with self.engine.files.locked(self.enrolled):
            with self.assertRaises(OSError):
                self.target.open("r+b")

    def test_cross_profile_target_lease_blocks_another_engine(self):
        target_key = sha256(os.path.normcase(self.target.name).encode()).hexdigest()[
            :32
        ]
        target_lock = self.target.parent / (".pokeapp-write-" + target_key + ".lock")
        other_profile = self.root / "profile-two"
        other = LocalWriteEngine(
            other_profile,
            TestNative(),
            files=WindowsWriteFiles(process_names=lambda: []),
            engineering_capability=EngineeringCapability.for_fixture_root(self.root),
        )
        with self.engine.files.operation_lock(target_lock):
            self.assert_error(
                "WRITE_ALREADY_RUNNING",
                lambda: other.prepare(
                    self.enrolled, self.intent, closed_emulator_confirmed=True
                ),
            )
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_keyword_arguments_and_intent_reconstruction(self):
        result = self.engine.prepare(
            target=self.enrolled,
            intent=self.intent,
            closed_emulator_confirmed=True,
        )
        self.assertEqual(self.intent, self.engine.intent_for(result.operation_id))
        self.assertEqual(self.target, self.engine.target_path(result.operation_id))
        self.assertEqual(
            "APPLIED_VERIFIED",
            self.engine.confirm(
                operation_id=result.operation_id, closed_emulator_confirmed=True
            ).status,
        )

    def test_readonly_target_rejected(self):
        self.target.chmod(stat.S_IREAD)
        self.assert_error("TARGET_READ_ONLY", lambda: self.engine.enroll(self.target))

    def test_hardlink_rejected(self):
        alias = self.root / "alias"
        os.link(self.target, alias)
        self.assert_error(
            "REGULAR_SINGLE_LINK_FILE_REQUIRED", lambda: self.engine.enroll(alias)
        )

    def test_unc_ads_relative_and_device_paths_rejected(self):
        for path in (
            Path(r"\\localhost\c$\main"),
            Path(str(self.target) + ":stream"),
            Path("main"),
            Path(r"\\?\C:\main"),
        ):
            self.assert_error("UNSAFE_PATH", lambda: self.engine.enroll(path))

    def test_parent_junction_rejected_before_resolve(self):
        destination = self.root / "real"
        destination.mkdir()
        (destination / "main").write_bytes(SOURCE)
        junction = self.root / "junction"
        # mklink creates only the test-owned junction; no shell deletion is used.
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(destination)],
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr.decode(errors="replace"))
        try:
            self.assert_error(
                "REPARSE_POINT_REJECTED", lambda: self.engine.enroll(junction / "main")
            )
        finally:
            junction.rmdir()

    def test_selected_inode_replacement_rejected_even_if_bytes_equal(self):
        other = self.root / "replacement"
        other.write_bytes(SOURCE)
        os.replace(other, self.target)
        self.assert_error("TARGET_IDENTITY_CHANGED", self.prepared)

    def test_backup_failure_never_modifies_original(self):
        class Failure(WindowsWriteFiles):
            def create_verified(self, path, data, *, immutable=False):
                if immutable:
                    raise OSError("disk full")
                return super().create_verified(path, data, immutable=immutable)

        engine = engine_at(self.root, files=Failure(process_names=lambda: []))
        self.assert_error(
            "PREPARATION_FAILED",
            lambda: engine.prepare(
                self.enrolled, self.intent, closed_emulator_confirmed=True
            ),
        )
        self.assertEqual(SOURCE, self.target.read_bytes())
        self.assertEqual("REJECTED", engine.status(self.intent.operation_id).status)

    def test_short_stage_write_and_corruption_fail_before_original(self):
        class Failure(WindowsWriteFiles):
            def create_verified(self, path, data, *, immutable=False):
                if not immutable:
                    with path.open("xb") as stream:
                        stream.write(data[:10])
                        stream.flush()
                        os.fsync(stream.fileno())
                    raise WriteSafetyError("SHORT_WRITE")
                return super().create_verified(path, data, immutable=immutable)

        engine = engine_at(self.root, files=Failure(process_names=lambda: []))
        self.assert_error(
            "SHORT_WRITE",
            lambda: engine.prepare(
                self.enrolled, self.intent, closed_emulator_confirmed=True
            ),
        )
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_stage_corruption_rejected(self):
        self.prepared()
        stage = self.root / (".pokeapp-" + self.intent.operation_id + ".stage")
        stage.write_bytes(SOURCE)
        receipt = self.engine.confirm(
            self.intent.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("ARTIFACT_HASH_CHANGED", receipt.error)
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_backup_is_exclusive_and_tamper_prevents_confirm(self):
        self.prepared()
        backup = self.engine.artifacts / (self.intent.operation_id + ".original")
        with self.assertRaises(FileExistsError):
            self.engine.files.create_verified(backup, b"other")
        backup.chmod(stat.S_IWRITE | stat.S_IREAD)
        backup.write_bytes(SOURCE[:-1] + b"Q")
        self.assert_error(
            "BACKUP_INVALID",
            lambda: self.engine.confirm(
                self.intent.operation_id, closed_emulator_confirmed=True
            ),
        )
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_same_id_cannot_target_another_file(self):
        self.prepared()
        other = self.root / "second"
        other.write_bytes(SOURCE)
        self.assert_error(
            "OPERATION_ID_REUSED",
            lambda: self.engine.prepare(
                self.engine.enroll(other), self.intent, closed_emulator_confirmed=True
            ),
        )

    def test_restore_will_not_overwrite_later_legitimate_edit(self):
        self.assertEqual("APPLIED_VERIFIED", self.applied().status)
        later = SOURCE[:-1] + b"Q"
        self.target.write_bytes(later)
        prior = self.engine.reconcile(self.intent.operation_id)
        self.assertEqual("APPLIED_VERIFIED", prior.status)
        self.assertFalse(prior.current_matches_receipt)
        rejected = self.engine.restore(
            self.intent.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("RECOVERY_REQUIRED", rejected.status)
        self.assertEqual(later, self.target.read_bytes())
        self.assertTrue(
            (self.engine.artifacts / (self.intent.operation_id + ".original")).exists()
        )

    def test_replace_failure_is_reconciled_not_retried(self):
        self.prepared()
        with patch.object(
            self.engine.files, "replace", side_effect=OSError("replace failed")
        ) as mocked:
            result = self.engine.confirm(
                self.intent.operation_id, closed_emulator_confirmed=True
            )
            self.assertEqual("RECOVERY_REQUIRED", result.status)
            retried = self.engine.confirm(
                self.intent.operation_id, closed_emulator_confirmed=True
            )
            self.assertEqual("REJECTED", retried.status)
            self.assertEqual(1, mocked.call_count)
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_postwrite_failure_retains_backup_and_reconciles(self):
        self.prepared()
        with patch.object(
            self.engine.files, "flush", side_effect=OSError("flush failed")
        ):
            result = self.engine.confirm(
                self.intent.operation_id, closed_emulator_confirmed=True
            )
        self.assertEqual("RECOVERY_REQUIRED", result.status)
        self.assertNotEqual(SOURCE, self.target.read_bytes())
        fresh = engine_at(self.root)
        self.assertEqual(
            "APPLIED_VERIFIED", fresh.reconcile(self.intent.operation_id).status
        )

    def test_external_delete_sharing_race_is_not_silently_certified_or_restored(self):
        later = SOURCE[:-1] + b"Q"

        class Adversarial(WindowsWriteFiles):
            def replace(inner, target, stage, witness):
                impostor = target.parent / "external-change"
                impostor.write_bytes(later)
                # Another same-user actor can use the same delete-sharing
                # ReplaceFileW primitive; plain CRT rename is stricter here.
                super().replace(target, impostor, target.parent / "external-original")
                super().replace(target, stage, witness)

        engine = engine_at(self.root, files=Adversarial(process_names=lambda: []))
        engine.prepare(self.enrolled, self.intent, closed_emulator_confirmed=True)
        result = engine.confirm(
            self.intent.operation_id, closed_emulator_confirmed=True
        )
        self.assertEqual("RECOVERY_REQUIRED", result.status)
        self.assertEqual("DISPLACED_SOURCE_CHANGED", result.error)
        witness = self.root / (".pokeapp-" + self.intent.operation_id + ".displaced")
        self.assertEqual(later, witness.read_bytes())
        before_recovery = self.target.read_bytes()
        fresh = engine_at(self.root)
        self.assertEqual(
            "RECOVERY_REQUIRED", fresh.reconcile(self.intent.operation_id).status
        )
        self.assertEqual(
            "RECOVERY_REQUIRED",
            fresh.restore(
                self.intent.operation_id, closed_emulator_confirmed=True
            ).status,
        )
        self.assertEqual(before_recovery, self.target.read_bytes())
        self.assertEqual(later, witness.read_bytes())

    def test_public_receipt_omits_paths_hashes_native_and_private_trainer(self):
        receipt = self.prepared().public_status()
        self.assertEqual(
            {"operation_id", "status", "game", "error", "current_matches_receipt"},
            set(receipt),
        )
        self.assertNotIn(str(self.root), json.dumps(receipt))
        self.assertNotIn(TRAINER, json.dumps(receipt))

    def test_real_process_termination_recovery_at_each_commit_boundary(self):
        script = (
            "import os,sys; from pathlib import Path; "
            "sys.path.insert(0,'tests'); "
            "from test_phase22_write_engine import engine_at,intent; "
            "root=Path(sys.argv[1]); stage=sys.argv[2]; "
            "engine=engine_at(root,fault_hook=lambda at: os._exit(77) if at==stage else None); "
            "i=intent(); t=engine.enroll(root/'main'); "
            "engine.prepare(t,i,closed_emulator_confirmed=True); "
            "engine.confirm(i.operation_id,closed_emulator_confirmed=True)"
        )
        for checkpoint, expected in (
            ("prepared", "RECOVERY_REQUIRED"),
            ("backup_verified", "REJECTED"),
            ("stage_verified", "REJECTED"),
            ("before_replace", "REJECTED"),
            ("after_replace", "APPLIED_VERIFIED"),
            ("after_verify", "APPLIED_VERIFIED"),
        ):
            with self.subTest(checkpoint=checkpoint):
                isolated = self.root / checkpoint
                isolated.mkdir()
                (isolated / "main").write_bytes(SOURCE)
                result = subprocess.run(
                    [sys.executable, "-c", script, str(isolated), checkpoint],
                    capture_output=True,
                )
                self.assertEqual(
                    77, result.returncode, result.stderr.decode(errors="replace")
                )
                fresh = engine_at(isolated)
                receipt = fresh.reconcile(self.intent.operation_id)
                self.assertEqual(expected, receipt.status, receipt.error)
                expected_data = (
                    TestNative().prepare(SOURCE, self.intent).output
                    if expected == "APPLIED_VERIFIED"
                    else SOURCE
                )
                self.assertEqual(expected_data, (isolated / "main").read_bytes())


if __name__ == "__main__":
    unittest.main()
