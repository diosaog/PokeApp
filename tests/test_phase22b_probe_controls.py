"""Bounded controls for the isolated Phase 22B tools, not product write tests."""

import subprocess
import sys
import unittest
from pathlib import Path

from tools.phase22b_cooperative_lifecycle_probe import _readline
from tools.phase22b_handoff_probe import checked_root


class ProbeControlsTests(unittest.TestCase):
    def child(self, code):
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        def cleanup():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()

        self.addCleanup(cleanup)
        return process

    def test_live_silent_child_has_real_timeout(self):
        process = self.child("import time; time.sleep(10)")
        with self.assertRaisesRegex(RuntimeError, "COOPERATIVE_EMULATOR_TIMEOUT"):
            _readline(process, timeout=0.05)
        self.assertIsNone(process.poll())

    def test_closed_pipe_is_not_a_close_acknowledgement(self):
        with self.assertRaisesRegex(RuntimeError, "COOPERATIVE_EMULATOR_EOF"):
            _readline(self.child("pass"), timeout=5)

    def test_explicit_acknowledgement(self):
        self.assertEqual(_readline(self.child("print('CLOSED')"), timeout=5), "CLOSED")

    def test_repository_is_not_an_allowed_mutation_root(self):
        with self.assertRaisesRegex(RuntimeError, "owned_disposable_root_required"):
            checked_root(Path.cwd())


if __name__ == "__main__":
    unittest.main()
