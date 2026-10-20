"""Local write/read coordination without owner files or remote effects."""

import threading
import unittest
import os
from pathlib import Path
import stat
import tempfile
from dataclasses import replace
from unittest.mock import Mock, patch

from phase9_fixtures import FakeParser
from app.save_parser.adapter import SaveInspector
from app.launcher.runtime import LauncherRuntime

from app.launcher.save_activity import SaveActivityGate, SaveBusy
from app.launcher.write_control import LocalWriteController
from app.launcher.write_files import WriteSafetyError
from test_phase22_write_engine import SOURCE, engine_at, intent


class SaveActivityTests(unittest.TestCase):
    def test_slow_sync_does_not_block_offline_read(self):
        gate = SaveActivityGate()
        acquired = threading.Event()
        with gate.reading():
            thread = threading.Thread(target=lambda: self._read(gate, acquired))
            thread.start()
            self.assertTrue(acquired.wait(1))
            thread.join(1)
            with self.assertRaises(SaveBusy):
                with gate.writing():
                    self.fail("sync and write overlapped")
        with gate.writing():
            pass

    @staticmethod
    def _read(gate, acquired):
        with gate.reading():
            acquired.set()

    def test_write_excludes_sync_selection_and_second_writer(self):
        gate = SaveActivityGate()
        with gate.writing():
            for lease in (gate.reading, gate.writing):
                with self.assertRaises(SaveBusy):
                    with lease():
                        self.fail("write lease bypassed")
        with gate.reading():
            pass

    def test_error_releases_lease_but_recovery_blocks_sync(self):
        gate = SaveActivityGate()
        with self.assertRaises(ValueError):
            with gate.writing():
                raise ValueError("injected")
        gate.recovery_required = True
        for lease in (gate.reading, gate.writing):
            with self.assertRaises(SaveBusy):
                with lease():
                    self.fail("unreconciled write bypassed")
        with gate.writing(recovery=True):
            gate.recovery_required = False
        with gate.reading():
            pass


class RuntimeReadOnlyFallbackTests(unittest.TestCase):
    def runtime(self, profile):
        parser = FakeParser()
        parser.executable = Path(__file__)  # never executed by these isolated tests
        with (
            patch("app.launcher.runtime.PkhexProcessWriter", return_value=Mock()),
            patch(
                "app.launcher.runtime.LocalWriteEngine",
                side_effect=WriteSafetyError("LOCAL_NTFS_REQUIRED"),
            ),
        ):
            runtime = LauncherRuntime(
                profile,
                SaveInspector(parser),
                start=False,
                client=Mock(origin="https://invalid.example"),
                token_store=Mock(),
            )
        self.addCleanup(runtime.close)
        return runtime

    def test_unsupported_writer_without_recovery_material_preserves_reading(self):
        with tempfile.TemporaryDirectory(prefix="pokeapp-phase22-fallback-") as temp:
            runtime = self.runtime(Path(temp))
            self.assertFalse(runtime.save_activity.recovery_required)
            with runtime.save_activity.reading():
                self.assertEqual(runtime.state()["write"]["status"], "IDLE")

    def test_existing_unreadable_journal_blocks_sync_even_when_engine_unavailable(self):
        with tempfile.TemporaryDirectory(prefix="pokeapp-phase22-fallback-") as temp:
            root = Path(temp)
            (root / "writes").mkdir()
            (root / "writes/physical-writes.sqlite3").write_bytes(b"unreadable")
            runtime = self.runtime(root)
            self.assertTrue(runtime.save_activity.recovery_required)
            with self.assertRaises(SaveBusy):
                with runtime.save_activity.reading():
                    self.fail("unreadable prior journal must block uploads")
            self.assertEqual(runtime.state()["write"]["status"], "RECOVERY_REQUIRED")

    def test_empty_partially_created_writer_directory_is_not_a_pending_write(self):
        with tempfile.TemporaryDirectory(prefix="pokeapp-phase22-fallback-") as temp:
            root = Path(temp)
            (root / "writes/write-backups").mkdir(parents=True)
            runtime = self.runtime(root)
            self.assertFalse(runtime.save_activity.recovery_required)


