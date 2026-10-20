"""Reproduce eight-game Phase22 native proof on retained contributor fixtures.

Run with PYTHONPATH=. and the project's Python environment. This is an isolated
engineering gate, not a user-save writer or atomic-filesystem certification.
Inputs must match the existing public fixture manifest exactly. All output goes
to a fresh private evidence directory; contributor originals are only read.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from app.launcher.write_engine import WriteIntent
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.registration import observation_digest
from app.save_parser.writer import PkhexProcessWriter

# Targets discovered and independently verified by the C# --write-checks gate.
# These are fixture-specific engineering actions, never a mutation plan inferred
# for an arbitrary save. Native code revalidates the exact original mark.
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


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def _new_file(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        if stream.write(data) != len(data):
            raise RuntimeError("incomplete_disposable_write")
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != data:
        raise RuntimeError("disposable_readback_mismatch")


def run(native: Path, manifest: Path, fixture_root: Path, evidence: Path) -> dict:
    fixture_root = fixture_root.resolve(strict=True)
    evidence = evidence.resolve()
    if evidence.is_relative_to(fixture_root) or fixture_root.is_relative_to(evidence):
        raise ValueError("evidence_must_be_separate_from_source_fixtures")
    catalog = json.loads(manifest.read_text(encoding="utf-8"))
    fixtures = {row["file"]: row for row in catalog["fixtures"]}
    if len(fixtures) != len(catalog["fixtures"]):
        raise ValueError("duplicate_fixture_metadata")
    # Validate the complete plan before creating any output.
    inputs = []
    for game, relative, location, original, changed in CASES:
        metadata = fixtures[relative]
        source = (fixture_root / relative).resolve(strict=True)
        if not source.is_relative_to(fixture_root) or metadata["game"] != game:
            raise ValueError("fixture_identity_or_path_mismatch")
        data = source.read_bytes()
        if len(data) != metadata["bytes"] or _hash(data) != metadata["sha256"]:
            raise ValueError("fixture_bytes_do_not_match_retained_manifest")
        inputs.append((game, relative, location, original, changed, source, data))
    parser = PkhexProcessParser(native)
    writer = PkhexProcessWriter(native)
    evidence.mkdir(parents=True, exist_ok=False)
    results, intents = [], []
    for game, relative, location, original, changed, source, data in inputs:
        before = parser.parse(data)
        if before.game != game:
            raise RuntimeError("content_game_mismatch")
        trainer = before.trainer
        trainer_key = _hash(
            "\0".join(
                (
                    game,
                    trainer.name,
                    str(trainer.tid),
                    str(trainer.sid),
                    str(trainer.gender),
                    str(trainer.language),
                )
            ).encode("utf-8")
        )
        intent = WriteIntent.create(
            game=game,
            expected_sha256=_hash(data),
            trainer_key=trainer_key,
            mutation={
                "kind": "test_marking",
                "location": location,
                "box_index": 0 if location == "box" else None,
                "slot_index": 0,
                "expected_original": original,
                "new_value": changed,
            },
        )
        game_dir = evidence / game
        game_dir.mkdir()
        _new_file(game_dir / "source-copy", data)
        # Both calls use the same isolated byte contract; neither receives a path.
        prepared = writer.prepare(data, intent)
        repeated = writer.prepare(data, intent)
        if prepared != repeated or prepared.output == data:
            raise RuntimeError("nondeterministic_or_noop_preparation")
        _new_file(game_dir / "prepared", prepared.output)
        persisted = (game_dir / "prepared").read_bytes()
        writer.verify(data, persisted, intent, prepared)
        after = parser.parse(persisted)
        before_digest = observation_digest(before, parser.version)
        after_digest = observation_digest(after, parser.version)
        if before.model_dump(mode="json") != after.model_dump(mode="json"):
            raise RuntimeError("reader_projection_changed")
        if before_digest != after_digest:
            raise RuntimeError("existing_receipt_digest_changed")
        # A separate restoration copy demonstrates original-byte recovery, not
        # replacement/rollback against any source or user file.
        _new_file(game_dir / "restored", (game_dir / "source-copy").read_bytes())
        if source.read_bytes() != data or (game_dir / "restored").read_bytes() != data:
            raise RuntimeError("source_or_recovery_bytes_changed")
        intents.append(
            {
                "game": game,
                "source": relative,
                "source_sha256": _hash(data),
                "output_sha256": prepared.output_hash,
                "intent": intent.to_payload(),
            }
        )
        results.append(
            {
                "game": game,
                "source": relative,
                "source_sha256": _hash(data),
                "output_sha256": prepared.output_hash,
                "source_bytes": len(data),
                "operation_id": intent.operation_id,
                "reader_digest": before_digest,
                "prepare_verify": "PASS",
                "nontrivial_native_diff": prepared.semantic_diff,
                "duplicate_preparation": "PASS",
                "persisted_output_readback": "PASS",
                "reader_and_receipt_unchanged": "PASS",
                "restored_copy_exact": "PASS",
                "contributor_original_unchanged": "PASS",
            }
        )
        print(f"PASS Phase22 native {game}: write / verify / replay / reader / digest / source")
    # Check all originals again after the entire run.
    for _, _, _, _, _, source, data in inputs:
        if source.read_bytes() != data:
            raise RuntimeError("final_original_preservation_failed")
    summary = {
        "schema_version": 1,
        "status": "PASS",
        "writer_version": writer.version,
        "parser_version": parser.version,
        "native_executable_sha256": _hash(native.read_bytes()),
        "games": results,
        "boundary": (
            "Native protocol and disposable persisted copies only. Atomic target "
            "replacement/crash recovery is a separate Windows-engine gate. Public "
            "contributor fixtures are not independent legality/hardware attestations."
        ),
    }
    _new_file(
        evidence / "native-write-intents.json",
        json.dumps(intents, ensure_ascii=True, indent=2).encode("utf-8"),
    )
    _new_file(
        evidence / "native-write-evidence.json",
        json.dumps(summary, ensure_ascii=True, indent=2).encode("utf-8"),
    )
    return summary


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--native", type=Path, required=True)
    argument_parser.add_argument(
        "--manifest", type=Path, default=Path("tests/fixtures/phase21-public-saves.json")
    )
    argument_parser.add_argument("--fixture-root", type=Path, required=True)
    argument_parser.add_argument("--evidence-dir", type=Path, required=True)
    args = argument_parser.parse_args()
    run(args.native.resolve(strict=True), args.manifest, args.fixture_root, args.evidence_dir)
    print("RESULT PASS; eight native games; contributor originals unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
