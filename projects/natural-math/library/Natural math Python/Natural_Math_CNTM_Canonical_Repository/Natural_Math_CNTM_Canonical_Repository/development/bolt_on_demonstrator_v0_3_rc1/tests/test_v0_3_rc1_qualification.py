from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "release_candidate"
    / "qualify_v0_3_rc1.py"
)
SPEC = importlib.util.spec_from_file_location("qualify_v0_3_rc1", MODULE_PATH)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


def make_minimal_repo(root: Path) -> tuple[Path, str]:
    dev = root / "development" / "bolt_on_demonstrator_v0_3"
    portability = dev / "portability"
    portability.mkdir(parents=True)
    (dev / "README.md").write_text("v0.3\n", encoding="utf-8", newline="\n")
    (portability / "portable_adapter_contract.py").write_text(
        "EXECUTION_AUTHORITY='NONE'\n"
        "class PortableHostAdapter:\n"
        "    def identity(self): pass\n"
        "    def normalize_event(self, raw_event): pass\n"
        "    def project_action(self, request, event): pass\n"
        "class ExampleAdapter(PortableHostAdapter):\n"
        "    def identity(self): pass\n"
        "    def normalize_event(self, raw_event): pass\n"
        "    def project_action(self, request, event): pass\n",
        encoding="utf-8",
        newline="\n",
    )
    frozen_v02 = root / "frozen" / "bolt_on" / "v0.2"
    frozen_v02.mkdir(parents=True)
    (frozen_v02 / "README.md").write_text("frozen\n", encoding="utf-8", newline="\n")
    manifest = frozen_v02 / "RELEASE_MANIFEST_SHA256.txt"
    manifest.write_text("fixture manifest\n", encoding="utf-8", newline="\n")
    (root / "tools").mkdir()
    return dev, hashlib.sha256(manifest.read_bytes()).hexdigest()


def evidence_for(spec: M.CommandSpec, *, suffix: str = "", count: int | None = None):
    observed = M.EXPECTED_TEST_COUNT if spec.validator == "tests" else 0
    if count is not None and spec.validator == "tests":
        observed = count
    seed = f"{spec.name}|{suffix}".encode()
    digest = hashlib.sha256(seed).hexdigest()
    return M.CommandEvidence(
        name=spec.name,
        command=spec.portable_command,
        marker=spec.marker,
        stdout_sha256=digest,
        stderr_sha256=hashlib.sha256(b"").hexdigest(),
        normalized_output_sha256=digest,
        observed_test_count=observed,
    )


