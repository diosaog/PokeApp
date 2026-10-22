"""Seed ONE authentic disposable recovery journal for packaged UI qualification."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from app.launcher.write_engine import (
    EngineeringCapability,
    LocalWriteEngine,
    WriteIntent,
)
from app.launcher.write_files import WindowsWriteFiles
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.writer import PkhexProcessWriter


def seed(workspace, native):
    target = workspace / "main"
    original = target.read_bytes()
    manifest = json.loads(Path("tests/fixtures/phase21-public-saves.json").read_text())
    expected = next(
        r["sha256"] for r in manifest["fixtures"] if r["file"] == "X-original/main"
    )

    def digest(b):
        return sha256(b).hexdigest()

    if digest(original) != expected or (workspace / "seed.json").exists():
        raise ValueError("FRESH_VERIFIED_X_COPY_REQUIRED")
    profile = workspace / "local-data/PokeApp/Launcher-Private"
    observed = PkhexProcessParser(native).parse(original)
    trainer = observed.trainer
    intent = WriteIntent.create(
        game="X",
        expected_sha256=expected,
        trainer_key=digest(
            "\0".join(
                (
                    "X",
                    trainer.name,
                    str(trainer.tid),
                    str(trainer.sid),
                    str(trainer.gender),
                    str(trainer.language),
                )
            ).encode()
        ),
        mutation={
            "kind": "test_marking",
            "location": "box",
            "box_index": 0,
            "slot_index": 0,
            "expected_original": 0,
            "new_value": 1,
        },
    )

    def interrupted(point):
        if point == "after_park":
            raise RuntimeError("isolated packaged recovery fixture")

    engine = LocalWriteEngine(
        profile / "writes",
        PkhexProcessWriter(native),
        files=WindowsWriteFiles(process_names=list),
        engineering_capability=EngineeringCapability.for_fixture_root(workspace),
        fault_hook=interrupted,
    )
    assert (
        engine.prepare(
            engine.enroll(target), intent, closed_emulator_confirmed=True
        ).status
        == "AWAITING_CONFIRMATION"
    )
    assert (
        engine.confirm(intent.operation_id, closed_emulator_confirmed=True).status
        == "RECOVERY_REQUIRED"
    )
    assert not target.exists()
    record = engine._load(intent.operation_id)
    assert engine._backup_bytes(record) == original
    result = {
        "target": str(target),
        "profile": str(profile),
        "operation": intent.operation_id,
        "backup": str(engine._backup_path(record)),
        "original_sha256": expected,
        "status": "RECOVERY_REQUIRED",
        "fault": "after_park",
        "production_authority": False,
    }
    (workspace / "seed.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: native X recovery fixture; disposable root only")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("workspace", type=Path)
    cli.add_argument("native", type=Path)
    args = cli.parse_args()
    seed(args.workspace.resolve(strict=True), args.native.resolve(strict=True))
