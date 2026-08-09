from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.rc1_qualification import (
    NOT_READY,
    READY,
    build_manifest,
    qualify_rc1,
    serialize_review_report,
    validate_manifest,
    validate_review_report,
)


def sample_files() -> dict[str, bytes]:
    return {
        "README.md": b"readme\n",
        "src/module.py": b"print('ok')\n",
        "docs/contract.md": b"contract\n",
    }


class RC1QualificationTests(unittest.TestCase):
    def test_manifest_is_sorted_and_complete(self) -> None:
        manifest = build_manifest(sample_files())
        self.assertEqual([entry["path"] for entry in manifest["entries"]], sorted(sample_files()))
        self.assertEqual(manifest["entry_count"], 3)

    def test_manifest_digest_and_file_digests(self) -> None:
        files = sample_files()
        manifest = build_manifest(files)
        by_path = {entry["path"]: entry for entry in manifest["entries"]}
        self.assertEqual(by_path["README.md"]["sha256"], hashlib.sha256(files["README.md"]).hexdigest())
        self.assertTrue(manifest["manifest_digest"].startswith("sha256:"))

    def test_input_order_does_not_change_manifest(self) -> None:
        files = sample_files()
        reversed_files = dict(reversed(list(files.items())))
        self.assertEqual(build_manifest(files), build_manifest(reversed_files))

    def test_changed_file_is_rejected(self) -> None:
        files = sample_files()
        manifest = build_manifest(files)
        changed = dict(files)
        changed["README.md"] = b"changed\n"
        with self.assertRaises(ValueError):
            validate_manifest(manifest, changed)

    def test_missing_file_is_rejected(self) -> None:
        files = sample_files()
        manifest = build_manifest(files)
        missing = dict(files)
        missing.pop("README.md")
        with self.assertRaises(ValueError):
            validate_manifest(manifest, missing)

    def test_extra_file_is_rejected(self) -> None:
        files = sample_files()
        manifest = build_manifest(files)
        extra = dict(files)
        extra["extra.txt"] = b"extra"
        with self.assertRaises(ValueError):
            validate_manifest(manifest, extra)

    def test_duplicate_manifest_entry_is_rejected(self) -> None:
        files = sample_files()
        manifest = build_manifest(files)
        tampered = copy.deepcopy(manifest)
        tampered["entries"].append(copy.deepcopy(tampered["entries"][0]))
        tampered["entry_count"] += 1
        with self.assertRaises(ValueError):
            validate_manifest(tampered, files)

    def test_path_escape_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_manifest({"../escape.txt": b"no"})

    def test_non_bytes_content_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_manifest({"bad.txt": "not bytes"})  # type: ignore[dict-item]

    def test_complete_evidence_is_ready(self) -> None:
        files = sample_files()
        report = qualify_rc1(
            build_manifest(files), files, test_count=127, tests_passed=True, frozen_regression_passed=True
        )
        self.assertEqual(report["outcome"], READY)

    def test_wrong_test_count_fails_closed(self) -> None:
        files = sample_files()
        report = qualify_rc1(
            build_manifest(files), files, test_count=126, tests_passed=True, frozen_regression_passed=True
        )
        self.assertEqual(report["outcome"], NOT_READY)

    def test_frozen_regression_is_required(self) -> None:
        files = sample_files()
        report = qualify_rc1(
            build_manifest(files), files, test_count=127, tests_passed=True, frozen_regression_passed=False
        )
        self.assertEqual(report["outcome"], NOT_READY)

    def test_prohibited_claim_fails_closed(self) -> None:
        files = sample_files()
        report = qualify_rc1(
            build_manifest(files), files, test_count=127, tests_passed=True,
            frozen_regression_passed=True, claims=("production ready",)
        )
        self.assertEqual(report["outcome"], NOT_READY)

    def test_safe_authority_and_stable_serialization(self) -> None:
        files = sample_files()
        report = qualify_rc1(
            build_manifest(files), files, test_count=127, tests_passed=True, frozen_regression_passed=True
        )
        self.assertTrue(report["authority"]["observation_only"])
        for key, value in report["authority"].items():
            if key != "observation_only":
                self.assertFalse(value)
        self.assertEqual(serialize_review_report(report), serialize_review_report(report))

    def test_review_tamper_detection(self) -> None:
        files = sample_files()
        report = qualify_rc1(
            build_manifest(files), files, test_count=127, tests_passed=True, frozen_regression_passed=True
        )
        tampered = copy.deepcopy(report)
        tampered["outcome"] = NOT_READY
        with self.assertRaises(ValueError):
            validate_review_report(tampered)


if __name__ == "__main__":
    unittest.main()
