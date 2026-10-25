"""Focused 25B proof of the prepared public quick-item switch.

Real native writer and the PRODUCTION engine configuration (no engineering
capability, real Windows process check) on a disposable fixture copy. The switch
is flipped only inside this process; the shipped registry stays empty.
"""

import argparse
import json
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path

from app.launcher import write_engine
from app.launcher.quick_items import inventory_view, quick_item_intent
from app.launcher.save_activity import SaveActivityGate
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import LocalWriteEngine, WriteIntent
from app.launcher.write_files import WriteSafetyError
from app.save_parser.writer import PkhexProcessWriter


def denied(call):
    try:
        call()
    except WriteSafetyError as error:
        return str(error)
    raise AssertionError("write admitted")


def main(args):
    native = PkhexProcessWriter(args.native_exe)
    root = Path(tempfile.mkdtemp(prefix="pokeapp-25b-"))
    report = {"status": "RUNNING", "checks": []}
    shipped = write_engine.PRODUCTION_MUTATIONS
    try:
        assert shipped == frozenset(), "shipped production registry must be empty"
        target = root / "main"
        data = (args.fixtures / "X" / "expected").read_bytes()
        target.write_bytes(data)
        engine = LocalWriteEngine(root / "profile", native)  # production configuration
        controller = LocalWriteController(
            SaveActivityGate(), lambda: str(target), engine
        )
        item = next(
            n
            for n in ("rare_candy", "heart_scale")
            if inventory_view(native, data)["items"][n]["addable"] >= 2
        )
        intent = quick_item_intent(native, data, item, 2)
        assert not engine.allows("add_item")
        assert (
            denied(lambda: controller.offer(intent, closed_emulator_confirmed=True))
            == "PRODUCTION_WRITES_DISABLED"
        )
        assert target.read_bytes() == data
        report["checks"].append(
            "shipped build: empty registry denies quick items; file untouched"
        )

        write_engine.PRODUCTION_MUTATIONS = frozenset(
            {"add_item", "revive", "test_marking"}
        )
        assert (
            engine.allows("add_item")
            and not engine.allows("revive")
            and not engine.allows("test_marking")
        )
        state = controller.offer(intent, closed_emulator_confirmed=True)
        assert state["status"] == "AWAITING_CONFIRMATION" and state["can_confirm"], (
            state
        )
        assert target.read_bytes() == data
        state = controller.confirm(
            state["operation_id"], closed_emulator_confirmed=True
        )
        assert state["status"] == "APPLIED_VERIFIED", state
        before = inventory_view(native, data)["items"][item]["count"]
        assert (
            inventory_view(native, target.read_bytes())["items"][item]["count"]
            == before + 2
        )
        record = engine._load(intent.operation_id)
        assert engine._backup_bytes(record) == data
        restarted = LocalWriteEngine(root / "profile", native)
        assert restarted.reconcile(intent.operation_id).status == "APPLIED_VERIFIED"
        current = target.read_bytes()
        marking = WriteIntent.create(
            expected_sha256=sha256(current).hexdigest(),
            game=intent.game,
            trainer_key=intent.trainer_key,
            mutation={
                "kind": "test_marking",
                "location": "box",
                "box_index": 0,
                "slot_index": 0,
                "expected_original": 0,
                "new_value": 1,
            },
        )
        assert (
            denied(lambda: controller.offer(marking, closed_emulator_confirmed=True))
            == "PRODUCTION_WRITES_DISABLED"
        )
        assert target.read_bytes() == current
        report["checks"].append(
            "flipped switch (test process only): production engine adds quick items with real process check, verified backup, confirm, readback and restart; other kinds still denied"
        )
        report["status"] = "PASS"
    finally:
        write_engine.PRODUCTION_MUTATIONS = shipped
        shutil.rmtree(root, ignore_errors=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("native-exe", "fixtures", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    main(p.parse_args())
