import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from guardian import StaticAnalyzer


def make_analyzer(body):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "case.py"
        source = (
            "# --- MANIFEST BEGIN ---\n"
            "# name: Analyzer Test\n"
            "# version: 1.0.0\n"
            "# purpose: Exercise analyzer hardening\n"
            "# dependencies: stdlib\n"
            "# --- MANIFEST END ---\n\n"
            + body
        )
        path.write_text(source, encoding="utf-8")
        return StaticAnalyzer(path, source=source)


class ProcessTests(unittest.TestCase):
    def hit(self, body, expected):
        hits = make_analyzer(body).find_process_or_dynamic_execution()
        self.assertIn(expected, hits, hits)

    def test_from_os_system(self):
        self.hit("from os import system\nsystem('x')\n", "os.system")

    def test_from_os_system_alias(self):
        self.hit(
            "from os import system as harmless\nharmless('x')\n", "os.system"
        )

    def test_os_alias(self):
        self.hit("import os as utility\nutility.system('x')\n", "os.system")

    def test_subprocess_alias(self):
        self.hit(
            "import subprocess as sp\nsp.run(['x'])\n", "subprocess.run"
        )

    def test_from_subprocess_alias(self):
        self.hit(
            "from subprocess import run as execute\nexecute(['x'])\n",
            "subprocess.run",
        )

    def test_assigned_callable(self):
        self.hit("import os\nrunner = os.system\nrunner('x')\n", "os.system")

    def test_getattr_os_system(self):
        self.hit("import os\ngetattr(os, 'system')('x')\n", "os.system")

    def test_getattr_builtins_eval(self):
        self.hit(
            "import builtins\ngetattr(builtins, 'eval')('1+1')\n",
            "builtins.eval",
        )

    def test_importlib_os_system(self):
        self.hit(
            "import importlib\nimportlib.import_module('os').system('x')\n",
            "os.system",
        )

    def test_dunder_import_os_system(self):
        self.hit("__import__('os').system('x')\n", "os.system")

    def test_os_exec(self):
        self.hit(
            "from os import execvp\nexecvp('x', ['x'])\n", "os.execvp"
        )


class FileWriteTests(unittest.TestCase):
    def hit(self, body, fragment):
        hits = make_analyzer(body).find_file_writes()
        self.assertTrue(any(fragment in item for item in hits), hits)

    def test_path_write_text(self):
        self.hit(
            "from pathlib import Path\nPath('x').write_text('data')\n",
            "write_text",
        )

    def test_path_write_bytes(self):
        self.hit(
            "from pathlib import Path\nPath('x').write_bytes(b'data')\n",
            "write_bytes",
        )

    def test_os_write(self):
        self.hit("import os\nos.write(1, b'x')\n", "os.write")

    def test_shutil_move(self):
        self.hit("import shutil\nshutil.move('a', 'b')\n", "shutil.move")

    def test_open_read_write_mode(self):
        self.hit("open('x', 'r+b')\n", "mode='r+b'")


class NetworkTests(unittest.TestCase):
    def test_smtplib(self):
        self.assertIn(
            "smtplib", make_analyzer("import smtplib\n").find_network_access()
        )

    def test_boto3(self):
        self.assertIn(
            "boto3", make_analyzer("import boto3\n").find_network_access()
        )

    def test_dynamic_requests(self):
        self.assertIn(
            "requests",
            make_analyzer(
                "import importlib\nimportlib.import_module('requests')\n"
            ).find_network_access(),
        )


class SecretTests(unittest.TestCase):
    def test_github(self):
        self.assertIn(
            "github_token",
            make_analyzer(
                "TOKEN='ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'\n"
            ).find_secrets(),
        )

    def test_google(self):
        self.assertIn(
            "google_api_key",
            make_analyzer(
                "KEY='AIzaSyA12345678901234567890123456789012'\n"
            ).find_secrets(),
        )

    def test_database_url(self):
        self.assertIn(
            "database_url_with_credentials",
            make_analyzer(
                "URL='postgres://user:password@example.com/db'\n"
            ).find_secrets(),
        )


class ObfuscationTests(unittest.TestCase):
    def test_dynamic_getattr(self):
        self.assertIn(
            "dynamic_getattr",
            make_analyzer(
                "import os\nname=input()\ngetattr(os, name)()\n"
            ).find_suspicious_obfuscation(),
        )

    def test_chr(self):
        self.assertIn(
            "runtime_string_construction:chr",
            make_analyzer(
                "value=chr(111)+chr(115)\n"
            ).find_suspicious_obfuscation(),
        )

    def test_base64(self):
        self.assertIn(
            "encoded_payload_decode:base64.b64decode",
            make_analyzer(
                "import base64\nbase64.b64decode('YWJjZA==')\n"
            ).find_suspicious_obfuscation(),
        )

    def test_long_encoded_string(self):
        value = "A" * 140
        self.assertIn(
            "long_encoded_string",
            make_analyzer(
                f"payload='{value}'\n"
            ).find_suspicious_obfuscation(),
        )


class CleanTests(unittest.TestCase):
    def test_clean_math(self):
        analyzer = make_analyzer(
            "def add(a, b):\n    return a + b\n"
        )
        self.assertEqual(analyzer.find_process_or_dynamic_execution(), [])
        self.assertEqual(analyzer.find_file_writes(), [])
        self.assertEqual(analyzer.find_network_access(), [])
        self.assertEqual(analyzer.find_secrets(), [])
        self.assertEqual(analyzer.find_suspicious_obfuscation(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
