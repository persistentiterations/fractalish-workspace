from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README_STAGE_7.md",
    "docs/STAGE_7_CONTRACT.md",
    "docs/STAGE_7_GATES.md",
    "src/bolt_on_continuity_v0_2/operator_control.py",
    "tests/test_stage_7_operator_control.py",
]

REQUIRED_MARKERS = {
    "README_STAGE_7.md": ["An approval is evidence of operator intent only", "native execution authority"],
    "docs/STAGE_7_CONTRACT.md": ["APPROVE", "DENY", "native_execution_authorized: false"],
    "docs/STAGE_7_GATES.md": ["No execution surface", "native_execution_authorized = false"],
}

FORBIDDEN_TEXT = [
    "import docker",
    "from docker",
    "import subprocess",
    "from subprocess",
    "os.system",
    "Popen(",
    "socket.",
    "/var/run/docker.sock",
    "npipe://",
    "docker pause",
    "docker unpause",
    "docker stop",
    "docker restart",
    "docker kill",
    "docker rm",
    "docker exec",
    "docker run",
    "docker create",
    "from bolt_on_continuity.gateway",
    "from bolt_on_continuity.execution",
]

REQUIRED_TESTS = [
    "test_valid_approval",
    "test_valid_denial_while_disabled",
    "test_disabled_gateway_rejects_approval",
    "test_expired_request_rejected",
    "test_request_digest_tampering_rejected",
    "test_no_action_rejected",
    "test_short_container_id_rejected",
    "test_extra_request_field_rejected",
    "test_duplicate_decision_rejected",
    "test_conflicting_decision_rejected",
    "test_request_id_reuse_with_different_digest_rejected",
    "test_gateway_transitions",
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

    module_path = ROOT / "src/bolt_on_continuity_v0_2/operator_control.py"
    if module_path.is_file():
        text = module_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in FORBIDDEN_TEXT:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 7 token: {token}")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            fail(failures, f"operator control syntax error: {exc}")
            tree = None
        if tree is not None:
            assignments: dict[str, object] = {}
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    try:
                        assignments[node.targets[0].id] = ast.literal_eval(node.value)
                    except Exception:
                        pass
            if assignments.get("ALLOWED_ACTIONS") != ("HOLD", "RELEASE"):
                fail(failures, "Stage 7 action allowlist mismatch")
            if assignments.get("ALLOWED_DECISIONS") != ("APPROVE", "DENY"):
                fail(failures, "Stage 7 decision allowlist mismatch")

    tests_path = ROOT / "tests/test_stage_7_operator_control.py"
    tests_text = tests_path.read_text(encoding="utf-8") if tests_path.is_file() else ""
    for marker in REQUIRED_TESTS:
        if marker not in tests_text:
            fail(failures, f"missing Stage 7 test: {marker}")

    predecessor = ROOT / "tools/verify_stage_6.py"
    if not predecessor.is_file():
        fail(failures, "Stage 6 verifier missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 7 VERIFICATION: FAIL")
        return 1

    print("BOLT-ON CONTINUITY V0.2 STAGE 7 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
