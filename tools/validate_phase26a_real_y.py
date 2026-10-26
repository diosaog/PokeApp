"""Phase26A real-save acceptance on COPIES of an owner-authorized Pokémon Y save.

All paths are arguments; nothing personal is stored in code. The original is
only hashed and compared, never written. An isolated portable Lime3DS proves the
real emulator process blocks writes and never touches the owner's Lime3DS data.
"""

import argparse
import json
import subprocess
import time
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

from app.launcher.quick_items import inventory_view, quick_item_intent
from app.launcher.runtime import LauncherRuntime
from app.launcher.save_activity import SaveActivityGate
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import EngineeringCapability, LocalWriteEngine
from app.launcher.write_files import WriteSafetyError
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.writer import PkhexProcessWriter


class Interrupted(Exception):
    pass


def snapshot(folder):
    return sorted(
        (
            str(p.relative_to(folder)),
            p.stat().st_mtime_ns,
            p.stat().st_size if p.is_file() else 0,
        )
        for p in folder.rglob("*")
    )


def running(pid):
    out = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return str(pid) in out


def main(a):
    h = lambda b: sha256(b).hexdigest()
    native, parser = PkhexProcessWriter(a.native_exe), PkhexProcessParser(a.native_exe)
    original = a.original.read_bytes()
    original_hash = h(original)
    report = {"status": "RUNNING", "checks": [], "original_sha256": original_hash}

    def passed(label):
        report["checks"].append(label)
        print("PASS", label, flush=True)

    def engine_at(profile, **kwargs):
        return LocalWriteEngine(
            profile,
            native,
            engineering_capability=EngineeringCapability.for_fixture_root(a.iso_root),
            **kwargs,
        )

    work = a.work
    assert h(work.read_bytes()) == original_hash, "working copy must start identical"
    observed_before = parser.parse(original).model_dump(mode="json")
    try:
        # 1. Real Lime3DS process: isolated portable instance.
        appdata_before = snapshot(a.appdata_lime)
        emulator = subprocess.Popen([str(a.lime3ds_exe)], cwd=a.lime3ds_exe.parent)
        time.sleep(8)
        assert running(emulator.pid), "isolated Lime3DS did not start"
        blocked = LocalWriteController(
            SaveActivityGate(), lambda: str(work), engine_at(a.profile / "blocked")
        )
        intent = quick_item_intent(native, work.read_bytes(), "rare_candy", 1)
        try:
            blocked.offer(intent, closed_emulator_confirmed=True)
            raise AssertionError("write admitted while Lime3DS was open")
        except WriteSafetyError as error:
            assert str(error) == "EMULATOR_RUNNING", error
        assert h(work.read_bytes()) == original_hash
        subprocess.run(
            ["taskkill", "/PID", str(emulator.pid)], capture_output=True, check=False
        )
        for _ in range(30):
            if emulator.poll() is not None:
                break
            time.sleep(1)
        assert emulator.poll() is not None, "isolated Lime3DS did not close gracefully"
        assert snapshot(a.appdata_lime) == appdata_before, (
            "owner's Lime3DS data changed"
        )
        assert (
            any((a.lime3ds_exe.parent / "user").rglob("*.log"))
            or (a.lime3ds_exe.parent / "user" / "log").exists()
        )
        passed(
            "real lime3ds.exe (isolated portable) detected: write refused while open, graceful close, owner's Lime3DS data untouched"
        )

        # 2. Quick items through the runtime commands on the working copy.
        runtime = LauncherRuntime(
            a.profile / "launcher",
            SaveInspector(parser),
            client=Mock(origin="https://launcher.invalid"),
            token_store=Mock(),
            start=False,
        )
        runtime.writes = LocalWriteController(
            runtime.save_activity,
            lambda: str(work),
            engine_at(a.profile / "writes"),
            on_verified=runtime._invalidate_written_save,
        )

        def run(name, args=None):
            assert runtime.command(name, args or {}) == {"status": "QUEUED"}
            runtime._write_step()
            return runtime.state()

        counts = run("quick_items_refresh")["quick_items"]["items"]
        added = {}
        for item, quantity in (
            ("rare_candy", a.rare_candy),
            ("heart_scale", a.heart_scale),
        ):
            before = counts[item]["count"]
            state = run(
                "quick_item_offer",
                {"item": item, "quantity": quantity, "closed_emulator_confirmed": True},
            )
            assert state["write"]["status"] == "AWAITING_CONFIRMATION", state[
                "quick_item_error"
            ]
            op = state["write"]["operation_id"]
            state = run(
                "write_confirm", {"operation_id": op, "closed_emulator_confirmed": True}
            )
            assert state["write"]["status"] == "APPLIED_VERIFIED", state
            counts = run("quick_items_refresh")["quick_items"]["items"]
            assert counts[item]["count"] == before + quantity
            added[item] = {
                "before": before,
                "after": counts[item]["count"],
                "operation_id": op,
            }
        after = work.read_bytes()
        assert parser.parse(after).model_dump(mode="json") == observed_before, (
            "Pokémon/trainer data changed"
        )
        report["quick_items"] = added
        report["work_sha256"] = h(after)
        passed(
            f"Rare Candy +{a.rare_candy} and Heart Scale +{a.heart_scale} applied with verified backup, explicit confirm and native readback; party, boxes and trainer identical"
        )

        # 3. Idempotency: re-offer the old intent and restart never add again.
        stale = quick_item_intent(native, original, "rare_candy", a.rare_candy)
        try:
            runtime.writes.offer(stale, closed_emulator_confirmed=True)
        except WriteSafetyError:
            pass
        restarted = engine_at(a.profile / "writes")
        for value in added.values():
            assert (
                restarted.reconcile(value["operation_id"]).status == "APPLIED_VERIFIED"
            )
        assert work.read_bytes() == after
        passed(
            "lost reply / re-offer of the original intent and Launcher restart: no duplicate addition"
        )

        # 4. Recovery on extra disposable copies (never the in-game copy).
        def copy(name):
            target = a.iso_root / "recovery" / name / "main"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
            return target

        target = copy("external")
        c = LocalWriteController(
            SaveActivityGate(), lambda: str(target), engine_at(a.profile / "external")
        )
        state = c.offer(
            quick_item_intent(native, original, "rare_candy", 3),
            closed_emulator_confirmed=True,
        )
        changed = bytearray(original)
        changed[0x100] ^= 1
        target.write_bytes(bytes(changed))
        # The controller reports a refused confirmation as state, not an exception.
        try:
            refused = c.confirm(state["operation_id"], closed_emulator_confirmed=True)[
                "status"
            ]
        except WriteSafetyError as error:
            refused = str(error)
        assert refused != "APPLIED_VERIFIED", refused
        report["external_modification"] = refused
        assert target.read_bytes() == bytes(changed)
        passed(
            "file modified externally after preparation: confirmation refused, external bytes kept"
        )

        for stage in ("backup_verified", "after_publish"):
            target = copy(stage)

            def fault(name, stage=stage):
                if name == stage:
                    raise Interrupted(stage)

            profile = a.profile / ("fault-" + stage)
            c = LocalWriteController(
                SaveActivityGate(),
                lambda t=target: str(t),
                engine_at(profile, fault_hook=fault),
            )
            intent = quick_item_intent(native, original, "heart_scale", 4)
            try:
                state = c.offer(intent, closed_emulator_confirmed=True)
                c.confirm(state["operation_id"], closed_emulator_confirmed=True)
            except Exception as crash:  # noqa: BLE001 - simulated crash at a fixed stage
                report.setdefault("simulated_crashes", []).append(type(crash).__name__)
            recovered = engine_at(profile)
            receipt = recovered.reconcile(intent.operation_id)
            count = inventory_view(native, target.read_bytes())["items"]["heart_scale"][
                "count"
            ]
            if stage == "backup_verified":
                assert (
                    target.read_bytes() == original
                    and receipt.status != "APPLIED_VERIFIED"
                )
            else:
                # Either verified exactly once, or blocked for recovery: never twice.
                assert receipt.status in (
                    "APPLIED_VERIFIED",
                    "RECOVERY_REQUIRED",
                ) and count in (0, 4)
                assert receipt.status != "APPLIED_VERIFIED" or count == 4
            report.setdefault("interruptions", {})[stage] = {
                "receipt": receipt.status,
                "heart_scale": count,
            }
        passed(
            "interruption during preparation leaves the file untouched; interruption after writing reconciles without duplication"
        )

        target = copy("restore")
        profile = a.profile / "restore"
        c = LocalWriteController(
            SaveActivityGate(), lambda: str(target), engine_at(profile)
        )
        intent = quick_item_intent(native, original, "rare_candy", 2)
        state = c.offer(intent, closed_emulator_confirmed=True)
        c.confirm(state["operation_id"], closed_emulator_confirmed=True)
        engine = engine_at(profile)
        applied = target.read_bytes()
        backup = engine._backup_path(engine._load(intent.operation_id), "original")
        good = backup.read_bytes()
        corrupted = bytearray(good)
        corrupted[0x200] ^= 1
        backup.chmod(0o666)
        backup.write_bytes(bytes(corrupted))
        try:
            corrupt = engine.restore(
                intent.operation_id, closed_emulator_confirmed=True
            ).status
        except WriteSafetyError as error:
            corrupt = str(error)
        assert corrupt != "RESTORED_VERIFIED", corrupt
        assert target.read_bytes() == applied
        backup.write_bytes(good)
        receipt = engine.restore(intent.operation_id, closed_emulator_confirmed=True)
        assert receipt.status == "RESTORED_VERIFIED" and target.read_bytes() == original
        report["restore"] = {"status": receipt.status, "corrupt_backup": corrupt}
        passed(
            "corrupt backup refused without touching the file; verified restore returns the exact original bytes"
        )

        assert h(a.original.read_bytes()) == original_hash, "ORIGINAL CHANGED"
        assert snapshot(a.appdata_lime) == appdata_before, (
            "owner's Lime3DS data changed"
        )
        passed("original save byte-identical (SHA-256 unchanged)")
        report["status"] = "PASS"
    finally:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in (
        "native-exe",
        "lime3ds-exe",
        "appdata-lime",
        "original",
        "work",
        "iso-root",
        "profile",
        "output",
    ):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--rare-candy", type=int, default=10)
    p.add_argument("--heart-scale", type=int, default=7)
    main(p.parse_args())