class RC1QualificationTests(unittest.TestCase):
    def test_rc_version(self):
        self.assertEqual(M.RC_VERSION, "v0.3-RC1")

    def test_expected_source_commit(self):
        self.assertEqual(
            M.EXPECTED_SOURCE_COMMIT,
            "0e92ecaca48c4c5bf85bab658a4e693aae3d36f6",
        )

    def test_expected_test_count(self):
        self.assertEqual(M.EXPECTED_TEST_COUNT, 256)

    def test_expected_v02_manifest(self):
        self.assertEqual(len(M.EXPECTED_V02_RELEASE_MANIFEST_SHA256), 64)

    def test_rc_record_target(self):
        self.assertEqual(M.RC_RECORD_PATH.name, "RC1_QUALIFICATION.json")

    def test_sha256(self):
        self.assertEqual(len(M._sha256_bytes(b"x")), 64)

    def test_canonical_json_is_sorted(self):
        self.assertEqual(M._canonical_json({"b": 2, "a": 1}), '{"a":1,"b":2}')

    def test_canonical_digest_order_independent(self):
        self.assertEqual(
            M._canonical_digest({"b": 2, "a": 1}),
            M._canonical_digest({"a": 1, "b": 2}),
        )

    def test_is_digest_accepts_lowercase_sha(self):
        self.assertTrue(M._is_digest("a" * 64))

    def test_is_digest_rejects_uppercase(self):
        self.assertFalse(M._is_digest("A" * 64))

    def test_normalise_console_removes_timing(self):
        self.assertIn("Ran 256 tests in <TIME>s", M._normalise_console("Ran 256 tests in 0.481s"))

    def test_normalise_console_normalises_newlines(self):
        self.assertEqual(M._normalise_console("a\r\nb\r\n"), "a\nb\n")

    def test_manifest_excludes_pyc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("a")
            (root / "a.pyc").write_bytes(b"x")
            self.assertEqual([p.name for p in M._iter_manifest_files(root)], ["a.py"])

    def test_manifest_excludes_pycache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "a.pyc").write_bytes(b"x")
            self.assertEqual([p.name for p in M._iter_manifest_files(root)], ["a"])

    def test_manifest_excludes_rc_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a")
            (root / "RC1_QUALIFICATION.json").write_text("{}")
            files = list(M._iter_manifest_files(root, exclude_rc_record=True))
            self.assertEqual([p.name for p in files], ["a"])

    def test_manifest_changes_when_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "a"
            path.write_text("a")
            first = M._tree_manifest_digest(root)
            path.write_text("b")
            self.assertNotEqual(first, M._tree_manifest_digest(root))

    def test_manifest_ignores_rc_record_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a")
            rc = root / "RC1_QUALIFICATION.json"
            rc.write_text("a")
            first = M._tree_manifest_digest(root, exclude_rc_record=True)
            rc.write_text("b")
            self.assertEqual(first, M._tree_manifest_digest(root, exclude_rc_record=True))

    def test_read_key_values(self):
        values = M._read_key_values("A: 1\nA: 2\nB: x\n")
        self.assertEqual(values, {"A": ["1", "2"], "B": ["x"]})

    def test_single_requires_one_value(self):
        with self.assertRaises(M.QualificationError):
            M._single({"A": ["1", "2"]}, "A")

    def test_command_order(self):
        names = [spec.name for spec in M._command_specs(Path("/repo"))]
        self.assertEqual(
            names,
            [
                "stage_1_portable_adapter_contract",
                "workflow_host_self_qualification",
                "stage_2_second_independent_host",
                "stage_3_cross_host_replay",
                "queue_host_self_qualification",
                "stage_4_live_host_substitution",
                "stage_5_adversarial_adapter_qualification",
                "complete_v0_3_tests",
                "all_frozen_verification",
            ],
        )

    def test_portable_commands_do_not_store_python_path(self):
        for spec in M._command_specs(Path("/repo")):
            self.assertEqual(spec.portable_command[0], "python")

    def test_stage1_output_passes(self):
        spec = M._command_specs(Path("/repo"))[0]
        output = "Execution authority: NONE\nExecuted actions: 0\n" + spec.marker
        self.assertEqual(M._validate_stage_output(spec, output), 0)

    def test_stage1_nonzero_execution_fails(self):
        spec = M._command_specs(Path("/repo"))[0]
        output = "Execution authority: NONE\nExecuted actions: 1\n" + spec.marker
        with self.assertRaises(M.QualificationError):
            M._validate_stage_output(spec, output)

    def test_workflow_host_output_passes(self):
        spec = M._command_specs(Path("/repo"))[1]
        output = "Applied: 4\nRejected: 0\nFinal state: DONE\n" + spec.marker
        self.assertEqual(M._validate_stage_output(spec, output), 0)

    def test_queue_host_wrong_final_phase_fails(self):
        spec = M._command_specs(Path("/repo"))[4]
        output = "Applied: 4\nRejected: 0\nFinal phase: HELD\n" + spec.marker
        with self.assertRaises(M.QualificationError):
            M._validate_stage_output(spec, output)

    def test_stage4_output_passes(self):
        spec = M._command_specs(Path("/repo"))[5]
        output = (
            "Bolt-on execution authority: NONE\n"
            "Execution boundary: HOST_BOUNDARY_ONLY\n"
            "Executed host actions: 2\n"
            "Bolt-on executed actions: 0\n"
            "Campaign digest: " + "a" * 64 + "\n"
            "Replay digest: " + "a" * 64 + "\n"
            + spec.marker
        )
        self.assertEqual(M._validate_stage_output(spec, output), 0)

    def test_stage4_replay_mismatch_fails(self):
        spec = M._command_specs(Path("/repo"))[5]
        output = (
            "Bolt-on execution authority: NONE\nExecution boundary: HOST_BOUNDARY_ONLY\n"
            "Executed host actions: 2\nBolt-on executed actions: 0\n"
            "Campaign digest: " + "a" * 64 + "\nReplay digest: " + "b" * 64 + "\n" + spec.marker
        )
        with self.assertRaises(M.QualificationError):
            M._validate_stage_output(spec, output)

    def test_stage5_output_passes(self):
        spec = M._command_specs(Path("/repo"))[6]
        output = (
            "Bolt-on execution authority: NONE\nExecution boundary: HOST_BOUNDARY_ONLY\n"
            "Attack categories: 4\nAttacks executed: 48\nAttacks safely rejected: 48\n"
            "Baseline host actions: 2\nHost actions during attacks: 0\nBolt-on executed actions: 0\n"
            "Adversarial campaign digest: " + "c" * 64 + "\nReplay digest: " + "c" * 64 + "\n" + spec.marker
        )
        self.assertEqual(M._validate_stage_output(spec, output), 0)

    def test_stage5_attack_count_fails(self):
        spec = M._command_specs(Path("/repo"))[6]
        output = (
            "Bolt-on execution authority: NONE\nExecution boundary: HOST_BOUNDARY_ONLY\n"
            "Attack categories: 4\nAttacks executed: 47\nAttacks safely rejected: 48\n"
            "Baseline host actions: 2\nHost actions during attacks: 0\nBolt-on executed actions: 0\n"
            "Adversarial campaign digest: " + "c" * 64 + "\nReplay digest: " + "c" * 64 + "\n" + spec.marker
        )
        with self.assertRaises(M.QualificationError):
            M._validate_stage_output(spec, output)

    def test_complete_tests_output_passes(self):
        spec = M._command_specs(Path("/repo"))[7]
        self.assertEqual(M._validate_stage_output(spec, "Ran 256 tests in 1.0s\n\nOK\n"), 256)

    def test_complete_tests_wrong_count_fails(self):
        spec = M._command_specs(Path("/repo"))[7]
        with self.assertRaises(M.QualificationError):
            M._validate_stage_output(spec, "Ran 255 tests in 1.0s\n\nOK\n")

    def test_frozen_output_passes(self):
        spec = M._command_specs(Path("/repo"))[8]
        self.assertEqual(M._validate_stage_output(spec, spec.marker), 0)

    def test_adapter_scan_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            dev, _ = make_minimal_repo(Path(directory))
            self.assertEqual(M._adapter_authority_scan(dev), ())

    def test_adapter_scan_detects_execute_method(self):
        with tempfile.TemporaryDirectory() as directory:
            dev, _ = make_minimal_repo(Path(directory))
            path = dev / "portability" / "bad.py"
            path.write_text("class BadAdapter:\n    def execute(self): pass\n")
            self.assertTrue(any("execute" in hit for hit in M._adapter_authority_scan(dev)))

    def test_adapter_scan_detects_non_none_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            dev, _ = make_minimal_repo(Path(directory))
            path = dev / "portability" / "bad.py"
            path.write_text("BOLT_ON_EXECUTION_AUTHORITY='ALL'\n")
            self.assertTrue(any("NOT_NONE" in hit for hit in M._adapter_authority_scan(dev)))

    def test_adapter_scan_detects_missing_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            dev = Path(directory)
            (dev / "a.py").write_text("x=1\n")
            self.assertIn("PortableHostAdapter:MISSING", M._adapter_authority_scan(dev))

    def test_write_record_creates_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            digest = M._write_record({"a": 1}, path)
            payload = json.loads(path.read_text())
            self.assertEqual(payload["record_sha256"], digest)
            self.assertEqual(payload["record"], {"a": 1})

    def test_write_record_same_content_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            first = M._write_record({"a": 1}, path)
            second = M._write_record({"a": 1}, path)
            self.assertEqual(first, second)

    def test_write_record_rejects_different_existing_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            M._write_record({"a": 1}, path)
            with self.assertRaises(M.QualificationError):
                M._write_record({"a": 2}, path)

    def test_command_evidence_record_includes_count_only_when_present(self):
        spec = M._command_specs(Path("/repo"))[0]
        self.assertNotIn("count", evidence_for(spec).record())
        test_spec = M._command_specs(Path("/repo"))[7]
        self.assertEqual(evidence_for(test_spec).record()["count"], 256)

    def test_verify_v02_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, digest = make_minimal_repo(root)
            with patch.object(M, "EXPECTED_V02_RELEASE_MANIFEST_SHA256", digest):
                self.assertEqual(M._verify_v02_manifest(root), digest)

    def test_verify_v02_manifest_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_minimal_repo(root)
            with patch.object(M, "EXPECTED_V02_RELEASE_MANIFEST_SHA256", "0" * 64):
                with self.assertRaises(M.QualificationError):
                    M._verify_v02_manifest(root)

    def test_qualify_with_deterministic_fake_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, digest = make_minimal_repo(root)

            def runner(spec, repo):
                return evidence_for(spec)

            with patch.object(M, "EXPECTED_V02_RELEASE_MANIFEST_SHA256", digest):
                record, record_digest = M.qualify(
                    root,
                    runner=runner,
                    source_commit_provider=lambda repo: M.EXPECTED_SOURCE_COMMIT,
                )
            self.assertTrue(record["approved_for_freeze_procedure"])
            self.assertTrue(record["deterministic_second_pass"])
            self.assertEqual(record["observed_test_count"], 256)
            self.assertEqual(len(record_digest), 64)
            self.assertTrue((root / "development" / "bolt_on_demonstrator_v0_3" / "RC1_QUALIFICATION.json").is_file())

    def test_qualify_rejects_source_commit_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_minimal_repo(root)
            with self.assertRaises(M.QualificationError):
                M.qualify(
                    root,
                    runner=lambda spec, repo: evidence_for(spec),
                    source_commit_provider=lambda repo: "f" * 40,
                )

    def test_qualify_rejects_second_pass_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, digest = make_minimal_repo(root)
            calls = {"n": 0}

            def runner(spec, repo):
                calls["n"] += 1
                suffix = "changed" if calls["n"] > len(M._command_specs(root)) and spec.name == "stage_1_portable_adapter_contract" else ""
                return evidence_for(spec, suffix=suffix)

            with patch.object(M, "EXPECTED_V02_RELEASE_MANIFEST_SHA256", digest):
                with self.assertRaises(M.QualificationError):
                    M.qualify(
                        root,
                        runner=runner,
                        source_commit_provider=lambda repo: M.EXPECTED_SOURCE_COMMIT,
                    )

    def test_qualify_rejects_wrong_test_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, digest = make_minimal_repo(root)

            def runner(spec, repo):
                return evidence_for(spec, count=255)

            with patch.object(M, "EXPECTED_V02_RELEASE_MANIFEST_SHA256", digest):
                with self.assertRaises(M.QualificationError):
                    M.qualify(
                        root,
                        runner=runner,
                        source_commit_provider=lambda repo: M.EXPECTED_SOURCE_COMMIT,
                    )


if __name__ == "__main__":
    unittest.main()