@unittest.skipUnless(os.name == "nt", "actual Windows filesystem integration")
class LocalConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pokeapp-phase22-control-")
        self.root = Path(self.temp.name)
        self.target = self.root / "main"
        self.target.write_bytes(SOURCE)
        self.selected = self.target
        self.gate = SaveActivityGate()
        self.engine = engine_at(self.root)
        self.control = LocalWriteController(
            self.gate, lambda: self.selected, self.engine
        )

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                path.chmod(stat.S_IWRITE | stat.S_IREAD)
        self.temp.cleanup()

    def offer(self):
        return self.control.offer(intent(), closed_emulator_confirmed=True)

    def test_confirmation_requires_exact_local_intent_and_closed_game(self):
        pending = self.offer()
        self.assertEqual("AWAITING_CONFIRMATION", pending["status"])
        self.assertIn("caja 1, posición 1, de 0 a 1", pending["description"])
        self.assertNotIn(str(self.target), str(pending))
        self.assertEqual(SOURCE, self.target.read_bytes())
        for identifier, confirmed in (
            ("forged", True),
            (pending["operation_id"], False),
        ):
            with self.assertRaises(WriteSafetyError):
                self.control.confirm(identifier, closed_emulator_confirmed=confirmed)
        result = self.control.confirm(
            pending["operation_id"], closed_emulator_confirmed=True
        )
        self.assertEqual("APPLIED_VERIFIED", result["status"])
        self.assertFalse(result["can_confirm"])

    def test_changed_selection_cannot_confirm_old_intent(self):
        pending = self.offer()
        other = self.root / "other"
        other.write_bytes(SOURCE)
        self.selected = other
        with self.assertRaisesRegex(WriteSafetyError, "WRITE_TARGET_CHANGED"):
            self.control.confirm(
                pending["operation_id"], closed_emulator_confirmed=True
            )
        self.assertEqual(SOURCE, self.target.read_bytes())
        self.assertEqual(SOURCE, other.read_bytes())

    def test_restart_reconciles_without_write_and_redisplays_exact_plan(self):
        pending = self.offer()
        restarted = LocalWriteController(
            self.gate, lambda: self.selected, engine_at(self.root)
        )
        self.assertEqual("RECOVERY_REQUIRED", restarted.state()["status"])
        with self.assertRaises(SaveBusy):
            with self.gate.reading():
                self.fail("sync must wait for recovery")
        restored = restarted.reconcile()
        self.assertEqual(pending["description"], restored["description"])
        self.assertEqual("AWAITING_CONFIRMATION", restored["status"])
        self.assertEqual(SOURCE, self.target.read_bytes())
        final = restarted.confirm(
            pending["operation_id"], closed_emulator_confirmed=True
        )
        self.assertEqual("APPLIED_VERIFIED", final["status"])

    def test_active_sync_refuses_write_without_losing_pending_confirmation(self):
        pending = self.offer()
        with self.gate.reading():
            with self.assertRaises(SaveBusy):
                self.control.confirm(
                    pending["operation_id"], closed_emulator_confirmed=True
                )
        self.assertTrue(self.control.state()["can_confirm"])
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_no_production_capability_or_renderer_plan_can_authorize_mutation(self):
        production = LocalWriteController(
            self.gate, lambda: self.selected, engine_at(self.root, enabled=False)
        )
        with self.assertRaisesRegex(WriteSafetyError, "PRODUCTION_WRITES_DISABLED"):
            production.offer(intent(), closed_emulator_confirmed=True)
        self.assertFalse(production.state()["production_operations_enabled"])
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_later_edit_is_retained_and_sync_stays_blocked(self):
        self.offer()
        self.target.write_bytes(b"later legitimate save")
        result = self.control.reconcile()
        self.assertEqual("RECOVERY_REQUIRED", result["status"])
        self.assertEqual(b"later legitimate save", self.target.read_bytes())
        with self.assertRaises(SaveBusy):
            with self.gate.reading():
                self.fail("unreconciled target must not be synced")

    def test_failed_new_offer_cannot_relabel_previous_confirmation(self):
        previous = self.offer()
        different = replace(intent(), mutation=intent().mutation | {"new_value": 2})
        with (
            patch.object(
                self.engine, "prepare", side_effect=WriteSafetyError("UNSAFE_TARGET")
            ),
            self.assertRaises(WriteSafetyError),
        ):
            self.control.offer(different, closed_emulator_confirmed=True)
        state = self.control.state()
        self.assertEqual(state["operation_id"], previous["operation_id"])
        self.assertEqual(state["description"], previous["description"])
        self.assertTrue(state["can_confirm"])

    def test_slow_native_operation_keeps_state_readable_without_reconfirmation(self):
        pending = self.offer()
        started, release, state_ready = (threading.Event() for _ in range(3))
        states, failures = [], []
        native_confirm = self.engine.confirm

        def delayed(*args, **kwargs):
            started.set()
            if not release.wait(3):
                raise RuntimeError("test release timeout")
            return native_confirm(*args, **kwargs)

        def confirm():
            try:
                self.control.confirm(
                    pending["operation_id"], closed_emulator_confirmed=True
                )
            except Exception as error:
                failures.append(error)

        def read():
            states.append(self.control.state())
            state_ready.set()

        with patch.object(self.engine, "confirm", side_effect=delayed):
            worker = threading.Thread(target=confirm)
            worker.start()
            self.assertTrue(started.wait(1))
            reader = threading.Thread(target=read)
            reader.start()
            try:
                self.assertTrue(
                    state_ready.wait(1), "IPC state waited for native write"
                )
                self.assertTrue(states[0]["busy"])
                self.assertFalse(states[0]["can_confirm"])
            finally:
                release.set()
                worker.join(3)
                reader.join(3)
        self.assertEqual(failures, [])

    def test_verified_write_invalidates_upload_receipt_before_releasing_lease(self):
        runtime = object.__new__(LauncherRuntime)
        runtime.lock = threading.Lock()
        runtime.value = {
            "local_status": "READY",
            "receipt_id": "old",
            "cloud_receipt": {"save_id": "old"},
            "observation": {"private": "old"},
        }
        runtime.receipt = object()
        runtime.watch = object()
        callback_checked = []

        def invalidate():
            with self.assertRaises(SaveBusy):
                with self.gate.reading():
                    self.fail("cloud could upload between replacement and invalidation")
            runtime._invalidate_written_save()
            callback_checked.append(True)

        self.control.on_verified = invalidate
        pending = self.offer()
        self.control.confirm(pending["operation_id"], closed_emulator_confirmed=True)
        self.assertEqual(callback_checked, [True])
        with self.gate.reading():
            self.assertIsNone(runtime.receipt)
            self.assertIsNone(runtime.value["cloud_receipt"])
            self.assertNotEqual(runtime.value["local_status"], "READY")

    def test_invalidation_failure_preserves_recovery_block(self):
        self.control.on_verified = Mock(side_effect=RuntimeError("cache failure"))
        pending = self.offer()
        with self.assertRaises(RuntimeError):
            self.control.confirm(
                pending["operation_id"], closed_emulator_confirmed=True
            )
        self.assertTrue(self.gate.recovery_required)
        with self.assertRaises(SaveBusy):
            with self.gate.reading():
                self.fail("failed invalidation must not allow stale upload")
