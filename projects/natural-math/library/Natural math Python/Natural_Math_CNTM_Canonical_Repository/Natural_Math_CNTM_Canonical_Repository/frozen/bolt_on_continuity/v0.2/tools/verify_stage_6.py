from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README_STAGE_6.md",
    "docs/STAGE_6_CONTRACT.md",
    "docs/STAGE_6_GATES.md",
    "src/bolt_on_continuity_v0_2/incident_review.py",
    "tests/test_stage_6_incident_review.py",
]

REQUIRED_MARKERS = {
    "README_STAGE_6.md": ["Incident Listing", "offline replay", "does not contact Docker"],
    "docs/STAGE_6_CONTRACT.md": ["projected or approved action is not represented as executed", "in memory only"],
    "docs/STAGE_6_GATES.md": ["Honest explanation", "No operational authority"],
}

FORBIDDEN_TEXT = [
    "subprocess",
    "os.system",
    "Popen(",
    "socket.",
    "docker pause",
    "docker unpause",
    "docker stop",
    "docker restart",
    "docker kill",
    "docker rm",
    "docker exec",
    "docker run",
    "docker create",
    "write_text(",
    "write_bytes(",
    "mkdir(",
]

REQUIRED_FUNCTIONS = {
    "validate_incident",
    "list_incidents",
    "explain_incident",
    "replay_incident",
    "create_export_package",
    "verify_export_package",
}

REQUIRED_TESTS = {
    "test_listing_order_is_stable",
    "test_projected_action_is_not_execution",
    "test_valid_replay",
    "test_tampered_receipt_digest_rejected",
    "test_broken_chain_rejected",
    "test_export_is_deterministic",
    "test_export_verifies",
    "test_tampered_export_fails",
}


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
            lowered = text.lower()
            for marker in markers:
                if marker.lower() not in lowered:
                    fail(failures, f"missing marker in {relative}: {marker!r}")

    implementation = ROOT / "src/bolt_on_continuity_v0_2/incident_review.py"
    if implementation.is_file():
        text = implementation.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in FORBIDDEN_TEXT:
            if token.lower() in lowered:
                fail(failures, f"forbidden Stage 6 token: {token}")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            fail(failures, f"Stage 6 syntax error: {exc}")
            tree = None
        if tree is not None:
            functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
            missing = REQUIRED_FUNCTIONS - functions
            if missing:
                fail(failures, f"missing Stage 6 functions: {sorted(missing)!r}")
            imported_roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            for forbidden in {"docker", "subprocess", "socket", "pathlib", "os"}:
                if forbidden in imported_roots:
                    fail(failures, f"forbidden Stage 6 import: {forbidden}")

    tests_path = ROOT / "tests/test_stage_6_incident_review.py"
    if tests_path.is_file():
        tests_text = tests_path.read_text(encoding="utf-8")
        for marker in REQUIRED_TESTS:
            if marker not in tests_text:
                fail(failures, f"missing Stage 6 test: {marker}")

    prior_verifier = ROOT / "tools/verify_stage_5.py"
    if not prior_verifier.is_file():
        fail(failures, "Stage 5 verifier missing")

    if failures:
        print("BOLT-ON CONTINUITY V0.2 STAGE 6 VERIFICATION: FAIL")
        return 1

    print("BOLT-ON CONTINUITY V0.2 STAGE 6 VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
