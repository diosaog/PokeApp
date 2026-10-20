"""One real X fixture-copy integration for the new export path, not an 8-game rerun."""

import argparse
import json
import tempfile
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from phase22_safe_export import FixtureExportPrototype

from app.launcher.write_engine import EngineeringCapability, WriteIntent
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.registration import observation_digest
from app.save_parser.writer import PkhexProcessWriter


def run(native, fixture_root, evidence_dir):
    repo = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (repo / "tests/fixtures/phase21-public-saves.json").read_text(encoding="utf-8")
    )
    entry = next(
        row for row in manifest["fixtures"] if row["file"] == "X-original/main"
    )
    source = fixture_root / entry["file"]
    original = source.read_bytes()
    digest = lambda data: sha256(data).hexdigest()
    assert digest(original) == entry["sha256"] and len(original) == entry["bytes"]
    parser = PkhexProcessParser(native)
    observation = parser.parse(original)
    assert observation.game == "X"
    trainer = observation.trainer
    trainer_key = digest(
        "\0".join(
            (
                "X",
                trainer.name,
                str(trainer.tid),
                str(trainer.sid),
                str(trainer.gender),
                str(trainer.language),
            )
        ).encode("utf-8")
    )
    intent = WriteIntent.create(
        expected_sha256=entry["sha256"],
        game="X",
        trainer_key=trainer_key,
        mutation={
            "kind": "test_marking",
            "location": "box",
            "box_index": 0,
            "slot_index": 0,
            "expected_original": 0,
            "new_value": 1,
        },
    )
    evidence_dir.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="pokeapp-phase22-export-native-") as temp:
        root = Path(temp)
        selected = root / "main"
        selected.write_bytes(original)
        destination = root / "exports"
        destination.mkdir()
        exporter = FixtureExportPrototype(
            EngineeringCapability.for_fixture_root(root), PkhexProcessWriter(native)
        )
        receipt = exporter.export(selected, destination, intent)
        output = Path(receipt.output_path).read_bytes()
        after = parser.parse(output)
        assert output != original and len(output) == len(original)
        assert after == observation
        assert observation_digest(after, parser.version) == observation_digest(
            observation, parser.version
        )
        assert selected.read_bytes() == original and receipt.applied_to_source is False
        result = asdict(receipt)
        result["output_path"] = "disposable-copy/exports/export-<operation-id>.save"
        result.update(
            status="PASS",
            game="X",
            original_fixture_unchanged=True,
            selected_copy_unchanged=True,
            same_reader_and_digest=True,
            native_prepare_verify=True,
            local_only=True,
        )
    assert source.read_bytes() == original
    result["temporary_directory_removed"] = not root.exists()
    (evidence_dir / "native-export-evidence.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: native X copy export; original/digest intact; no source application")


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--native", type=Path, required=True)
    cli.add_argument("--fixture-root", type=Path, required=True)
    cli.add_argument("--evidence-dir", type=Path, required=True)
    args = cli.parse_args()
    run(args.native, args.fixture_root, args.evidence_dir)
