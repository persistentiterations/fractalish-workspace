from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "release_review/README_RELEASE_REVIEW.md",
    "release_review/RELEASE_REVIEW_CONTRACT.md",
    "release_review/RELEASE_REVIEW_GATES.md",
    "src/bolt_on_continuity_v0_2/release_review.py",
    "tests/test_release_review.py",
]

REQUIRED_MARKERS = {
    "release_review/README_RELEASE_REVIEW.md": ["PROPOSED_FREEZE_READY_FOR_APPROVAL", "does not create a frozen snapshot"],
    "release_review/RELEASE_REVIEW_CONTRACT.md": ["FAIL_CLOSED_RELEASE_REVIEW", "release_freeze_authorized = false"],
    "release_review/RELEASE_REVIEW_GATES.md": ["human release owner", "does not authorize creating the frozen snapshot"],
}

FORBIDDEN = [
    "subprocess", "os.system", "Popen(", "socket.", "docker pause", "docker unpause",
    "docker stop", "docker restart", "docker kill", "docker rm", "docker exec",
    "docker run", "docker create", "open(", "write_text(", "write_bytes(", "mkdir(",
    "systemctl", "winreg", "requests.", "urllib.", "git merge", "git tag", "git push",
]

REQUIRED_TESTS = [
    "test_manifest_is_sorted_and_complete",
    "test_complete_review_is_ready",
    "test_wrong_test_count_fails_closed",
    "test_rc1_verification_is_required",
    "test_frozen_regression_is_required",
    "test_empty_frozen_diff_is_required",
    "test_clean_working_tree_is_required",
    "test_prohibited_claim_fails_closed",
    "test_manifest_tamper_fails_closed",
    "test_review_tamper_detection",
]


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            failures.append(f"missing required file: {relative}")

    for relative, markers in REQUIRED_MARKERS.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                failures.append(f"missing marker in {relative}: {marker}")

    module_path = ROOT / "src/bolt_on_continuity_v0_2/release_review.py"
    if module_path.is_file():
        module_text = module_path.read_text(encoding="utf-8")
        try:
            ast.parse(module_text)
        except SyntaxError as exc:
            failures.append(f"module syntax error: {exc}")
        for forbidden in FORBIDDEN:
            if forbidden in module_text:
                failures.append(f"forbidden module surface: {forbidden}")
        for marker in [
            "PROPOSED_FREEZE_READY_FOR_APPROVAL", "FAIL_CLOSED_RELEASE_REVIEW",
            "REQUIRED_TEST_COUNT = 142", "PROPOSED_DESTINATION",
            "release_freeze_authorized", "tag_authorized",
        ]:
            if marker not in module_text:
                failures.append(f"missing module contract marker: {marker}")

    test_path = ROOT / "tests/test_release_review.py"
    if test_path.is_file():
        test_text = test_path.read_text(encoding="utf-8")
        try:
            ast.parse(test_text)
        except SyntaxError as exc:
            failures.append(f"test syntax error: {exc}")
        for test_name in REQUIRED_TESTS:
            if f"def {test_name}(" not in test_text:
                failures.append(f"missing required test: {test_name}")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 RELEASE REVIEW VERIFICATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("BOLT-ON CONTINUITY V0.2 RELEASE REVIEW VERIFICATION: PASS")
    print("Review preparation remains non-mutating: no freeze, merge, tag, publication, or native execution authority.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
