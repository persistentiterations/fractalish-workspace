from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README_STAGE_8.md",
    "docs/STAGE_8_CONTRACT.md",
    "docs/STAGE_8_GATES.md",
    "src/bolt_on_continuity_v0_2/recovery_classifier.py",
    "tests/test_stage_8_recovery.py",
]

REQUIRED_MARKERS = {
    "README_STAGE_8.md": ["observation-only", "duplicate-action suppression", "receipt-store"],
    "docs/STAGE_8_CONTRACT.md": ["SUBJECT_REPLACED", "FAIL_CLOSED_STORE", "SUPPRESS_DUPLICATE"],
    "docs/STAGE_8_GATES.md": ["REQUIRE_REENROLLMENT", "RESUME_OBSERVATION_ONLY", "No execution"],
}

FORBIDDEN = [
    "subprocess", "os.system", "Popen(", "socket.", "docker pause", "docker unpause",
    "docker stop", "docker restart", "docker kill", "docker rm", "docker exec",
    "docker run", "docker create", "open(", "write_text(", "write_bytes(", "mkdir(",
]

REQUIRED_TESTS = [
    "test_healthy_restart_resumes_observation_only",
    "test_terminal_request_is_suppressed",
    "test_conflicting_request_id_fails_closed",
    "test_same_name_replacement_requires_reenrollment",
    "test_all_store_failures_fail_closed",
    "test_canonical_serialization_is_stable",
]


def fail(failures: list[str], message: str) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            fail(failures, f"missing required file: {relative}")

    for relative, markers in REQUIRED_MARKERS.items():
        path = ROOT / relative
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                if marker not in text:
                    fail(failures, f"missing marker in {relative}: {marker!r}")

    source_path = ROOT / "src/bolt_on_continuity_v0_2/recovery_classifier.py"
    if source_path.is_file():
        text = source_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in FORBIDDEN:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 8 token: {token}")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            fail(failures, f"Stage 8 syntax error: {exc}")
            tree = None
        if tree is not None:
            imported_roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            for forbidden_import in {"docker", "subprocess", "socket", "bolt_on_continuity"}:
                if forbidden_import in imported_roots:
                    fail(failures, f"forbidden Stage 8 import: {forbidden_import}")
            function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
            for required_function in {"classify_recovery", "serialize_recovery_report"}:
                if required_function not in function_names:
                    fail(failures, f"missing Stage 8 function: {required_function}")

    tests_path = ROOT / "tests/test_stage_8_recovery.py"
    tests_text = tests_path.read_text(encoding="utf-8") if tests_path.is_file() else ""
    for marker in REQUIRED_TESTS:
        if marker not in tests_text:
            fail(failures, f"missing Stage 8 test: {marker}")

    prior_verifier = ROOT / "tools/verify_stage_7.py"
    if not prior_verifier.is_file():
        fail(failures, "Stage 7 verifier missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 8 VERIFICATION: FAIL")
        return 1
    print("BOLT-ON CONTINUITY V0.2 STAGE 8 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
