"""Eight authentic disposable saves through the integrated journal and backup UI DTO."""

import argparse
import json
import os
import stat
import tempfile
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
from tools.validate_phase22_native_writes import CASES


def digest(data):
    return sha256(data).hexdigest()


def run(native, fixtures, evidence):
    if evidence.exists():
        raise ValueError("fresh_evidence_path_required")
    catalog = json.loads(Path("tests/fixtures/phase21-public-saves.json").read_text())
    manifest = {r["file"]: r for r in catalog["fixtures"]}
    parser, writer = PkhexProcessParser(native), PkhexProcessWriter(native)
    rows, original_hashes = [], {}
    with tempfile.TemporaryDirectory(prefix="pokeapp-phase22c-eight-") as temp:
        root = Path(temp).resolve()
        try:
            for game, relative, location, old, new in CASES:
                original = (fixtures / relative).read_bytes()
                if (
                    digest(original) != manifest[relative]["sha256"]
                    or len(original) != manifest[relative]["bytes"]
                ):
                    raise AssertionError("fixture_manifest_mismatch")
                original_hashes[relative] = digest(original)
                game_root = root / game
                game_root.mkdir()
                target = game_root / "main"
                target.write_bytes(original)
                observation = parser.parse(original)
                trainer = observation.trainer
                trainer_key = digest(
                    "\0".join(
                        (
                            game,
                            trainer.name,
                            str(trainer.tid),
                            str(trainer.sid),
                            str(trainer.gender),
                            str(trainer.language),
                        )
                    ).encode()
                )
                intent = WriteIntent.create(
                    game=game,
                    trainer_key=trainer_key,
                    expected_sha256=digest(original),
                    mutation={
                        "kind": "test_marking",
                        "location": location,
                        "box_index": 0 if location == "box" else None,
                        "slot_index": 0,
                        "expected_original": old,
                        "new_value": new,
                    },
                )
                engine = LocalWriteEngine(
                    game_root / "profile",
                    writer,
                    files=WindowsWriteFiles(process_names=list),
                    engineering_capability=EngineeringCapability.for_fixture_root(root),
                )
                receipt = engine.prepare(
                    engine.enroll(target), intent, closed_emulator_confirmed=True
                )
                if (
                    receipt.status != "AWAITING_CONFIRMATION"
                    or target.read_bytes() != original
                ):
                    raise AssertionError("prepare_mutated_source")
                history = engine.backups_for(target)
                if (
                    len(history) != 1
                    or not history[0]["verified"]
                    or not history[0]["created_at"]
                ):
                    raise AssertionError("backup_history_missing")
                applied = engine.confirm(
                    intent.operation_id, closed_emulator_confirmed=True
                )
                if (
                    applied.status != "APPLIED_VERIFIED"
                    or not applied.current_matches_receipt
                ):
                    raise AssertionError(f"apply_{game}_{applied.error}")
                current = target.read_bytes()
                if current == original or parser.parse(current).model_dump(
                    mode="json"
                ) != observation.model_dump(mode="json"):
                    raise AssertionError("native_projection_changed")
                if (
                    engine.confirm(intent.operation_id, closed_emulator_confirmed=True)
                    != applied
                ):
                    raise AssertionError("receipt_replay_changed")
                # A local history/export reader needs neither native worker nor capability.
                offline = LocalWriteEngine(game_root / "profile", None)
                copy = game_root / "player-backup.sav"
                offline.export_backup(intent.operation_id, destination=copy)
                if copy.read_bytes() != original or target.read_bytes() != current:
                    raise AssertionError("backup_copy_mismatch")
                restored = engine.restore(
                    intent.operation_id, closed_emulator_confirmed=True
                )
                if (
                    restored.status != "RESTORED_VERIFIED"
                    or target.read_bytes() != original
                ):
                    raise AssertionError(f"restore_{game}_{restored.error}")
                if (
                    engine.restore(intent.operation_id, closed_emulator_confirmed=True)
                    != restored
                ):
                    raise AssertionError("restore_replay_changed")
                rows_after = engine.backups_for(target)
                if len(rows_after) != 2 or not all(
                    row["verified"] for row in rows_after
                ):
                    raise AssertionError("recovery_copies_not_retained")
                if (fixtures / relative).read_bytes() != original:
                    raise AssertionError("fixture_changed")
                rows.append(
                    {
                        "game": game,
                        "status": "PASS",
                        "source_sha256": digest(original),
                        "candidate_sha256": digest(current),
                        "backup_before_mutation": True,
                        "apply_native_verified": True,
                        "apply_replay": True,
                        "native_free_backup_export": True,
                        "restore_native_verified": True,
                        "restore_replay": True,
                        "both_backups_retained": True,
                    }
                )
                print(
                    f"PASS {game}: backup / apply / replay / Save Copy / restore / native verification",
                    flush=True,
                )
        finally:
            # Only this fresh, resolved, owned fixture tree; never earlier cleanup residue.
            if root.parent != Path(
                tempfile.gettempdir()
            ).resolve() or not root.name.startswith("pokeapp-phase22c-eight-"):
                raise RuntimeError("unexpected_cleanup_root")
            for path in root.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    path.chmod(stat.S_IREAD | stat.S_IWRITE)
        if any(
            digest((fixtures / name).read_bytes()) != value
            for name, value in original_hashes.items()
        ):
            raise AssertionError("final_fixture_changed")
    result = {
        "status": "PASS",
        "games": rows,
        "count": len(rows),
        "originals_unchanged": True,
        "temporary_root_removed": not root.exists(),
        "real_emulator_qualified": False,
        "power_loss_certified": False,
        "production_capability": False,
    }
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--native", required=True, type=Path)
    cli.add_argument("--fixtures", required=True, type=Path)
    cli.add_argument("--evidence", required=True, type=Path)
    args = cli.parse_args()
    if os.name != "nt":
        cli.error("Windows NTFS required")
    run(
        args.native.resolve(strict=True),
        args.fixtures.resolve(strict=True),
        args.evidence.resolve(),
    )
