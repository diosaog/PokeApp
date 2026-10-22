import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.launcher.emulator_qualification import (
    inspect_azahar_candidate,
    qualification_status,
)
from tools.prepare_azahar_qualification import prepare


@unittest.skipUnless(os.name == "nt", "Windows path contract")
class QualificationTests(unittest.TestCase):
    def test_recognized_candidate_is_never_certified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "azahar.exe"
            path.write_bytes(b"isolated test executable, never run")
            from hashlib import sha256

            with patch(
                "app.launcher.emulator_qualification.AZAHAR_SHA256",
                sha256(path.read_bytes()).hexdigest(),
            ):
                candidate = inspect_azahar_candidate(path)
            self.assertFalse(candidate["qualified"])
            self.assertFalse(candidate["automatic_lifecycle_enabled"])
            candidate["qualified"] = True
            self.assertFalse(qualification_status()["qualified"])

    def test_unknown_binary_and_network_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "azahar.exe"
            path.write_bytes(b"unknown version")
            with self.assertRaisesRegex(ValueError, "VERSION_NOT_PINNED"):
                inspect_azahar_candidate(path)
            with self.assertRaisesRegex(ValueError, "LOCAL_WINDOWS"):
                inspect_azahar_candidate(Path(r"\\server\share\azahar.exe"))

    def test_portable_preparation_excludes_user_data_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "installed"
            source.mkdir()
            (source / "azahar.exe").write_bytes(b"never execute this test fixture")
            (source / "runtime.dll").write_bytes(b"runtime")
            (source / "user").mkdir()
            (source / "user" / "private-save").write_bytes(b"must not be copied")
            from hashlib import sha256

            with patch(
                "app.launcher.emulator_qualification.AZAHAR_SHA256",
                sha256((source / "azahar.exe").read_bytes()).hexdigest(),
            ):
                result = prepare(source / "azahar.exe", root / "portable")
                self.assertFalse(result["qualified"])
                self.assertEqual([], list((root / "portable/user").iterdir()))
                self.assertEqual(
                    b"runtime", (root / "portable/runtime.dll").read_bytes()
                )
                with self.assertRaisesRegex(ValueError, "FRESH_ISOLATED"):
                    prepare(source / "azahar.exe", root / "portable")
            self.assertEqual(
                b"must not be copied", (source / "user/private-save").read_bytes()
            )


if __name__ == "__main__":
    unittest.main()
