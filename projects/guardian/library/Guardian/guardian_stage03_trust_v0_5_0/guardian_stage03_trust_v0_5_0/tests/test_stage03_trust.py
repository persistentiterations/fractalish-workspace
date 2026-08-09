import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import guardian


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def clean_source(name: str = "Clean") -> str:
    return f"""# --- MANIFEST BEGIN ---
# name: {name}
# version: 1.0.0
# purpose: Stage 03 trust infrastructure test
# dependencies: stdlib
# --- MANIFEST END ---

def add(a, b):
    return a + b
"""


class PolicyValidationTests(unittest.TestCase):
    def valid(self):
        return copy.deepcopy(guardian.DEFAULT_POLICY)

    def test_valid_policy(self):
        result = guardian.validate_policy(self.valid())
        self.assertEqual(result["policy_schema_version"], "1.0")

    def test_unknown_checker_rejected(self):
        policy = self.valid()
        policy["checklist"][0]["check_type"] = "magic_bypass"
        with self.assertRaises(guardian.PolicyValidationError):
            guardian.validate_policy(policy)

    def test_invalid_severity_rejected(self):
        policy = self.valid()
        policy["checklist"][0]["severity"] = "hard_rejct"
        with self.assertRaises(guardian.PolicyValidationError):
            guardian.validate_policy(policy)

    def test_duplicate_rule_id_rejected(self):
        policy = self.valid()
        policy["checklist"][1]["id"] = policy["checklist"][0]["id"]
        with self.assertRaises(guardian.PolicyValidationError):
            guardian.validate_policy(policy)

    def test_missing_required_field_rejected(self):
        policy = self.valid()
        del policy["limits"]
        with self.assertRaises(guardian.PolicyValidationError):
            guardian.validate_policy(policy)

    def test_unsupported_schema_rejected(self):
        policy = self.valid()
        policy["policy_schema_version"] = "9.0"
        with self.assertRaises(guardian.PolicyValidationError):
            guardian.validate_policy(policy)

    def test_unknown_top_level_field_rejected(self):
        policy = self.valid()
        policy["silent_override"] = True
        with self.assertRaises(guardian.PolicyValidationError):
            guardian.validate_policy(policy)

    def test_policy_change_changes_fingerprint(self):
        first = self.valid()
        second = self.valid()
        second["description"] += " changed"
        self.assertNotEqual(
            guardian.policy_fingerprint(first),
            guardian.policy_fingerprint(second),
        )

    def test_key_order_does_not_change_fingerprint(self):
        first = self.valid()
        second = json.loads(json.dumps(first, sort_keys=True))
        self.assertEqual(
            guardian.policy_fingerprint(first),
            guardian.policy_fingerprint(second),
        )

    def test_validate_policy_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            policy_path = Path(temp) / "policy.json"
            write_json(policy_path, self.valid())
            proc = subprocess.run(
                [sys.executable, str(ROOT / "guardian.py"),
                 "validate-policy", str(policy_path)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["valid"])
            self.assertEqual(
                payload["policy_fingerprint"],
                guardian.policy_fingerprint(self.valid()),
            )


class ReceiptTests(unittest.TestCase):
    KEY = "stage03-test-signing-key"

    def scan_once(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        source = root / "clean.py"
        ledger = root / "ledger.jsonl"
        source.write_text(clean_source(), encoding="utf-8")
        gate = guardian.Guardian(
            ledger_path=ledger,
            signing_key=self.KEY,
        )
        slip = gate.scan(source)
        return temp, root, source, ledger, gate, slip

    def test_required_schema_fields(self):
        temp, _, _, _, _, slip = self.scan_once()
        self.addCleanup(temp.cleanup)
        payload = asdict(slip)
        for field in (
            "slip_schema_name", "slip_schema_version", "engine_version",
            "policy_schema_version", "policy_fingerprint",
            "file_fingerprint", "previous_slip_hash",
            "slip_fingerprint", "slip_signature",
        ):
            self.assertIn(field, payload)
        self.assertEqual(payload["slip_schema_version"], "1.0")

    def test_fingerprint_recomputes(self):
        temp, _, _, _, gate, slip = self.scan_once()
        self.addCleanup(temp.cleanup)
        self.assertEqual(
            gate._fingerprint_slip(asdict(slip)),
            slip.slip_fingerprint,
        )

    def test_protected_field_change_breaks_fingerprint(self):
        temp, _, _, _, gate, slip = self.scan_once()
        self.addCleanup(temp.cleanup)
        payload = asdict(slip)
        payload["policy_version"] = "changed"
        self.assertNotEqual(
            gate._fingerprint_slip(payload),
            slip.slip_fingerprint,
        )

    def test_policy_fingerprint_in_cli_and_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clean.py"
            ledger = root / "ledger.jsonl"
            source.write_text(clean_source(), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "guardian.py"),
                 "--hmac-key", self.KEY,
                 "--ledger", str(ledger),
                 "scan", str(source), "--json"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            cli_slip = json.loads(proc.stdout)
            ledger_slip = json.loads(
                ledger.read_text(encoding="utf-8").splitlines()[0]
            )["slip"]
            self.assertEqual(
                cli_slip["policy_fingerprint"],
                ledger_slip["policy_fingerprint"],
            )

    def test_human_output_contains_limitation_notice(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clean.py"
            ledger = root / "ledger.jsonl"
            source.write_text(clean_source(), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "guardian.py"),
                 "--hmac-key", self.KEY,
                 "--ledger", str(ledger),
                 "scan", str(source), "--explain"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(
                "A pass does not mean the content is completely safe.",
                proc.stdout,
            )
            self.assertIn("WHY THIS RESULT", proc.stdout)


class LedgerTests(unittest.TestCase):
    KEY = "stage03-ledger-key"

    def make_ledger(self, count=3):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        ledger = root / "ledger.jsonl"
        source = root / "clean.py"
        source.write_text(clean_source(), encoding="utf-8")
        gate = guardian.Guardian(ledger_path=ledger, signing_key=self.KEY)
        for index in range(count):
            source.write_text(clean_source(f"Clean {index}"), encoding="utf-8")
            gate.scan(source)
        return temp, root, ledger, gate

    def read_lines(self, ledger):
        return [json.loads(line) for line in ledger.read_text().splitlines()]

    def write_lines(self, ledger, entries):
        ledger.write_text(
            "\n".join(
                guardian.canonical_json_bytes(entry).decode("utf-8")
                for entry in entries
            ) + "\n",
            encoding="utf-8",
        )

    def test_normal_append_and_replay(self):
        temp, _, _, gate = self.make_ledger()
        self.addCleanup(temp.cleanup)
        valid, issues = gate.replay()
        self.assertTrue(valid, issues)

    def test_altered_slip_detected(self):
        temp, _, ledger, gate = self.make_ledger()
        self.addCleanup(temp.cleanup)
        entries = self.read_lines(ledger)
        entries[1]["slip"]["file_name"] = "altered.py"
        self.write_lines(ledger, entries)
        valid, issues = gate.replay()
        self.assertFalse(valid)
        self.assertTrue(any("fingerprint mismatch" in item for item in issues))

    def test_altered_previous_hash_detected(self):
        temp, _, ledger, gate = self.make_ledger()
        self.addCleanup(temp.cleanup)
        entries = self.read_lines(ledger)
        entries[1]["slip"]["previous_slip_hash"] = "f" * 64
        self.write_lines(ledger, entries)
        valid, issues = gate.replay()
        self.assertFalse(valid)
        self.assertTrue(any("previous hash" in item for item in issues))

    def test_inserted_entry_detected(self):
        temp, _, ledger, gate = self.make_ledger()
        self.addCleanup(temp.cleanup)
        entries = self.read_lines(ledger)
        entries.insert(1, copy.deepcopy(entries[0]))
        self.write_lines(ledger, entries)
        valid, issues = gate.replay()
        self.assertFalse(valid)
        self.assertTrue(any("previous hash" in item for item in issues))

    def test_reordered_entries_detected(self):
        temp, _, ledger, gate = self.make_ledger()
        self.addCleanup(temp.cleanup)
        entries = self.read_lines(ledger)
        entries[0], entries[1] = entries[1], entries[0]
        self.write_lines(ledger, entries)
        valid, issues = gate.replay()
        self.assertFalse(valid)
        self.assertTrue(any("previous hash" in item for item in issues))

    def test_malformed_final_line_detected(self):
        temp, _, ledger, gate = self.make_ledger()
        self.addCleanup(temp.cleanup)
        with ledger.open("ab") as handle:
            handle.write(b'{"broken":')
        with self.assertRaises(guardian.LedgerIntegrityError):
            gate.replay()

    def test_wrong_hmac_key_detected(self):
        temp, _, ledger, _ = self.make_ledger()
        self.addCleanup(temp.cleanup)
        wrong = guardian.Guardian(
            ledger_path=ledger,
            signing_key="wrong-key",
        )
        valid, issues = wrong.replay()
        self.assertFalse(valid)
        self.assertTrue(any("HMAC signature mismatch" in item for item in issues))

    def test_unsigned_requires_explicit_acknowledgement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clean.py"
            source.write_text(clean_source(), encoding="utf-8")
            gate = guardian.Guardian(ledger_path=root / "ledger.jsonl")
            with self.assertRaises(guardian.UnsignedModeError):
                gate.scan(source)

    def test_unsigned_dev_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clean.py"
            source.write_text(clean_source(), encoding="utf-8")
            gate = guardian.Guardian(
                ledger_path=root / "ledger.jsonl",
                unsigned_dev=True,
            )
            slip = gate.scan(source)
            self.assertTrue(slip.unsigned_dev_mode)
            self.assertEqual(slip.slip_signature, "")

    def test_concurrent_scans_form_one_linear_chain(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = root / "ledger.jsonl"
            sources = []
            for index in range(12):
                source = root / f"clean_{index}.py"
                source.write_text(clean_source(f"Concurrent {index}"), encoding="utf-8")
                sources.append(source)

            def run(path):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / "guardian.py"),
                     "--hmac-key", self.KEY,
                     "--ledger", str(ledger),
                     "scan", str(path), "--json"],
                    capture_output=True, text=True,
                )
                return proc.returncode, proc.stderr

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(run, sources))

            self.assertTrue(all(code == 0 for code, _ in results), results)
            gate = guardian.Guardian(ledger_path=ledger, signing_key=self.KEY)
            valid, issues = gate.replay()
            self.assertTrue(valid, issues)

            entries = self.read_lines(ledger)
            self.assertEqual(len(entries), len(sources))
            fingerprints = [entry["slip"]["slip_fingerprint"] for entry in entries]
            self.assertEqual(len(fingerprints), len(set(fingerprints)))
            expected = guardian.ZERO_HASH
            for entry in entries:
                self.assertEqual(entry["slip"]["previous_slip_hash"], expected)
                expected = entry["slip"]["slip_fingerprint"]


class FrozenAnalyzerTests(unittest.TestCase):
    def test_frozen_manifest_analyzer_block_hash(self):
        source = (ROOT / "guardian.py").read_text(encoding="utf-8")
        start = source.index("class ManifestParser:")
        end = source.index(
            "\n\n# =============================================================================\n# POLICY AND SCORING",
            start,
        )
        block = source[start:end]
        self.assertEqual(
            hashlib.sha256(block.encode("utf-8")).hexdigest(),
            "f47b9a570b75fea839207182b989f02e99212c5d99c09575537bf491f248d4ab",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
