from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    "README_STAGE_3.md",
    "docs/STAGE_3_CONTRACT.md",
    "docs/STAGE_3_GATES.md",
    "src/bolt_on_continuity_v0_2/container_enrollment.py",
    "tests/test_stage_3_enrollment.py",
]

MARKERS = {
    "README_STAGE_3.md": ["full 64-character container ID", "docker container ls", "docker inspect"],
    "docs/STAGE_3_CONTRACT.md": ["Names and images are not authority", "CONFIRMATION_MISMATCH", "observation_only"],
    "docs/STAGE_3_GATES.md": ["Full-ID authority", "same-name container", "Stage 4"],
}

FORBIDDEN_SOURCE = [
    "docker pause",
    "docker unpause",
    "docker stop",
    "docker restart",
    "docker kill",
    "docker rm",
    "docker exec",
    "docker run",
    "docker create",
    "shell=True",
    "os.system",
    "Popen(",
    "/var/run/docker.sock",
    "npipe://",
]

EXPECTED_DISCOVERY = ("container", "ls", "--all", "--no-trunc", "--format", "{{json .}}")
EXPECTED_INSPECT_PREFIX = ("inspect",)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def literal_assignment(tree: ast.AST, name: str):
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise KeyError(name)


def main() -> int:
    failures: list[str] = []

    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            fail(failures, f"missing required file: {relative}")

    for relative, markers in MARKERS.items():
        path = ROOT / relative
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                if marker not in text:
                    fail(failures, f"missing marker in {relative}: {marker!r}")

    source_path = ROOT / "src/bolt_on_continuity_v0_2/container_enrollment.py"
    if source_path.is_file():
        source = source_path.read_text(encoding="utf-8")
        lowered = source.lower()
        for token in FORBIDDEN_SOURCE:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 3 token: {token}")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            fail(failures, f"Stage 3 syntax error: {exc}")
            tree = None
        if tree is not None:
            try:
                if tuple(literal_assignment(tree, "DISCOVERY_ARGS")) != EXPECTED_DISCOVERY:
                    fail(failures, "unexpected discovery command vector")
                if tuple(literal_assignment(tree, "INSPECT_PREFIX")) != EXPECTED_INSPECT_PREFIX:
                    fail(failures, "unexpected inspect command prefix")
                timeout = literal_assignment(tree, "PROBE_TIMEOUT_SECONDS")
                if not isinstance(timeout, int) or timeout <= 0:
                    fail(failures, "probe timeout must be a positive integer")
            except (KeyError, ValueError, TypeError) as exc:
                fail(failures, f"could not validate Stage 3 constants: {exc}")

            imported_roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            for forbidden_import in {"docker", "bolt_on_continuity"}:
                if forbidden_import in imported_roots:
                    fail(failures, f"forbidden operational import: {forbidden_import}")

        if "^[0-9a-f]{64}$" not in source:
            fail(failures, "full lowercase 64-character ID validation missing")
        if "confirmation != candidate.container_id" not in source:
            fail(failures, "exact confirmation check missing")

    tests_path = ROOT / "tests/test_stage_3_enrollment.py"
    tests_text = tests_path.read_text(encoding="utf-8") if tests_path.is_file() else ""
    required_tests = [
        "test_discovery_sorted_by_full_id",
        "test_short_id_rejected",
        "test_name_only_selection_rejected",
        "test_confirmation_mismatch_prevents_inspect",
        "test_inspection_id_mismatch_rejected",
        "test_same_name_replacement_does_not_inherit",
        "test_enrollment_digest_stable_and_safe_defaults",
        "test_only_exact_allowlisted_commands_used",
    ]
    for marker in required_tests:
        if marker not in tests_text:
            fail(failures, f"missing Stage 3 test: {marker}")

    if not (ROOT / "tools/verify_stage_2.py").is_file():
        fail(failures, "Stage 2 verifier missing")
    if not (REPO_ROOT / "frozen/bolt_on_continuity_v0_1").is_dir():
        fail(failures, "authoritative frozen v0.1 directory missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 3 VERIFICATION: FAIL")
        return 1
    print("BOLT-ON CONTINUITY V0.2 STAGE 3 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
