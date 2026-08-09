"""Deterministic Stage 3 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.discovery import DISCOVERY_VECTOR, inspect_and_enroll, parse_discovery, select

AUTHORITY_FILES = (
    "docs/STAGE_3_CONTRACT.md",
    "docs/STAGE_3_GATES.md",
    "src/bolt_on/discovery.py",
    "src/bolt_on/cli/main.py",
    "tests/test_stage_3.py",
    "tools/verify_stage_3.py",
)
FORBIDDEN_DOCKER_COMMANDS = {
    "pause", "unpause", "stop", "restart", "kill", "remove", "exec",
    "create", "run", "network", "volume", "image",
}
CID = "a" * 64


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 3 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def _literal_string_sequence(node: ast.AST) -> tuple[str, ...] | None:
    if not isinstance(node, (ast.Tuple, ast.List)):
        return None
    values: list[str] = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        values.append(element.value)
    return tuple(values)


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/discovery.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    # Inspect only literal Docker command vectors. Ordinary data fields such as
    # "image" are allowed; mutation subcommands are not.
    for node in ast.walk(tree):
        vector = _literal_string_sequence(node)
        if not vector or vector[0] != "docker":
            continue
        forbidden = set(vector[1:]) & FORBIDDEN_DOCKER_COMMANDS
        if forbidden:
            fail(f"forbidden Docker mutation command: {sorted(forbidden)}")

    if DISCOVERY_VECTOR != ("docker", "container", "ls", "--all", "--no-trunc", "--format", "{{json .}}"):
        fail("discovery vector mismatch")


def verify_vectors() -> None:
    line = json.dumps({"ID": CID, "Names": "demo", "Image": "example:1", "State": "RUNNING", "Status": "Up"})
    candidates = parse_discovery(line)
    candidate = select(candidates, CID, CID)
    calls = []

    class Result:
        returncode = 0
        stdout = json.dumps([{"Id": CID, "Name": "/demo", "Platform": "linux"}])

    def runner(vector, timeout):
        calls.append((tuple(vector), timeout))
        return Result()

    record = inspect_and_enroll(candidate, runner)
    if calls != [(("docker", "inspect", CID), 5.0)]:
        fail("inspection vector mismatch")
    expected_base = {
        "container_id": CID,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "display_name": "demo",
        "gateway_enabled": False,
        "image": "example:1",
        "observation_only": True,
        "observed_state": "running",
        "schema_version": 1,
    }
    payload = json.dumps(expected_base, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    expected_digest = hashlib.sha256(payload).hexdigest()
    if record.enrollment_digest != expected_digest:
        fail("enrollment digest mismatch")


def manifest_digest() -> str:
    entries = []
    for relative in AUTHORITY_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run() -> None:
    verify_files()
    verify_source_boundary()
    verify_vectors()
    print(f"STAGE 3 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 3 VERIFICATION PASSED")


if __name__ == "__main__":
    run()
