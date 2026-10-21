"""Run the new journaled export transaction against eight disposable saves."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from app.launcher.write_engine import (
    EngineeringCapability,
    LocalWriteEngine,
    WriteIntent,
)
from app.launcher.write_files import WindowsWriteFiles
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.writer import PkhexProcessWriter

CASES = (
    ("X", "X-original/main", "box", 0, 1),
    ("Y", "Y-before-transfer/main", "box", 3, 2),
    ("OR", "OR/main", "box", 0, 1),
    ("AS", "AS-current/main", "box", 0, 1),
    ("SN", "SN/main", "box", 0, 1),
    ("MN", "MN/main", "box", 0, 1),
    ("US", "US/main", "party", 0, 1),
    ("UM", "UM/main", "box", 0, 1),
)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def run(native: Path, fixture_root: Path, evidence_dir: Path) -> dict:
    manifest = json.loads(Path("tests/fixtures/phase21-public-saves.json").read_text())
    entries = {row["file"]: row for row in manifest["fixtures"]}
    parser = PkhexProcessParser(native)
    writer = PkhexProcessWriter(native)
    evidence_dir.mkdir(parents=True, exist_ok=False)
    source_hashes = {}
    results = []
    with tempfile.TemporaryDirectory(prefix="pokeapp-phase22-export-eight-") as temp:
        root = Path(temp)
        engine = LocalWriteEngine(
            root / "profile",
            writer,
            files=WindowsWriteFiles(process_names=lambda: []),
            engineering_capability=EngineeringCapability.for_fixture_root(root),
        )
        for game, relative, location, expected, changed in CASES:
            source = root / "saves" / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            original = (fixture_root / relative).read_bytes()
            metadata = entries[relative]
            if (
                digest(original) != metadata["sha256"]
                or len(original) != metadata["bytes"]
            ):
                raise RuntimeError("fixture_manifest_mismatch")
            source.write_bytes(original)
            before = parser.parse(original)
            trainer = before.trainer
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
                expected_sha256=digest(original),
                trainer_key=trainer_key,
                mutation={
                    "kind": "test_marking",
                    "location": location,
                    "box_index": 0 if location == "box" else None,
                    "slot_index": 0,
                    "expected_original": expected,
                    "new_value": changed,
                },
            )
            destination = root / "exports" / game
            destination.mkdir(parents=True)
            enrolled = engine.enroll(source)
            prepared = engine.prepare_export(
                enrolled,
                intent,
                destination_directory=destination,
                closed_emulator_confirmed=True,
            )
            receipt = engine.confirm(
                intent.operation_id, closed_emulator_confirmed=True
            )
            if receipt.status != "EXPORTED_VERIFIED" or receipt.applied_to_source:
                raise RuntimeError(f"export_failed_{game}_{receipt.error}")
            output = Path(receipt.export_path).read_bytes()
            after = parser.parse(output)
            if source.read_bytes() != original or digest(output) == digest(original):
                raise RuntimeError(f"source_or_output_mismatch_{game}")
            if before.model_dump(mode="json") != after.model_dump(mode="json"):
                raise RuntimeError(f"reader_projection_changed_{game}")
            source_hashes[relative] = digest(original)
            results.append(
                {
                    "game": game,
                    "status": receipt.status,
                    "applied_to_source": False,
                    "source_unchanged": True,
                    "output_verified": True,
                }
            )
        if len(list((root / "exports").rglob("export-*.save"))) != 8:
            raise RuntimeError("wrong_export_count")
    evidence = {
        "status": "PASS",
        "games": results,
        "count": len(results),
        "original_hashes": source_hashes,
        "temporary_root_removed": not root.exists(),
        "scope": "disposable copies; no owner or production saves",
    }
    (evidence_dir / "journaled-export-eight-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(
        "PASS: journaled verified export for eight disposable game copies; originals unchanged"
    )
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("Windows NTFS required")
    run(
        args.native.resolve(strict=True),
        args.fixture_root.resolve(strict=True),
        args.evidence_dir.resolve(),
    )
