"""Native bridge contracts; stub subprocesses are not native-save write evidence."""

import base64
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.launcher.write_engine import WriteIntent
from app.save_parser.writer import (
    NATIVE_SIZES,
    WRITER_VERSION,
    NativeWriteError,
    PkhexProcessWriter,
)


class NativeBridgeTests(unittest.TestCase):
    def setUp(self):
        self.source = bytes(NATIVE_SIZES["X"])
        self.output = b"\x01" + self.source[1:]
        self.intent = WriteIntent.create(
            game="X",
            expected_sha256=sha256(self.source).hexdigest(),
            trainer_key="b" * 64,
            mutation={
                "kind": "test_marking",
                "location": "box",
                "box_index": 0,
                "slot_index": 0,
                "expected_original": 0,
                "new_value": 1,
            },
        )
        self.writer = PkhexProcessWriter(Path(sys.executable))

    def response(self, status="prepared"):
        return {
            "schema_version": 1,
            "writer_version": WRITER_VERSION,
            "status": status,
            "error": None,
            "game": "X",
            "trainer_key": self.intent.trainer_key,
            "source_sha256": sha256(self.source).hexdigest(),
            "output_sha256": sha256(self.output).hexdigest(),
            "output_base64": base64.b64encode(self.output).decode()
            if status == "prepared"
            else None,
            "semantic_diff": self.intent.mutation
            | {
                "preserved_unrelated": True,
                "checksums_valid": True,
                "signature_valid": True,
            },
        }

    def test_prepare_requires_separate_verification_and_persisted_reverification(self):
        with patch.object(
            self.writer,
            "_run",
            side_effect=[
                self.response(),
                self.response("verified"),
                self.response("verified"),
            ],
        ) as run:
            prepared = self.writer.prepare(self.source, self.intent)
            self.writer.verify(self.source, self.output, self.intent, prepared)
        self.assertEqual(prepared.output, self.output)
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            ["--prepare-write", "--verify-write", "--verify-write"],
        )
        for call in run.call_args_list:
            self.assertEqual(
                set(call.args[1]),
                {"schema_version", "source_base64", "intent"}
                | ({"output_base64"} if call.args[0] == "--verify-write" else set()),
            )
            self.assertEqual(
                base64.b64decode(call.args[1]["source_base64"]), self.source
            )

    def test_rejects_stale_source_and_unsupported_size_before_starting_child(self):
        with patch.object(self.writer, "_run") as run:
            for source, code in (
                (self.source[:-1], "UNSUPPORTED_FORMAT"),
                (self.output, "STALE_SOURCE"),
            ):
                with (
                    self.subTest(code=code),
                    self.assertRaises(NativeWriteError) as got,
                ):
                    self.writer.prepare(source, self.intent)
                self.assertEqual(got.exception.code, code)
        run.assert_not_called()

    def test_rejects_wrong_receipt_or_nontriviality_or_semantic_proof(self):
        candidates = [
            {"game": "Y"},
            {"trainer_key": "c" * 64},
            {"source_sha256": "d" * 64},
            {"output_sha256": "e" * 64},
            {"output_base64": "not base64"},
            {"output_base64": None},
            {"status": "verified"},
            {
                "output_base64": base64.b64encode(self.source).decode(),
                "output_sha256": sha256(self.source).hexdigest(),
            },
            {"semantic_diff": None},
            {"semantic_diff": self.response()["semantic_diff"] | {"extra": "private"}},
            {
                "semantic_diff": self.response()["semantic_diff"]
                | {"preserved_unrelated": 1}
            },
            {
                "semantic_diff": self.response()["semantic_diff"]
                | {"expected_original": False}
            },
        ]
        for update in candidates:
            with (
                self.subTest(update=update.keys()),
                patch.object(
                    self.writer, "_run", return_value=self.response() | update
                ),
                self.assertRaises(NativeWriteError),
            ):
                self.writer.prepare(self.source, self.intent)

    def test_verifier_cannot_return_new_bytes_or_accept_postwrite_corruption(self):
        with patch.object(
            self.writer,
            "_run",
            side_effect=[self.response(), self.response("verified")],
        ):
            prepared = self.writer.prepare(self.source, self.intent)
        with patch.object(self.writer, "_run") as run:
            with self.assertRaises(NativeWriteError):
                self.writer.verify(self.source, self.source, self.intent, prepared)
            run.assert_not_called()
        with (
            patch.object(
                self.writer,
                "_run",
                return_value=self.response("verified") | {"output_base64": "AA=="},
            ),
            self.assertRaises(NativeWriteError),
        ):
            self.writer.verify(self.source, self.output, self.intent, prepared)

    def test_recovery_receipt_without_candidate_bytes_requires_native_verification(
        self,
    ):
        with patch.object(
            self.writer,
            "_run",
            side_effect=[self.response(), self.response("verified")],
        ):
            prepared = self.writer.prepare(self.source, self.intent)
        recovered = replace(prepared, output=b"")
        with patch.object(
            self.writer, "_run", return_value=self.response("verified")
        ) as run:
            self.writer.verify(self.source, self.output, self.intent, recovered)
            self.assertEqual(run.call_args.args[0], "--verify-write")
        with patch.object(self.writer, "_run") as run:
            with self.assertRaises(NativeWriteError):
                self.writer.verify(self.source, self.source, self.intent, recovered)
            run.assert_not_called()

    def child(self, source, *, timeout=2):
        """Real bounded subprocess pipes; controlled protocol stub, not PKHeX."""
        original_popen = subprocess.Popen
        directory = tempfile.TemporaryDirectory(prefix="pokeapp-phase22-bridge-")
        self.addCleanup(directory.cleanup)
        script = Path(directory.name) / "worker.py"
        script.write_text(source, encoding="utf-8")
        self.writer.timeout = timeout

        def launch(command, **kwargs):
            self.assertEqual(command[0], str(Path(sys.executable).resolve()))
            self.assertIn(command[1], ("--prepare-write", "--verify-write"))
            self.assertIs(kwargs["shell"], False)
            self.assertEqual(
                kwargs["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            return original_popen([sys.executable, str(script), command[1]], **kwargs)

        return patch("app.save_parser.writer.subprocess.Popen", side_effect=launch)

    def test_actual_child_pipes_enforce_exact_envelope_and_version(self):
        good = self.response()
        for change in (
            {},
            {"schema_version": True},
            {"writer_version": "later"},
            {"x": 1},
        ):
            value = good | change
            script = (
                "import sys,json\n"
                "request=json.load(sys.stdin)\n"
                "assert set(request)=={'schema_version'}\n"
                f"sys.stdout.write({json.dumps(json.dumps(value))})\n"
            )
            with self.subTest(change=change), self.child(script):
                if not change:
                    self.assertEqual(
                        self.writer._run("--prepare-write", {"schema_version": 1}),
                        good,
                    )
                else:
                    with self.assertRaises(NativeWriteError):
                        self.writer._run("--prepare-write", {"schema_version": 1})

    def test_rejected_child_only_exposes_recognized_sanitized_code(self):
        rejected = {key: None for key in self.response()} | {
            "schema_version": 1,
            "writer_version": WRITER_VERSION,
            "status": "rejected",
            "error": "CORRUPT_SAVE",
        }
        for code, expected in (
            ("CORRUPT_SAVE", "CORRUPT_SAVE"),
            ("private trainer or path", "NATIVE_WRITER_FAILURE"),
        ):
            value = rejected | {"error": code}
            script = (
                "import sys\nsys.stdin.read()\n"
                f"sys.stdout.write({json.dumps(json.dumps(value))})\n"
                "sys.exit(2)\n"
            )
            with self.subTest(code=code), self.child(script):
                with self.assertRaises(NativeWriteError) as got:
                    self.writer._run("--prepare-write", {"schema_version": 1})
                self.assertEqual(str(got.exception), expected)

    def test_duplicate_fields_bad_json_and_nonzero_success_fail_closed(self):
        duplicate = json.dumps(self.response()).replace(
            '"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1
        )
        for text, exit_code in (
            (duplicate, 0),
            ("private diagnostic", 0),
            (json.dumps(self.response()), 1),
        ):
            script = (
                "import sys\nsys.stdin.read()\n"
                f"sys.stdout.write({json.dumps(text)})\n"
                f"sys.exit({exit_code})\n"
            )
            with self.subTest(exit_code=exit_code), self.child(script):
                with self.assertRaises(NativeWriteError):
                    self.writer._run("--prepare-write", {"schema_version": 1})

    def test_timeout_stdout_and_stderr_limits_kill_child_without_private_output(self):
        for script, timeout in (
            ("import time\ntime.sleep(5)\n", 0.1),
            ("import sys\nsys.stdout.write('s'*(1024*1024+8192))\n", 2),
            ("import sys\nsys.stderr.write('private'*(16384))\n", 2),
        ):
            with self.subTest(timeout=timeout), self.child(script, timeout=timeout):
                with self.assertRaises(NativeWriteError) as got:
                    self.writer._run("--prepare-write", {"schema_version": 1})
                self.assertEqual(str(got.exception), "NATIVE_WRITER_FAILURE")

    def test_native_failure_is_not_hidden_by_a_prepared_claim(self):
        with patch.object(
            self.writer,
            "_run",
            side_effect=[self.response(), NativeWriteError("UNEXPECTED_DIFF")],
        ):
            with self.assertRaises(NativeWriteError) as got:
                self.writer.prepare(self.source, self.intent)
            self.assertEqual(got.exception.code, "UNEXPECTED_DIFF")


if __name__ == "__main__":
    unittest.main()
