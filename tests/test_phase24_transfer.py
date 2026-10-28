"""Paired journal failures with real disposable Windows files, synthetic semantics.

The separate PG/native validator proves game bytes and server coordination.
"""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.launcher.save_activity import SaveActivityGate
from app.launcher.transfer import EngineeringTransfer
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import WriteIntent
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from app.repositories.errors import PersistenceError
from tests.test_phase22_write_engine import SOURCE, TRAINER, engine_at


class Repository:
    def __init__(self, aid):
        self.state = {
            "authorization_id": aid,
            "side": "source",
            "status": "PENDING_SOURCE",
            "source_sha256": sha256(SOURCE).hexdigest(),
            "apply_started": False,
            "result_sha256": None,
            "verified": False,
        }
        self.claim = None
        self.failure = None

    def leg(self, request):
        op = request["operation"]
        if op == "ready":
            if self.claim is not None and self.claim != request["claim_id"]:
                raise PersistenceError("claim conflict")
            self.claim = request["claim_id"]
        elif op == "begin":
            if self.claim != request["claim_id"]:
                raise PersistenceError("claim conflict")
            self.state.update(apply_started=True, status="VERIFYING_SOURCE")
        if op == self.failure:
            self.failure = None
            raise PersistenceError("lost response")
        return dict(self.state)


