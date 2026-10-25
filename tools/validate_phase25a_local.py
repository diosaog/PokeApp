"""Focused 25A quick-item proof on disposable copies of retained public fixtures.

Real native PKHeX writer, existing journal/backups/controller and the Launcher
runtime command layer. No PostgreSQL, network, owner save or production path.
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

from app.launcher.quick_items import inventory_view, quick_item_intent
from app.launcher.runtime import LauncherRuntime
from app.launcher.save_activity import SaveActivityGate
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import EngineeringCapability, LocalWriteEngine
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.writer import NativeWriteError, PkhexProcessWriter

GAMES = ("X", "Y", "OR", "AS", "SN", "MN", "US", "UM")


def main(args):
    native = PkhexProcessWriter(args.native_exe)
    report = {"status": "RUNNING", "checks": [], "games": []}
    root = Path(tempfile.mkdtemp(prefix="pokeapp-25a-"))

    def passed(label):
        report["checks"].append(label)
        print("PASS", label, flush=True)

    def engine_at(folder, processes=list):
        return LocalWriteEngine(
            folder / "profile",
            native,
            files=WindowsWriteFiles(process_names=processes),
            engineering_capability=EngineeringCapability.for_fixture_root(folder),
        )

    try:
        for game in GAMES:
            folder = root / game
            folder.mkdir()
            target = folder / "main"
            original = (args.fixtures / game / "expected").read_bytes()
            target.write_bytes(original)
            view = inventory_view(native, original)
            item = next(
                (
                    n
                    for n in ("rare_candy", "heart_scale")
                    if view["items"][n]["addable"] >= 3
                ),
                None,
            )
            assert item, game + " no addable quick item"
            before = view["items"][item]["count"]
            controller = LocalWriteController(
                SaveActivityGate(), lambda t=target: str(t), engine_at(folder)
            )
            intent = quick_item_intent(native, original, item, 3)
            # Gen7 re-signing can fail closed for one exact output; try 2 then.
            try:
                state = controller.offer(intent, closed_emulator_confirmed=True)
            except WriteSafetyError:
                assert target.read_bytes() == original
                intent = quick_item_intent(native, original, item, 2)
                state = controller.offer(intent, closed_emulator_confirmed=True)
            quantity = intent.mutation["quantity"]
            assert (
                state["status"] == "AWAITING_CONFIRMATION"
                and target.read_bytes() == original
            )
            state = controller.confirm(
                state["operation_id"], closed_emulator_confirmed=True
            )
            assert state["status"] == "APPLIED_VERIFIED", state
            applied = target.read_bytes()
            assert (
                inventory_view(native, applied)["items"][item]["count"]
                == before + quantity
            )
            record = controller.engine._load(intent.operation_id)
            assert controller.engine._backup_bytes(record) == original
            # Lost reply: same operation reconciles; a re-offer of the old intent
            # can never apply twice.
            assert controller.reconcile()["status"] in ("APPLIED_VERIFIED", "IDLE")
            try:
                controller.offer(intent, closed_emulator_confirmed=True)
            except WriteSafetyError:
                pass
            assert target.read_bytes() == applied
            # Restarted Launcher journal: reconciles, never re-adds.
            restarted = LocalWriteController(
                SaveActivityGate(), lambda t=target: str(t), engine_at(folder)
            )
            assert (
                restarted.engine.reconcile(intent.operation_id).status
                == "APPLIED_VERIFIED"
            )
            assert (
                inventory_view(native, target.read_bytes())["items"][item]["count"]
                == before + quantity
            )
            report["games"].append(
                {
                    "game": game,
                    "item": item,
                    "before": before,
                    "added": quantity,
                    "status": "APPLIED_VERIFIED",
                }
            )
        passed(
            "8 titles: prepare with verified backup, explicit confirm, native readback, lost reply/re-offer/restart without duplication"
        )

        folder = root / "emulator"
        folder.mkdir()
        target = folder / "main"
        data = (args.fixtures / "X" / "expected").read_bytes()
        target.write_bytes(data)
        open_emulator = LocalWriteController(
            SaveActivityGate(),
            lambda: str(target),
            engine_at(folder, lambda: ["lime3ds.exe"]),
        )
        item = next(
            n
            for n in ("rare_candy", "heart_scale")
            if inventory_view(native, data)["items"][n]["addable"]
        )
        try:
            open_emulator.offer(
                quick_item_intent(native, data, item, 1), closed_emulator_confirmed=True
            )
            raise AssertionError("open emulator admitted")
        except WriteSafetyError as error:
            assert str(error) == "EMULATOR_RUNNING", error
        assert target.read_bytes() == data
        for bad in (b"\0" * 1000, data[:-1]):
            try:
                inventory_view(native, bad)
                raise AssertionError("incompatible save admitted")
            except NativeWriteError:
                pass
        for quantity in (0, -1, 1.5, 10_000):
            try:
                quick_item_intent(native, data, item, quantity)
                raise AssertionError("invalid quantity admitted")
            except WriteSafetyError:
                pass
        passed(
            "open Lime3DS process blocks before any change; incompatible save and invalid quantities refused"
        )

        folder = root / "runtime"
        folder.mkdir()
        target = folder / "main"
        target.write_bytes(data)
        runtime = LauncherRuntime(
            folder / "launcher",
            SaveInspector(PkhexProcessParser(args.native_exe)),
            client=Mock(origin="https://launcher.invalid"),
            token_store=Mock(),
            start=False,
        )
        production = runtime.writes
        runtime.writes = LocalWriteController(
            production.gate, lambda: str(target), production.engine
        )
        assert runtime.command("quick_items_refresh", {}) == {"status": "QUEUED"}
        runtime._write_step()
        state = runtime.state()
        assert state["quick_items"]["application_enabled"] is False
        runtime.command(
            "quick_item_offer",
            {"item": item, "quantity": 1, "closed_emulator_confirmed": True},
        )
        runtime._write_step()
        assert (
            "no está habilitado" in runtime.state()["quick_item_error"]
            and target.read_bytes() == data
        )
        assert not runtime.save_activity.recovery_required
        runtime.writes = LocalWriteController(
            runtime.save_activity,
            lambda: str(target),
            engine_at(folder),
            on_verified=runtime._invalidate_written_save,
        )
        runtime.command("quick_items_refresh", {})
        runtime._write_step()
        before = runtime.state()["quick_items"]["items"][item]["count"]
        runtime.command(
            "quick_item_offer",
            {"item": item, "quantity": 1, "closed_emulator_confirmed": True},
        )
        runtime._write_step()
        write = runtime.state()["write"]
        assert write["status"] == "AWAITING_CONFIRMATION" and write["can_confirm"], (
            runtime.state()["quick_item_error"]
        )
        runtime.command(
            "write_confirm",
            {"operation_id": write["operation_id"], "closed_emulator_confirmed": True},
        )
        runtime._write_step()
        state = runtime.state()
        assert (
            state["write"]["status"] == "APPLIED_VERIFIED"
            and state["quick_items"] is None
        )
        runtime.command("quick_items_refresh", {})
        runtime._write_step()
        assert runtime.state()["quick_items"]["items"][item]["count"] == before + 1
        passed(
            "runtime commands: production build reads only; engineering build prepares, waits for explicit confirm, applies once and re-reads"
        )
        report["status"] = "PASS"
    finally:
        shutil.rmtree(root, ignore_errors=True)
        report["cleanup"] = "disposable copies removed"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("native-exe", "fixtures", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    main(p.parse_args())
