"""Fixture-only Windows export adversaries; no Pokemon format claims.

These small synthetic bytes exercise filesystem races only. The retained native
eight-game evidence belongs to the unchanged native adapter, not this test file.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from test_phase22_write_engine import SOURCE, TestNative, intent

from app.launcher.write_engine import EngineeringCapability
from app.launcher.write_files import WriteSafetyError
from tools.phase22_safe_export import FixtureExportPrototype

ROOT = Path(__file__).resolve().parents[1]
CHILD_PREFIX = """
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from test_phase22_write_engine import SOURCE, TestNative, intent
from app.launcher.write_engine import EngineeringCapability
from app.launcher.write_files import WriteSafetyError
from tools.phase22_safe_export import FixtureExportPrototype
args = json.loads(sys.stdin.readline())
"""


def child_run(body, data):
    result = subprocess.run(
        [sys.executable, "-c", CHILD_PREFIX + body],
        check=False,
        input=json.dumps(data) + "\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result


def child_waiter(body, data):
    process = subprocess.Popen(
        [sys.executable, "-c", CHILD_PREFIX + body],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=ROOT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    process.stdin.write(json.dumps(data) + "\n")
    process.stdin.flush()
    line = process.stdout.readline().strip()
    if line != "READY":
        process.kill()
        output, errors = process.communicate(timeout=10)
        raise AssertionError(f"child not ready: {line} {output} {errors}")
    return process


@unittest.skipUnless(os.name == "nt", "requires real Windows NTFS")
class SafeExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pokeapp-phase22-export-")
        self.root = Path(self.tmp.name)
        self.source = self.root / "main"
        self.source.write_bytes(SOURCE)
        self.destination = self.root / "exports"
        self.destination.mkdir()
        self.intent = intent()
        self.prepared = TestNative().prepare(SOURCE, self.intent)
        self.final = self.destination / f"export-{self.intent.operation_id}.save"

    def tearDown(self):
        self.tmp.cleanup()

    def exporter(self, hook=None):
        return FixtureExportPrototype(
            EngineeringCapability.for_fixture_root(self.root), TestNative(), hook=hook
        )

    def export(self, hook=None):
        return self.exporter(hook).export(self.source, self.destination, self.intent)

    def args(self):
        return {
            "root": str(self.root),
            "source": str(self.source),
            "destination": str(self.destination),
        }

    def assert_original(self):
        self.assertEqual(SOURCE, self.source.read_bytes())

    def test_valid_partial_is_not_a_published_export(self):
        def stop(stage, paths):
            if stage == "before_publish":
                raise WriteSafetyError("SIMULATED_INTERRUPTION")

        with self.assertRaisesRegex(WriteSafetyError, "SIMULATED_INTERRUPTION"):
            self.export(stop)
        (partial,) = self.destination.glob("*.partial")
        self.assertEqual(self.prepared.output, partial.read_bytes())
        with self.assertRaisesRegex(WriteSafetyError, "NOT_A_PUBLISHED_EXPORT_NAME"):
            self.exporter().inspect(partial, SOURCE, self.intent, self.prepared)
        self.assertFalse(self.final.exists())
        self.assert_original()

    def test_new_export_original_unchanged_and_replay_cannot_replace(self):
        receipt = self.export()
        self.assertFalse(receipt.applied_to_source)
        self.assertEqual("EXPORTED_VERIFIED", receipt.state)
        self.assertEqual(str(self.final), receipt.output_path)
        self.assertEqual(self.prepared.output, self.final.read_bytes())
        self.assert_original()
        with self.assertRaises(WriteSafetyError) as caught:
            self.export()
        self.assertTrue(
            caught.exception.code.startswith("NO_REPLACE_PUBLICATION_FAILED_")
        )
        self.assertEqual(self.prepared.output, self.final.read_bytes())
        self.assert_original()

    def test_child_cannot_write_rename_or_replace_locked_source_and_stage(self):
        attempts = []

        def attack(stage, paths):
            if stage != "before_publish":
                return
            result = child_run(
                """
results = []
for value in args["paths"]:
    path = Path(value)
    for action in ("write", "rename", "replace"):
        try:
            if action == "write":
                with path.open("r+b") as stream:
                    stream.write(b"ATTACK")
            elif action == "rename":
                path.rename(path.with_name(path.name + ".moved"))
            else:
                replacement = path.with_name(path.name + ".rival")
                replacement.write_bytes(b"RIVAL")
                os.replace(replacement, path)
            results.append([action, "UNEXPECTED_SUCCESS"])
        except OSError as error:
            results.append([action, error.winerror or error.errno])
print(json.dumps(results))
""",
                {"paths": [str(paths["source"]), str(paths["stage"])]},
            )
            self.assertEqual(0, result.returncode, result.stderr)
            attempts.extend(json.loads(result.stdout))

        self.export(attack)
        self.assertEqual(6, len(attempts))
        # CRT open reports EACCES=13; Win32 rename/replace report sharing or
        # access denial. Every operation must fail; no other exception qualifies.
        self.assertTrue(all(result in (5, 13, 32) for _, result in attempts), attempts)
        self.assert_original()
        self.assertEqual(self.prepared.output, self.final.read_bytes())

    def test_child_claims_final_name_no_overwrite_occurs(self):
        def collision(stage, paths):
            if stage == "before_publish":
                result = child_run(
                    'Path(args["final"]).write_bytes(b"OTHER PROCESS SAVE")\n',
                    {"final": str(paths["final"])},
                )
                self.assertEqual(0, result.returncode, result.stderr)

        with self.assertRaises(WriteSafetyError) as caught:
            self.export(collision)
        self.assertTrue(
            caught.exception.code.startswith("NO_REPLACE_PUBLICATION_FAILED_")
        )
        self.assertEqual(b"OTHER PROCESS SAVE", self.final.read_bytes())
        self.assert_original()
        candidates = list(self.destination.glob("*.partial"))
        self.assertEqual(1, len(candidates))
        self.assertEqual(self.prepared.output, candidates[0].read_bytes())

    def test_existing_writer_and_writable_mapping_fail_closed(self):
        body = """