@unittest.skipUnless(os.name == "nt", "requires Windows filesystem")
class TransferJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-phase24-journal-")
        self.root = Path(self.tmp.name)
        self.target = self.root / "main"
        self.target.write_bytes(SOURCE)
        self.aid, self.tid, self.sid = (str(uuid4()) for _ in range(3))
        self.intent = WriteIntent.create(
            game="X",
            trainer_key=TRAINER,
            expected_sha256=sha256(SOURCE).hexdigest(),
            mutation={"kind": "transfer_remove", "pair_id": self.aid},
        )
        self.repo = Repository(self.aid)
        self.bridge = self.restart()

    def restart(self, **kwargs):
        controller = LocalWriteController(
            SaveActivityGate(), lambda: str(self.target), engine_at(self.root, **kwargs)
        )
        bridge = EngineeringTransfer(
            controller, self.repo, season_id=self.sid, trainer_id=self.tid
        )
        bridge.bind(self.aid, "source", self.intent)
        return bridge

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                p.chmod(stat.S_IREAD | stat.S_IWRITE)
        self.tmp.cleanup()

    def prepare(self):
        return self.bridge.prepare(self.aid, closed_emulator_confirmed=True)

    def apply(self):
        return self.bridge.apply(self.aid, closed_emulator_confirmed=True)

    def test_confirmation_must_be_explicit(self):
        for value in (False, None, 1, "true", {}):
            with self.assertRaises(WriteSafetyError):
                self.bridge.prepare(self.aid, closed_emulator_confirmed=value)
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_ready_response_loss_preserves_claim_and_original(self):
        self.repo.failure = "ready"
        with self.assertRaises(PersistenceError):
            self.prepare()
        claim = self.repo.claim
        self.bridge = self.restart()
        self.prepare()
        self.assertEqual(claim, self.repo.claim)
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_begin_response_loss_does_not_write_before_reconciliation(self):
        self.prepare()
        self.repo.failure = "begin"
        with self.assertRaises(PersistenceError):
            self.apply()
        self.assertEqual(SOURCE, self.target.read_bytes())
        self.bridge = self.restart()
        self.apply()
        self.assertNotEqual(SOURCE, self.target.read_bytes())
        digest = sha256(self.target.read_bytes()).hexdigest()
        self.apply()
        self.assertEqual(digest, sha256(self.target.read_bytes()).hexdigest())

    def test_restart_after_publish_reconciles_and_does_not_reapply(self):
        class Crash(BaseException):
            pass

        def crash(stage):
            if stage == "after_publish":
                raise Crash()

        self.bridge = self.restart(fault_hook=crash)
        self.prepare()
        with self.assertRaises(Crash):
            self.apply()
        output = self.target.read_bytes()
        self.bridge = self.restart()
        self.apply()
        self.assertEqual(output, self.target.read_bytes())
        self.assertEqual(
            SOURCE,
            self.bridge.engine._backup_bytes(
                self.bridge.engine._load(self.intent.operation_id)
            ),
        )
        exported = self.root / "retained-original.sav"
        self.bridge.engine.export_backup(self.intent.operation_id, destination=exported)
        self.assertEqual(SOURCE, exported.read_bytes())

    def test_gap_conflict_is_preserved_and_unilateral_restore_denied(self):
        def conflict(stage):
            if stage == "after_park":
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from pathlib import Path;import sys;Path(sys.argv[1]).write_bytes(b'EXTERNAL')",
                        str(self.target),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(0, result.returncode)

        self.bridge = self.restart(fault_hook=conflict)
        self.prepare()
        self.assertEqual("RECOVERY_REQUIRED", self.apply()["status"])
        self.assertEqual(b"EXTERNAL", self.target.read_bytes())
        self.bridge = self.restart()
        self.assertEqual("RECOVERY_REQUIRED", self.apply()["status"])
        with self.assertRaisesRegex(
            WriteSafetyError, "TRANSFER_COORDINATED_RECOVERY_REQUIRED"
        ):
            self.bridge.engine.restore(
                self.intent.operation_id, closed_emulator_confirmed=True
            )
        self.assertEqual(
            SOURCE,
            self.bridge.engine._backup_bytes(
                self.bridge.engine._load(self.intent.operation_id)
            ),
        )

    def test_emulator_and_stale_source_fail_closed(self):
        self.bridge = self.restart(
            files=WindowsWriteFiles(process_names=lambda: ["lime3ds.exe"])
        )
        with self.assertRaises(WriteSafetyError):
            self.prepare()
        self.bridge = self.restart()
        self.target.write_bytes(b"CHANGED")
        with self.assertRaises(WriteSafetyError):
            self.prepare()
        self.assertEqual(b"CHANGED", self.target.read_bytes())

    def test_controller_never_offers_unilateral_apply_or_restore(self):
        self.prepare()
        self.assertFalse(self.bridge.controller.state()["can_confirm"])
        with self.assertRaises(WriteSafetyError):
            self.bridge.engine.confirm(
                self.intent.operation_id,
                closed_emulator_confirmed=True,
                paired_permit={"operation_id": self.intent.operation_id},
            )
        self.apply()
        self.assertFalse(
            self.bridge.engine.backups_for(str(self.target))[0]["can_restore"]
        )
        fresh = LocalWriteController(
            SaveActivityGate(), lambda: str(self.target), engine_at(self.root)
        )
        self.assertTrue(fresh.gate.recovery_required)
        self.assertIn("no está completado", fresh.state()["message"])
        self.assertFalse(fresh.state()["emulator_restart_allowed"])
        other = self.root / "other-save"
        other.write_bytes(SOURCE)
        switched = LocalWriteController(
            SaveActivityGate(), lambda: str(other), engine_at(self.root)
        )
        self.assertTrue(switched.gate.recovery_required)
        self.assertFalse(switched.state()["can_confirm"])

    def test_tampered_binding_and_other_profile_claim_rejected(self):
        self.prepare()
        with self.bridge.engine._db() as db:
            raw = json.loads(
                db.execute("select record from transfer_bindings").fetchone()[0]
            )
            raw["binding"]["trainer_id"] = str(uuid4())
            db.execute("update transfer_bindings set record=?", (json.dumps(raw),))
        with self.assertRaises(WriteSafetyError):
            self.apply()
        self.assertEqual(SOURCE, self.target.read_bytes())

    def test_same_path_other_process_lock_blocks_application(self):
        self.prepare()
        # Independent ordinary writer: no cooperative lock protocol.
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys;f=open(sys.argv[1],'r+b');print('ready',flush=True);sys.stdin.readline()",
                str(self.target),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual("ready", child.stdout.readline().strip())
            self.assertEqual("RECOVERY_REQUIRED", self.apply()["status"])
            self.assertEqual(SOURCE, self.target.read_bytes())
        finally:
            child.communicate("close\n", timeout=10)

    def test_production_engine_without_robbery_kinds_cannot_accept_transfer(self):
        # The shipped policy enables both legs (owner, 2026-10-28); with them
        # switched off the bridge still fails closed.
        from unittest.mock import patch

        import app.launcher.write_engine as write_engine

        controller = LocalWriteController(
            SaveActivityGate(),
            lambda: str(self.target),
            engine_at(self.root, enabled=False),
        )
        with patch.object(write_engine, "PRODUCTION_MUTATIONS", frozenset({"add_item"})):
            with self.assertRaisesRegex(WriteSafetyError, "TRANSFER_APPLICATION_DISABLED"):
                EngineeringTransfer(
                    controller, self.repo, season_id=self.sid, trainer_id=self.tid
                )
        # Shipped policy: the production engine accepts the bridge.
        EngineeringTransfer(controller, self.repo, season_id=self.sid, trainer_id=self.tid)
