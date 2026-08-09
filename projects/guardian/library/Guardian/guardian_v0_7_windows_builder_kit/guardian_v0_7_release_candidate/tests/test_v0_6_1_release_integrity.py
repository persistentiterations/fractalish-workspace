import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ReleaseIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.site = cls.root / 'site'
        proc = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--no-deps',
            '--no-build-isolation', '--target', str(cls.site), str(ROOT)
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)
        cls.env = dict(os.environ)
        cls.env['PYTHONPATH'] = str(cls.site)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_verify_installation_passes(self):
        proc = subprocess.run([
            sys.executable, '-S', '-m', 'guardian_intake', 'verify-installation'
        ], capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload['valid'])
        self.assertTrue(all(item['status'] == 'valid' for item in payload['files']))

    def test_verify_installation_detects_engine_change(self):
        copied_site = self.root / 'tampered_site'
        shutil.copytree(self.site, copied_site)
        engine = copied_site / 'guardian_intake' / 'guardian.py'
        engine.write_text(engine.read_text(encoding='utf-8') + '\n# changed\n', encoding='utf-8')
        env = dict(self.env)
        env['PYTHONPATH'] = str(copied_site)
        proc = subprocess.run([
            sys.executable, '-S', '-m', 'guardian_intake', 'verify-installation'
        ], capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload['valid'])
        self.assertTrue(any(item['status'] == 'mismatch' for item in payload['files']))

    def _clean_source(self, path):
        path.write_text(
            '# --- MANIFEST BEGIN ---\n# name: Clean\n# version: 1.0.0\n'
            '# purpose: Test unsigned acknowledgement\n# dependencies: stdlib\n'
            '# --- MANIFEST END ---\n\nvalue = 1\n', encoding='utf-8')

    def test_unsigned_dev_requires_environment_acknowledgement(self):
        source = self.root / 'clean_refused.py'
        self._clean_source(source)
        proc = subprocess.run([
            sys.executable, '-S', '-m', 'guardian_intake', '--unsigned-dev',
            '--ledger', str(self.root / 'refused.jsonl'), 'scan', str(source), '--json'
        ], capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 4)
        self.assertIn('GUARDIAN_DEV_MODE=1', proc.stderr)

    def test_unsigned_dev_with_acknowledgement_warns_and_runs(self):
        source = self.root / 'clean_ack.py'
        self._clean_source(source)
        env = dict(self.env)
        env['GUARDIAN_DEV_MODE'] = '1'
        proc = subprocess.run([
            sys.executable, '-S', '-m', 'guardian_intake', '--unsigned-dev',
            '--ledger', str(self.root / 'ack.jsonl'), 'scan', str(source), '--json'
        ], capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('UNSIGNED DEVELOPER MODE IS ACTIVE', proc.stderr)
        self.assertTrue(json.loads(proc.stdout)['unsigned_dev_mode'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
