from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README_STAGE_5.md",
    "docs/STAGE_5_CONTRACT.md",
    "docs/STAGE_5_GATES.md",
    "src/bolt_on_continuity_v0_2/local_cli.py",
    "tests/test_stage_5_cli.py",
]

REQUIRED_MARKERS = {
    "README_STAGE_5.md": ["observation-only", "plans only"],
    "docs/STAGE_5_CONTRACT.md": ["version", "config-check", "OBSERVATION_PLAN_READY", "does not start a daemon"],
    "docs/STAGE_5_GATES.md": ["Plans are not execution", "native_execution_authorized = false"],
}

FORBIDDEN_TEXT = [
    "subprocess",
    "os.system",
    "Popen(",
    "socket.",
    "threading",
    "multiprocessing",
    "docker pause",
    "docker unpause",
    "docker stop",
    "docker restart",
    "docker kill",
    "docker rm",
    "docker exec",
    "docker run",
    "docker create",
    "open(",
    "write_text(",
    "write_bytes(",
    "mkdir(",
]

EXPECTED_COMMANDS = {"version", "config-check", "status", "start", "stop"}
EXPECTED_STATES = {"NOT_STARTED", "OBSERVATION_PLAN_READY", "STOP_PLAN_READY"}


def fail(failures: list[str], message: str) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def literal_assignment(tree: ast.AST, name: str) -> object:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    value = node.value
                    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "frozenset" and len(value.args) == 1:
                        return ast.literal_eval(value.args[0])
                    return ast.literal_eval(value)
    raise ValueError(f"assignment not found: {name}")


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

    cli_path = ROOT / "src/bolt_on_continuity_v0_2/local_cli.py"
    if cli_path.is_file():
        text = cli_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in FORBIDDEN_TEXT:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 5 token: {token}")
        try:
            tree = ast.parse(text)
            commands = set(literal_assignment(tree, "ALLOWED_COMMANDS"))
            states = set(literal_assignment(tree, "ALLOWED_STATES"))
            if commands != EXPECTED_COMMANDS:
                fail(failures, f"unexpected command set: {sorted(commands)!r}")
            if states != EXPECTED_STATES:
                fail(failures, f"unexpected lifecycle state set: {sorted(states)!r}")
            imported_roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            for forbidden in {"docker", "bolt_on_continuity", "subprocess", "socket", "threading", "multiprocessing"}:
                if forbidden in imported_roots:
                    fail(failures, f"forbidden Stage 5 import: {forbidden}")
        except (SyntaxError, ValueError) as exc:
            fail(failures, f"could not inspect Stage 5 CLI: {exc}")

    tests_path = ROOT / "tests/test_stage_5_cli.py"
    tests_text = tests_path.read_text(encoding="utf-8") if tests_path.is_file() else ""
    for marker in [
        "test_unknown_command_rejected",
        "test_tampered_configuration_rejected",
        "test_start_is_plan_only",
        "test_stop_does_not_mutate_container",
        "test_safety_invariants_on_all_commands",
        "test_canonical_output_is_stable",
    ]:
        if marker not in tests_text:
            fail(failures, f"missing Stage 5 test: {marker}")

    if not (ROOT / "tools/verify_stage_4.py").is_file():
        fail(failures, "Stage 4 verifier missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 5 VERIFICATION: FAIL")
        return 1

    print("BOLT-ON CONTINUITY V0.2 STAGE 5 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
