from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README_STAGE_9.md",
    "docs/STAGE_9_CONTRACT.md",
    "docs/STAGE_9_GATES.md",
    "src/bolt_on_continuity_v0_2/installation_lifecycle.py",
    "tests/test_stage_9_installation_lifecycle.py",
]

REQUIRED_MARKERS = {
    "README_STAGE_9.md": ["repeat-install", "DELETE RECEIPT DATA", "native_execution_authorized = false"],
    "docs/STAGE_9_CONTRACT.md": ["PLAN_INSTALL", "PLAN_UNINSTALL_RETAIN_DATA", "container_mutation_authorized = false"],
    "docs/STAGE_9_GATES.md": ["ALREADY_INSTALLED", "Protected container", "Safe uninstall"],
}

FORBIDDEN = [
    "subprocess", "os.system", "Popen(", "socket.", "docker pause", "docker unpause",
    "docker stop", "docker restart", "docker kill", "docker rm", "docker exec",
    "docker run", "docker create", "open(", "write_text(", "write_bytes(", "mkdir(",
    "winreg", "systemctl", "sc.exe", "setx ",
]

REQUIRED_TESTS = [
    "test_clean_install_plan",
    "test_repeat_install_has_no_duplicate_work",
    "test_partial_install_fails_closed",
    "test_uninstall_defaults_to_retain_data",
    "test_confirmed_delete_data_plan",
    "test_delete_without_exact_confirmation_fails_closed",
    "test_protected_container_never_operation_target",
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

    source_path = ROOT / "src/bolt_on_continuity_v0_2/installation_lifecycle.py"
    if source_path.is_file():
        text = source_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in FORBIDDEN:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 9 token: {token}")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            fail(failures, f"Stage 9 syntax error: {exc}")
            tree = None
        if tree is not None:
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            for forbidden_import in {"docker", "subprocess", "socket", "winreg"}:
                if forbidden_import in imported:
                    fail(failures, f"forbidden Stage 9 import: {forbidden_import}")

    tests_path = ROOT / "tests/test_stage_9_installation_lifecycle.py"
    tests_text = tests_path.read_text(encoding="utf-8") if tests_path.is_file() else ""
    for marker in REQUIRED_TESTS:
        if marker not in tests_text:
            fail(failures, f"missing Stage 9 test: {marker}")

    previous = ROOT / "tools/verify_stage_8.py"
    if not previous.is_file():
        fail(failures, "Stage 8 verifier missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 9 VERIFICATION: FAIL")
        return 1
    print("BOLT-ON CONTINUITY V0.2 STAGE 9 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
