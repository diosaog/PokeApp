import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ApiPortableImportsTest(unittest.TestCase):
    def test_api_imports_without_windows_only_modules(self):
        # The API runs in a Linux container; the suites run on Windows. A fresh
        # process imports app.api.main with msvcrt/winreg/ctypes.windll absent.
        result = subprocess.run(
            [sys.executable, "-m", "tools.check_api_portable_imports"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("115 routes", result.stdout)


if __name__ == "__main__":
    unittest.main()
