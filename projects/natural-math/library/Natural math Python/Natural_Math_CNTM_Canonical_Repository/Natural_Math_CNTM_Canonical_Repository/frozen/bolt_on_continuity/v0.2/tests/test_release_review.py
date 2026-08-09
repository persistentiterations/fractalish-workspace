from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.release_review import (
    NOT_READY,
    READY,
    build_proposed_snapshot_manifest,
    review_proposed_freeze,
    serialize_review,
    validate_review,
)


def sample_files() -> dict[str, bytes]:
    return {
        "README.md": b"readme\n",
        "docs/contract.md": b"contract\n",
        "src/module.py": b"print('ok')\n",
    }


def ready_review(**overrides):
    args = {
        "rc1_verification_passed": True,
        "test_count": 142,
        "tests_passed": True,
        "frozen_regression_passed": True,
        "frozen_diff_empty": True,
        "working_tree_clean": True,
    }
    args.update(overrides)
    return review_proposed_freeze(build_proposed_snapshot_manifest(sample_files()), **args)


class ReleaseReviewTests(unittest.TestCase):
    def test_manifest_is_sorted_and_complete(self) -> None:
        manifest = build_proposed_snapshot_manifest(sample_files())
        self.assertEqual([entry["path"] for entry in manifest["entries"]], sorted(sample_files()))
        self.assertEqual(manifest["entry_count"], 3)

    def test_manifest_file_digests(self) -> None:
        files = sample_files()
        manifest = build_proposed_snapshot_manifest(files)
        by_path = {entry["path"]: entry for entry in manifest["entries"]}
        self.assertEqual(by_path["README.md"]["sha256"], hashlib.sha256(files["README.md"]).hexdigest())

    def test_path_escape_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_proposed_snapshot_manifest({"../escape": b"x"})

    def test_complete_review_is_ready(self) -> None:
        self.assertEqual(ready_review()["outcome"], READY)

    def test_wrong_test_count_fails_closed(self) -> None:
        self.assertEqual(ready_review(test_count=141)["outcome"], NOT_READY)

    def test_rc1_verification_is_required(self) -> None:
        self.assertEqual(ready_review(rc1_verification_passed=False)["outcome"], NOT_READY)

    def test_frozen_regression_is_required(self) -> None:
        self.assertEqual(ready_review(frozen_regression_passed=False)["outcome"], NOT_READY)

    def test_empty_frozen_diff_is_required(self) -> None:
        self.assertEqual(ready_review(frozen_diff_empty=False)["outcome"], NOT_READY)

    def test_clean_working_tree_is_required(self) -> None:
        self.assertEqual(ready_review(working_tree_clean=False)["outcome"], NOT_READY)

    def test_prohibited_claim_fails_closed(self) -> None:
        self.assertEqual(ready_review(claims=("production ready",))["outcome"], NOT_READY)

    def test_manifest_tamper_fails_closed(self) -> None:
        manifest = build_proposed_snapshot_manifest(sample_files())
        manifest["entries"][0]["byte_count"] += 1
        report = review_proposed_freeze(
            manifest, rc1_verification_passed=True, test_count=142, tests_passed=True,
            frozen_regression_passed=True, frozen_diff_empty=True, working_tree_clean=True,
        )
        self.assertEqual(report["outcome"], NOT_READY)

    def test_safe_authority(self) -> None:
        authority = ready_review()["authority"]
        self.assertTrue(authority["observation_only"])
        for key, value in authority.items():
            if key != "observation_only":
                self.assertFalse(value)

    def test_serialization_is_stable(self) -> None:
        report = ready_review()
        self.assertEqual(serialize_review(report), serialize_review(report))

    def test_review_tamper_detection(self) -> None:
        report = ready_review()
        tampered = copy.deepcopy(report)
        tampered["outcome"] = NOT_READY
        with self.assertRaises(ValueError):
            validate_review(tampered)


if __name__ == "__main__":
    unittest.main()
