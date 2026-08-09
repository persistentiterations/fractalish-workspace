from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    "README_STAGE_4.md",
    "docs/STAGE_4_CONTRACT.md",
    "docs/STAGE_4_GATES.md",
    "src/bolt_on_continuity_v0_2/product_configuration.py",
    "tests/test_stage_4_configuration.py",
]

MARKERS = {
    "README_STAGE_4.md": ["observation_only = true", "gateway_enabled = false", "configuration digest"],
    "docs/STAGE_4_CONTRACT.md": ["Canonical JSON", "native_execution_authorized", "No write side effect"],
    "docs/STAGE_4_GATES.md": ["Exact subject binding", "Safe storage description", "Stage 5"],
}

FORBIDDEN = [
    "import docker",
    "from docker",
    "import subprocess",
    "from subprocess",
    "os.system",
    "Popen(",
    "subprocess.run",
    "docker pause",
    "docker unpause",
    "docker stop",
    "docker restart",
    "docker kill",
    "docker rm",
    "/var/run/docker.sock",
    "open(",
    "write_text(",
    "write_bytes(",
    "mkdir(",
]

REQUIRED_TESTS = [
    "test_deterministic_configuration_and_bytes",
    "test_safe_defaults",
    "test_digest_tampering_rejected",
    "test_extra_field_rejected",
    "test_missing_field_rejected",
    "test_short_or_uppercase_id_rejected",
    "test_authority_expansion_rejected",
    "test_unsafe_paths_rejected",
    "test_invalid_bounds_rejected",
    "test_unsafe_enrollment_defaults_rejected",
]


def fail(failures: list[str], message: str) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def assigned_literal(tree: ast.AST, name: str):
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

    source_path = ROOT / "src/bolt_on_continuity_v0_2/product_configuration.py"
    if source_path.is_file():
        source = source_path.read_text(encoding="utf-8")
        lowered = source.lower()
        for token in FORBIDDEN:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 4 token: {token}")
        try:
            tree = ast.parse(source)
            actions = assigned_literal(tree, "ALLOWED_ACTIONS")
            retention = assigned_literal(tree, "ALLOWED_RETENTION_MODES")
            if tuple(actions) != ("NO_ACTION", "HOLD", "RELEASE"):
                fail(failures, f"unexpected action vocabulary: {actions!r}")
            if set(retention) != {"bounded_count", "retain_until_operator_deletes"}:
                fail(failures, f"unexpected retention modes: {retention!r}")
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            for forbidden_import in {"docker", "subprocess", "bolt_on_continuity"}:
                if forbidden_import in imported:
                    fail(failures, f"forbidden operational import: {forbidden_import}")
        except (SyntaxError, ValueError, KeyError) as exc:
            fail(failures, f"could not inspect Stage 4 source: {exc}")

    tests_path = ROOT / "tests/test_stage_4_configuration.py"
    if tests_path.is_file():
        tests = tests_path.read_text(encoding="utf-8")
        for marker in REQUIRED_TESTS:
            if marker not in tests:
                fail(failures, f"missing Stage 4 test: {marker}")

    if not (ROOT / "src/bolt_on_continuity_v0_2/container_enrollment.py").is_file():
        fail(failures, "Stage 3 enrollment implementation missing")
    if not (REPO_ROOT / "frozen/bolt_on_continuity_v0_1").is_dir():
        fail(failures, "authoritative frozen v0.1 directory missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 4 VERIFICATION: FAIL")
        return 1
    print("BOLT-ON CONTINUITY V0.2 STAGE 4 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
