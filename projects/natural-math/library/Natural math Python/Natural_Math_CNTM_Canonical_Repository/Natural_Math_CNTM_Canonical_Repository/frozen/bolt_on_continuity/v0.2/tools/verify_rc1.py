from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "rc1/README_RC1.md",
    "rc1/RC1_CONTRACT.md",
    "rc1/RC1_REVIEW_GATES.md",
    "src/bolt_on_continuity_v0_2/rc1_qualification.py",
    "tests/test_rc1_qualification.py",
]

REQUIRED_MARKERS = {
    "rc1/README_RC1.md": ["internal release candidate", "127-test", "leave `frozen` unchanged"],
    "rc1/RC1_CONTRACT.md": ["v0.2-rc1", "FAIL_CLOSED_RC1_NOT_READY", "release_freeze_authorized = false"],
    "rc1/RC1_REVIEW_GATES.md": ["RC1_READY_FOR_RELEASE_REVIEW", "human release review", "frozen diff must be empty"],
}

FORBIDDEN_MODULE_TEXT = [
    "subprocess", "os.system", "Popen(", "socket.", "docker pause", "docker unpause",
    "docker stop", "docker restart", "docker kill", "docker rm", "docker exec",
    "docker run", "docker create", "open(", "write_text(", "write_bytes(", "mkdir(",
    "systemctl", "winreg", "requests.", "urllib.", "git merge", "git tag", "git push",
]

REQUIRED_TESTS = [
    "test_manifest_is_sorted_and_complete",
    "test_changed_file_is_rejected",
    "test_missing_file_is_rejected",
    "test_extra_file_is_rejected",
    "test_duplicate_manifest_entry_is_rejected",
    "test_path_escape_is_rejected",
    "test_complete_evidence_is_ready",
    "test_wrong_test_count_fails_closed",
    "test_frozen_regression_is_required",
    "test_prohibited_claim_fails_closed",
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

    module_path = ROOT / "src/bolt_on_continuity_v0_2/rc1_qualification.py"
    if module_path.is_file():
        module_text = module_path.read_text(encoding="utf-8")
        try:
            ast.parse(module_text)
        except SyntaxError as exc:
            failures.append(f"module syntax error: {exc}")
        for forbidden in FORBIDDEN_MODULE_TEXT:
            if forbidden in module_text:
                failures.append(f"forbidden module surface: {forbidden}")
        for required in [
            "RC1_READY_FOR_RELEASE_REVIEW", "FAIL_CLOSED_RC1_NOT_READY",
            "QUALIFIED_SOURCE_COMMIT", "REQUIRED_TEST_COUNT = 127",
            "release_freeze_authorized", "production_readiness_claim_authorized",
        ]:
            if required not in module_text:
                failures.append(f"missing module contract marker: {required}")

    test_path = ROOT / "tests/test_rc1_qualification.py"
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
        print("BOLT-ON CONTINUITY V0.2 RC1 VERIFICATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("BOLT-ON CONTINUITY V0.2 RC1 VERIFICATION: PASS")
    print("RC1 remains review-only: no freeze, merge, tag, publication, or native execution authority.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
