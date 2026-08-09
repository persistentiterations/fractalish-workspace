from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    "README_STAGE_2.md",
    "docs/STAGE_2_CONTRACT.md",
    "docs/STAGE_2_GATES.md",
    "src/bolt_on_continuity_v0_2/prerequisite_checker.py",
    "tests/test_stage_2_prerequisites.py",
]

REQUIRED_MARKERS = {
    "README_STAGE_2.md": ["observation-only", "docker version", "docker info"],
    "docs/STAGE_2_CONTRACT.md": ["CPython 3.11", "Linux-container", "fails closed"],
    "docs/STAGE_2_GATES.md": ["Fixed read-only probes", "gateway_enabled = false"],
}

FORBIDDEN_TEXT = [
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

ALLOWED_DOCKER_ARGUMENTS = {
    ("version", "--format", "{{json .}}"),
    ("info", "--format", "{{json .}}"),
}


def fail(messages: list[str], message: str) -> None:
    messages.append(message)
    print(f"FAIL: {message}")


def assigned_literals(tree: ast.AST) -> dict[str, object]:
    values: dict[str, object] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            values[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
    return values


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

    checker_path = ROOT / "src/bolt_on_continuity_v0_2/prerequisite_checker.py"
    if checker_path.is_file():
        checker_text = checker_path.read_text(encoding="utf-8")
        lowered = checker_text.lower()
        for token in FORBIDDEN_TEXT:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 2 token in prerequisite checker: {token}")

        try:
            tree = ast.parse(checker_text)
        except SyntaxError as exc:
            fail(failures, f"prerequisite checker syntax error: {exc}")
            tree = None

        if tree is not None:
            imported_roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            for forbidden_import in {"docker", "bolt_on_continuity"}:
                if forbidden_import in imported_roots:
                    fail(failures, f"forbidden operational import: {forbidden_import}")

            constants = assigned_literals(tree)
            version_args = constants.get("VERSION_ARGS")
            info_args = constants.get("INFO_ARGS")
            actual = {tuple(version_args or ()), tuple(info_args or ())}
            if actual != ALLOWED_DOCKER_ARGUMENTS:
                fail(failures, f"unexpected Docker probe allowlist: {sorted(actual)!r}")
            timeout = constants.get("PROBE_TIMEOUT_SECONDS")
            if not isinstance(timeout, int) or timeout <= 0:
                fail(failures, "probe timeout must be a positive integer")

    boundary_tool = ROOT / "tools/verify_stage_1.py"
    if not boundary_tool.is_file():
        fail(failures, "Stage 1 verifier missing")

    tests_path = ROOT / "tests/test_stage_2_prerequisites.py"
    tests_text = tests_path.read_text(encoding="utf-8") if tests_path.is_file() else ""
    required_test_markers = [
        "test_missing_docker_fails_without_probe",
        "test_windows_container_mode_rejected",
        "test_remote_endpoint_rejected_without_probe",
        "test_canonical_output_is_stable",
        "test_only_exact_allowlisted_probes_are_used",
    ]
    for marker in required_test_markers:
        if marker not in tests_text:
            fail(failures, f"missing Stage 2 test: {marker}")

    frozen_v01 = REPO_ROOT / "frozen/bolt_on_continuity_v0_1"
    if not frozen_v01.is_dir():
        fail(failures, "authoritative frozen v0.1 directory missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 2 VERIFICATION: FAIL")
        return 1

    print("BOLT-ON CONTINUITY V0.2 STAGE 2 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
