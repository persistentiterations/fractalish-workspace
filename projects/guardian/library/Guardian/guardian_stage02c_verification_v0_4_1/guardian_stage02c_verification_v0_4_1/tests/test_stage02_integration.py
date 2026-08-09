import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN = ROOT / "guardian.py"


def wrapped(body):
    return (
        "# --- MANIFEST BEGIN ---\n"
        "# name: Integration Test\n"
        "# version: 1.0.0\n"
        "# purpose: Verify outcome mapping\n"
        "# dependencies: stdlib\n"
        "# --- MANIFEST END ---\n\n"
        + body
    )


class IntegrationTests(unittest.TestCase):
    def scan(self, content):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "case.py"
            ledger = root / "ledger.jsonl"
            source.write_text(content, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(GUARDIAN),
                    "--ledger",
                    str(ledger),
                    "scan",
                    str(source),
                    "--json",
                ],
                capture_output=True,
                text=True,
            )
            return result.returncode, json.loads(result.stdout)

    def test_os_system_reject(self):
        code, slip = self.scan(
            wrapped("from os import system\nsystem('x')\n")
        )
        self.assertEqual(code, 3)
        self.assertEqual(slip["intake_outcome"], "Reject")

    def test_path_write_hold(self):
        code, slip = self.scan(
            wrapped(
                "from pathlib import Path\n"
                "Path('x').write_text('data')\n"
            )
        )
        self.assertEqual(code, 2)
        self.assertEqual(slip["intake_outcome"], "Hold")

    def test_obfuscation_hold(self):
        code, slip = self.scan(
            wrapped("value=chr(111)+chr(115)\n")
        )
        self.assertEqual(code, 2)
        self.assertEqual(slip["intake_outcome"], "Hold")

    def test_clean_let_in(self):
        code, slip = self.scan(
            wrapped("def add(a,b):\n    return a+b\n")
        )
        self.assertEqual(code, 0)
        self.assertEqual(slip["intake_outcome"], "Let In")


if __name__ == "__main__":
    unittest.main(verbosity=2)