import mmap
stream = Path(args["source"]).open("r+b")
mapping = None
if args["mapped"]:
    mapping = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_WRITE)
    stream.close()
print("READY", flush=True)
sys.stdin.readline()
if mapping:
    mapping.close()
if not stream.closed:
    stream.close()
"""
        for mapped in (False, True):
            with self.subTest(mapped=mapped):
                process = child_waiter(body, {**self.args(), "mapped": mapped})
                try:
                    with self.assertRaises(WriteSafetyError) as caught:
                        self.export()
                    self.assertEqual(
                        "EXCLUSIVE_CREATE_OR_SOURCE_LOCK_FAILED",
                        caught.exception.code,
                    )
                    self.assertFalse(self.final.exists())
                    self.assertEqual([], list(self.destination.iterdir()))
                finally:
                    output, errors = process.communicate("\n", timeout=10)
                    self.assertEqual(0, process.returncode, output + errors)
                self.assert_original()

    def test_two_prepared_processes_same_name_only_one_can_publish(self):
        body = """
def hook(stage, paths):
    if stage == "before_publish":
        print("READY", flush=True)
        sys.stdin.readline()
engine = FixtureExportPrototype(
    EngineeringCapability.for_fixture_root(Path(args["root"])),
    TestNative(), hook=hook,
)
try:
    receipt = engine.export(Path(args["source"]), Path(args["destination"]), intent())
    print(json.dumps({"state": receipt.state}))
except WriteSafetyError as error:
    print(json.dumps({"error": error.code}))
"""
        processes = []
        try:
            processes.append(child_waiter(body, self.args()))
            processes.append(child_waiter(body, self.args()))
            for process in processes:
                process.stdin.write("\n")
                process.stdin.flush()
            results = []
            for process in processes:
                output, errors = process.communicate(timeout=15)
                self.assertEqual(0, process.returncode, errors)
                results.append(json.loads(output))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
        self.assertEqual(
            1, sum(row.get("state") == "EXPORTED_VERIFIED" for row in results)
        )
        failures = [row["error"] for row in results if "error" in row]
        self.assertEqual(1, len(failures))
        self.assertTrue(failures[0].startswith("NO_REPLACE_PUBLICATION_FAILED_"))
        self.assertEqual(self.prepared.output, self.final.read_bytes())
        self.assert_original()

    def test_process_death_partial_is_rejected_final_can_be_inspected_read_only(self):
        body = """
def hook(stage, paths):
    if stage == args["crash"]:
        os._exit(73)
engine = FixtureExportPrototype(
    EngineeringCapability.for_fixture_root(Path(args["root"])),
    TestNative(), hook=hook,
)
engine.export(Path(args["source"]), Path(args["destination"]), intent())
"""
        for crash in ("stage_created", "after_publish"):
            with self.subTest(crash=crash):
                folder = self.destination / crash
                folder.mkdir()
                result = child_run(
                    body, {**self.args(), "destination": str(folder), "crash": crash}
                )
                self.assertEqual(73, result.returncode, result.stderr)
                self.assert_original()
                files = list(folder.iterdir())
                self.assertEqual(1, len(files))
                candidate = files[0]
                before = candidate.read_bytes()
                if crash == "stage_created":
                    self.assertEqual(b"", before)
                    with self.assertRaises(WriteSafetyError) as caught:
                        self.exporter().inspect(
                            candidate, SOURCE, self.intent, self.prepared
                        )
                    self.assertEqual(
                        "NOT_A_PUBLISHED_EXPORT_NAME", caught.exception.code
                    )
                else:
                    recovered = self.exporter().inspect(
                        candidate, SOURCE, self.intent, self.prepared
                    )
                    self.assertFalse(recovered.applied_to_source)
                    self.assertEqual(self.prepared.output, before)
                self.assertEqual(before, candidate.read_bytes())
                self.assertEqual([candidate], list(folder.iterdir()))
                self.assert_original()

    def test_later_export_edit_is_not_an_accepted_receipt(self):
        self.export()
        self.final.write_bytes(b"LATER EXPORT EDIT")
        with self.assertRaises(WriteSafetyError) as caught:
            self.exporter().inspect(self.final, SOURCE, self.intent, self.prepared)
        self.assertEqual("EXPORT_CHANGED_OR_INCOMPLETE", caught.exception.code)
        self.assertEqual(b"LATER EXPORT EDIT", self.final.read_bytes())
        self.assert_original()

    def test_later_source_edit_stays_intact_recovery_is_historical_only(self):
        receipt = self.export()
        later = SOURCE[:-1] + b"Q"
        self.source.write_bytes(later)
        recovered = self.exporter().inspect(
            self.final, SOURCE, self.intent, self.prepared
        )
        self.assertEqual(receipt, recovered)
        self.assertFalse(recovered.applied_to_source)
        self.assertEqual(sha256(SOURCE).hexdigest(), recovered.source_sha256)
        self.assertNotEqual(sha256(later).hexdigest(), recovered.source_sha256)
        self.assertEqual(later, self.source.read_bytes())
        self.assertEqual(self.prepared.output, self.final.read_bytes())


if __name__ == "__main__":
    unittest.main()
