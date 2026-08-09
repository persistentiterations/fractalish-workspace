from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "final_stage" / "freeze_v0_3.py"
SPEC = importlib.util.spec_from_file_location("freeze_v0_3", MODULE_PATH)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


class FreezeV03Tests(unittest.TestCase):
    def test_release(self):
        self.assertEqual(M.RELEASE, "v0.3")

    def test_rc_version(self):
        self.assertEqual(M.RC_VERSION, "v0.3-RC1")

    def test_freeze_source_commit(self):
        self.assertEqual(len(M.EXPECTED_FREEZE_SOURCE_COMMIT), 40)

    def test_rc_source_commit(self):
        self.assertEqual(len(M.EXPECTED_RC_SOURCE_COMMIT), 40)

    def test_target(self):
        self.assertEqual(M.TARGET.as_posix(), "frozen/bolt_on/v0.3")

    def test_verifier_path(self):
        self.assertEqual(M.VERIFY.as_posix(), "tools/verify_bolt_on_v0_3.py")

    def test_expected_test_count(self):
        self.assertEqual(M.EXPECTED_TEST_COUNT, 256)

    def test_expected_host_families(self):
        self.assertEqual(M.EXPECTED_HOST_FAMILIES, 2)

    def test_expected_substitutions(self):
        self.assertEqual(M.EXPECTED_SUBSTITUTIONS, 1)

    def test_expected_attacks(self):
        self.assertEqual(M.EXPECTED_ATTACKS, 48)

    def test_expected_manifest_entries(self):
        self.assertEqual(M.EXPECTED_FROZEN_MANIFEST_ENTRIES, 20)

    def test_stage_order(self):
        self.assertEqual(
            [row[0] for row in M.STAGES],
            [
                "stage_1_portable_adapter_contract",
                "workflow_host_self_qualification",
                "stage_2_second_independent_host",
                "stage_3_cross_host_replay",
                "queue_host_self_qualification",
                "stage_4_live_host_substitution",
                "stage_5_adversarial_adapter_qualification",
            ],
        )

    def test_stage_markers_unique(self):
        markers = [row[2] for row in M.STAGES]
        self.assertEqual(len(markers), len(set(markers)))

    def test_sha256_bytes(self):
        self.assertEqual(len(M.sha256_bytes(b"x")), 64)

    def test_canonical_digest_is_order_independent(self):
        self.assertEqual(
            M.canonical_digest({"b": 2, "a": 1}),
            M.canonical_digest({"a": 1, "b": 2}),
        )

    def test_is_digest_accepts_lowercase_sha(self):
        self.assertTrue(M.is_digest("a" * 64))

    def test_is_digest_rejects_uppercase(self):
        self.assertFalse(M.is_digest("A" * 64))

    def test_is_digest_rejects_wrong_length(self):
        self.assertFalse(M.is_digest("a" * 63))

    def test_normalise_console_removes_timing(self):
        result = M.normalise_console("Ran 256 tests in 0.480s\r\nOK\r\n")
        self.assertIn("Ran 256 tests in <TIME>s", result)
        self.assertNotIn("0.480", result)

    def test_read_key_values(self):
        values = M.read_key_values("A: 1\nB: 2\nA: 3\n")
        self.assertEqual(values, {"A": ["1", "3"], "B": ["2"]})

    def test_single_success(self):
        self.assertEqual(M.single({"A": ["1"]}, "A"), "1")

    def test_single_missing_raises(self):
        with self.assertRaises(M.FreezeError):
            M.single({}, "A")

    def test_single_duplicate_raises(self):
        with self.assertRaises(M.FreezeError):
            M.single({"A": ["1", "2"]}, "A")

    def test_iter_files_ignores_bytecode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("x", encoding="utf-8")
            (root / "a.pyc").write_bytes(b"x")
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "a.pyc").write_bytes(b"x")
            self.assertEqual([path.name for path in M.iter_files(root)], ["a.py"])

    def test_iter_files_excludes_rc_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a", encoding="utf-8")
            (root / "RC1_QUALIFICATION.json").write_text("{}", encoding="utf-8")
            names = [path.name for path in M.iter_files(root, exclude_rc_record=True)]
            self.assertEqual(names, ["a"])

    def test_iter_files_excludes_release_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a", encoding="utf-8")
            (root / "RELEASE_MANIFEST_SHA256.txt").write_text("x", encoding="utf-8")
            names = [path.name for path in M.iter_files(root, exclude_release_manifest=True)]
            self.assertEqual(names, ["a"])

    def test_iter_files_excludes_subtree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a", encoding="utf-8")
            excluded = root / "skip"
            excluded.mkdir()
            (excluded / "b").write_text("b", encoding="utf-8")
            names = [path.relative_to(root).as_posix() for path in M.iter_files(root, exclude_subtree=excluded)]
            self.assertEqual(names, ["a"])

    def test_tree_manifest_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b").write_text("b", encoding="utf-8")
            (root / "a").write_text("a", encoding="utf-8")
            first = M.tree_manifest_digest(root)
            second = M.tree_manifest_digest(root)
            self.assertEqual(first, second)

    def test_tree_manifest_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "a"
            path.write_text("a", encoding="utf-8")
            first = M.tree_manifest_digest(root)
            path.write_text("b", encoding="utf-8")
            self.assertNotEqual(first, M.tree_manifest_digest(root))

    def test_tree_manifest_excludes_rc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("a", encoding="utf-8")
            rc = root / "RC1_QUALIFICATION.json"
            rc.write_text("{}", encoding="utf-8")
            first = M.tree_manifest_digest(root, exclude_rc_record=True)
            rc.write_text('{"changed":true}', encoding="utf-8")
            self.assertEqual(first, M.tree_manifest_digest(root, exclude_rc_record=True))

    def test_tree_manifest_empty_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(M.FreezeError):
                M.tree_manifest_digest(Path(directory))

    def test_exact_copy_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            (source / "a").write_text("a", encoding="utf-8")
            (target / "a").write_text("a", encoding="utf-8")
            (target / "FREEZE_RECEIPT.json").write_text("{}", encoding="utf-8")
            self.assertTrue(M.exact_copy_matches(source, target))

    def test_exact_copy_detects_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            (source / "a").write_text("a", encoding="utf-8")
            (target / "a").write_text("b", encoding="utf-8")
            self.assertFalse(M.exact_copy_matches(source, target))

    def test_extend_aggregate_verifier(self):
        original = 'checks = (\n        tools / "verify_bolt_on_v0_2.py",\n)\n'
        updated = M.extend_aggregate_verifier(original)
        self.assertIn('tools / "verify_bolt_on_v0_3.py"', updated)

    def test_extend_aggregate_rejects_duplicate(self):
        original = (
            '        tools / "verify_bolt_on_v0_2.py",\n'
            '        tools / "verify_bolt_on_v0_3.py",\n'
        )
        with self.assertRaises(M.FreezeError):
            M.extend_aggregate_verifier(original)

    def test_extend_aggregate_rejects_missing_anchor(self):
        with self.assertRaises(M.FreezeError):
            M.extend_aggregate_verifier("checks = ()\n")

    def test_release_verifier_marker(self):
        self.assertIn("BOLT-ON v0.3 FROZEN VERIFICATION PASSED", M.release_verifier_source())

    def test_release_verifier_expected_entries(self):
        self.assertIn("EXPECTED_ENTRIES = 20", M.release_verifier_source())

    def test_release_verifier_compiles(self):
        compile(M.release_verifier_source(), "verify_bolt_on_v0_3.py", "exec")

    def test_build_release_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for index in range(20):
                (target / f"f{index:02d}").write_text(str(index), encoding="utf-8")
            digest, count = M.build_release_manifest(target)
            self.assertTrue(M.is_digest(digest))
            self.assertEqual(count, 20)
            self.assertEqual(len((target / "RELEASE_MANIFEST_SHA256.txt").read_text().splitlines()), 20)

    def test_build_release_manifest_wrong_count_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "only").write_text("x", encoding="utf-8")
            with self.assertRaises(M.FreezeError):
                M.build_release_manifest(target)

    def test_validate_stage1_passes(self):
        M.validate_stage_output("stage_1_portable_adapter_contract", "Executed actions: 0\n")

    def test_validate_stage1_rejects_execution(self):
        with self.assertRaises(M.FreezeError):
            M.validate_stage_output("stage_1_portable_adapter_contract", "Executed actions: 1\n")

    def test_validate_workflow_host_passes(self):
        M.validate_stage_output(
            "workflow_host_self_qualification",
            "Applied: 4\nRejected: 0\nFinal state: DONE\n",
        )

    def test_validate_workflow_host_rejects_state(self):
        with self.assertRaises(M.FreezeError):
            M.validate_stage_output(
                "workflow_host_self_qualification",
                "Applied: 4\nRejected: 0\nFinal state: PAUSED\n",
            )

    def test_validate_queue_host_passes(self):
        M.validate_stage_output(
            "queue_host_self_qualification",
            "Applied: 4\nRejected: 0\nFinal phase: COMPLETE\n",
        )

    def test_validate_stage4_passes(self):
        M.validate_stage_output(
            "stage_4_live_host_substitution",
            "Executed host actions: 2\nBolt-on executed actions: 0\nCampaign digest: abc\nReplay digest: abc\n",
        )

    def test_validate_stage4_rejects_digest_mismatch(self):
        with self.assertRaises(M.FreezeError):
            M.validate_stage_output(
                "stage_4_live_host_substitution",
                "Executed host actions: 2\nBolt-on executed actions: 0\nCampaign digest: abc\nReplay digest: def\n",
            )

    def test_validate_stage5_passes(self):
        M.validate_stage_output(
            "stage_5_adversarial_adapter_qualification",
            "Attack categories: 4\nAttacks executed: 48\nAttacks safely rejected: 48\n"
            "Baseline host actions: 2\nHost actions during attacks: 0\n"
            "Bolt-on executed actions: 0\nAdversarial campaign digest: abc\nReplay digest: abc\n",
        )

    def test_validate_stage5_rejects_attack_action(self):
        with self.assertRaises(M.FreezeError):
            M.validate_stage_output(
                "stage_5_adversarial_adapter_qualification",
                "Attack categories: 4\nAttacks executed: 48\nAttacks safely rejected: 48\n"
                "Baseline host actions: 2\nHost actions during attacks: 1\n"
                "Bolt-on executed actions: 0\nAdversarial campaign digest: abc\nReplay digest: abc\n",
            )

    def test_load_rc_missing_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(M.FreezeError):
                M.load_and_validate_rc(Path(directory))

    def test_load_rc_malformed_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / M.RC_RECORD
            path.parent.mkdir(parents=True)
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(M.FreezeError):
                M.load_and_validate_rc(root)

    def test_receipt_digest_is_deterministic(self):
        record = {"release": "v0.3", "status": "FROZEN"}
        self.assertEqual(M.canonical_digest(record), M.canonical_digest(dict(reversed(list(record.items())))))


if __name__ == "__main__":
    unittest.main()
