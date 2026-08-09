from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README_STAGE_10.md",
    "docs/STAGE_10_CONTRACT.md",
    "docs/STAGE_10_GATES.md",
    "src/bolt_on_continuity_v0_2/end_to_end_qualification.py",
    "tests/test_stage_10_end_to_end_qualification.py",
]

REQUIRED_MARKERS = {
    "README_STAGE_10.md": ["end-to-end usability qualification", "release-candidate qualification", "native_execution_authorized = false"],
    "docs/STAGE_10_CONTRACT.md": ["RELEASE_CANDIDATE_READY", "FAIL_CLOSED_NOT_READY", "production_readiness_claim_authorized = false"],
    "docs/STAGE_10_GATES.md": ["Complete evidence set", "Exclusion disclosure", "release-candidate package"],
}

FORBIDDEN = [
    "subprocess", "os.system", "Popen(", "socket.", "docker pause", "docker unpause",
    "docker stop", "docker restart", "docker kill", "docker rm", "docker exec",
    "docker run", "docker create", "open(", "write_text(", "write_bytes(", "mkdir(",
    "systemctl", "sc.exe", "winreg",
]

REQUIRED_TESTS = [
    "test_complete_qualification_is_ready",
    "test_input_order_does_not_change_report",
    "test_missing_evidence_fails_closed",
    "test_failed_evidence_fails_closed",
    "test_authority_expansion_fails_closed",
    "test_tamper_detection",
]


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file():
            fail(failures, f"missing required file: {relative}")

    for relative, markers in REQUIRED_MARKERS.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(failures, f"missing marker in {relative}: {marker}")

    module_path = ROOT / "src/bolt_on_continuity_v0_2/end_to_end_qualification.py"
    if module_path.is_file():
        source = module_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            fail(failures, f"module syntax error: {exc}")
        else:
            functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
            for required_function in {"qualify_release_candidate", "validate_qualification_report", "serialize_qualification_report"}:
                if required_function not in functions:
                    fail(failures, f"missing function: {required_function}")
        lowered = source.lower()
        for forbidden in FORBIDDEN:
            if forbidden.lower() in lowered:
                fail(failures, f"forbidden operational surface in Stage 10 module: {forbidden}")

    test_path = ROOT / "tests/test_stage_10_end_to_end_qualification.py"
    if test_path.is_file():
        test_text = test_path.read_text(encoding="utf-8")
        for test_name in REQUIRED_TESTS:
            if f"def {test_name}(" not in test_text:
                fail(failures, f"missing required test: {test_name}")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 10 VERIFICATION: FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("BOLT-ON CONTINUITY V0.2 STAGE 10 VERIFICATION: PASS")
    print("Stage 10 end-to-end qualification structure is complete and authority-bounded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
