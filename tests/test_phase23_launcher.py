"""Focused bridge tests: real Windows files, synthetic native semantics only."""

import json
import os
import stat
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from test_phase22_write_engine import SOURCE, engine_at, intent

from app.launcher.item_use import EngineeringItemUse
from app.launcher.save_activity import SaveActivityGate, SaveBusy
from app.launcher.write_control import LocalWriteController
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError


class FakeAuthority:
    def __init__(self, authorization):
        self.a = authorization.copy()
        self.key = None
        self.completions = 0
        self.lost_claim = False

    def claim(self, aid, sid, tid, request):
        if self.key and self.key != request["claim_id"]:
            raise ValueError("claimed by another Launcher")
        self.key = request["claim_id"]
        self.a["status"] = "PENDING_APPLICATION"
        if self.lost_claim:
            self.lost_claim = False
            raise OSError("lost claim response")
        return self.a.copy()

    def complete(self, *args):
        self.completions += 1
        return self.a | {"status": "BLOCKED_UNCERTAIN"}


class SimulatedProcessDeath(BaseException):
    pass


@unittest.skipUnless(os.name == "nt", "Windows filesystem integration")
class ItemBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pokeapp-phase23-")
        self.root = Path(self.temp.name)
        self.target = self.root / "main"
        self.target.write_bytes(SOURCE)
        self.a = {
            k: str(uuid4())
            for k in (
                "id",
                "season_id",
                "trainer_id",
                "purchase_id",
                "target_pokemon_entity_id",
                "save_file_id",
                "operation_id",
                "identity_revision_id",
            )
        }
        self.a.update(
            effect_code="revive",
            save_sha256=intent().expected_sha256,
            status="PREPARED",
            expires_at=(datetime.now(UTC) + timedelta(minutes=15)).isoformat(),
        )
        self.repo = FakeAuthority(self.a)
        self.bridge = self.create()
        self.bind(self.bridge)

    def tearDown(self):
        for p in self.root.rglob("*"):
            if p.is_file() and not p.is_symlink():
                p.chmod(stat.S_IWRITE | stat.S_IREAD)
        self.temp.cleanup()

    def create(self, **kw):
        engine = engine_at(self.root, **kw)
        controller = LocalWriteController(
            SaveActivityGate(), lambda: str(self.target), engine
        )
        return EngineeringItemUse(
            controller,
            self.repo,
            season_id=self.a["season_id"],
            trainer_id=self.a["trainer_id"],
        )

    def bind(self, bridge):
        bridge.bind_fixture(
            self.a, intent(), pokemon_entity_id=self.a["target_pokemon_entity_id"]
        )

    def test_production_engine_and_unconfirmed_intents_are_denied(self):
        with self.assertRaisesRegex(WriteSafetyError, "ITEM_APPLICATION_DISABLED"):
            self.create(enabled=False)
        for value in (False, None, "true", 1):
            with self.assertRaises(WriteSafetyError):
                self.bridge.apply(self.a["id"], closed_emulator_confirmed=value)
        self.assertIsNone(self.repo.key)
        self.assertEqual(self.target.read_bytes(), SOURCE)

    def test_binding_cannot_change_pokemon_source_or_operation(self):
        for field in ("target_pokemon_entity_id", "save_sha256", "operation_id"):
            altered = self.a | {field: str(uuid4())}
            with self.assertRaises(WriteSafetyError):
                self.bridge.bind_fixture(
                    altered,
                    intent(),
                    pokemon_entity_id=self.a["target_pokemon_entity_id"],
                )
        self.assertEqual(self.target.read_bytes(), SOURCE)

    def test_sync_exclusion_and_stale_source(self):
        with self.bridge.controller.gate.reading(), self.assertRaises(SaveBusy):
            self.bridge.apply(self.a["id"], closed_emulator_confirmed=True)
        self.target.write_bytes(b"external preserved")
        with self.assertRaisesRegex(WriteSafetyError, "SOURCE_HASH_CHANGED"):
            self.bridge.apply(self.a["id"], closed_emulator_confirmed=True)
        self.assertEqual(self.target.read_bytes(), b"external preserved")
        self.assertEqual(self.repo.completions, 0)

    def test_open_emulator_prevents_apply(self):
        bridge = self.create(
            files=WindowsWriteFiles(process_names=lambda: ["azahar.exe"])
        )
        with self.assertRaisesRegex(WriteSafetyError, "EMULATOR_RUNNING"):
            bridge.apply(self.a["id"], closed_emulator_confirmed=True)
        self.assertTrue(bridge.controller.gate.recovery_required)
        self.assertEqual(self.target.read_bytes(), SOURCE)

    def test_claim_response_lost_is_reconciled_with_same_claim(self):
        self.repo.lost_claim = True
        with self.assertRaises(OSError):
            self.bridge.apply(self.a["id"], closed_emulator_confirmed=True)
        key = self.repo.key
        bridge = self.create()
        self.assertTrue(bridge.controller.gate.recovery_required)
        self.assertEqual(
            bridge.apply(self.a["id"], closed_emulator_confirmed=True),
            "LOCAL_VERIFIED_AWAITING_CONFIRMATION",
        )
        self.assertEqual(key, self.repo.key)
        self.assertEqual(bridge.complete(self.a["id"]), "BLOCKED_UNCERTAIN")

    def test_process_interruptions_before_during_after_publication(self):
        # Existing physical engine, not a second replacement implementation.
        for stage in ("before_park", "after_park", "after_publish"):
            with (
                self.subTest(stage=stage),
                tempfile.TemporaryDirectory(prefix="pokeapp-phase23-crash-") as temp,
            ):
                original_root, original_target = self.root, self.target
                self.root = Path(temp)
                self.target = self.root / "main"
                self.target.write_bytes(SOURCE)

                def fault(name, stage=stage):
                    if name == stage:
                        raise SimulatedProcessDeath()

                bridge = self.create(fault_hook=fault)
                self.bind(bridge)
                # This new disposable profile is a new experiment/authority.
                self.repo.key = None
                with self.assertRaises(SimulatedProcessDeath):
                    bridge.apply(self.a["id"], closed_emulator_confirmed=True)
                recovered = self.create()
                state = recovered.complete(self.a["id"])
                self.assertIn(state, ("RECOVERY_REQUIRED", "BLOCKED_UNCERTAIN"))
                self.assertTrue(recovered.controller.gate.recovery_required)
                _, original, _ = recovered.engine._materials(
                    recovered.engine._load(intent().operation_id)
                )
                self.assertEqual(original, SOURCE)
                if stage == "after_park":
                    self.assertFalse(self.target.exists())
                for p in self.root.rglob("*"):
                    if p.is_file():
                        p.chmod(stat.S_IWRITE | stat.S_IREAD)
                self.root, self.target = original_root, original_target

    def test_client_mutation_cannot_become_native_plan(self):
        self.repo.a["target_pokemon_entity_id"] = str(uuid4())
        with self.assertRaisesRegex(WriteSafetyError, "ITEM_RECEIPT_MISMATCH"):
            self.bridge.apply(self.a["id"], closed_emulator_confirmed=True)
        self.assertEqual(self.target.read_bytes(), SOURCE)

    def test_unchanged_bind_replay_and_selection_change(self):
        self.bind(self.bridge)
        _, record = self.bridge._load(self.a["id"])
        self.assertNotIn("pin", json.dumps(record).lower())
        self.target = self.root / "different"
        with self.assertRaises(WriteSafetyError):
            self.bridge.apply(self.a["id"], closed_emulator_confirmed=True)


if __name__ == "__main__":
    unittest.main()
