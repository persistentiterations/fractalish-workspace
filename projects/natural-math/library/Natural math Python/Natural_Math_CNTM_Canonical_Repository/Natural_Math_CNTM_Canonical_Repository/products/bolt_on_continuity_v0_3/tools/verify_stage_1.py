"""Deterministic Stage 1 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.environment import EnvironmentSnapshot, build_doctor_report

FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket"}
AUTHORITY_FILES = (
    "docs/STAGE_1_CONTRACT.md",
    "docs/STAGE_1_GATES.md",
    "src/bolt_on/environment.py",
    "src/bolt_on/cli/main.py",
    "tests/test_stage_1.py",
    "tools/verify_stage_1.py",
)
STAGE_1_SOURCE_FILES = (
    "src/bolt_on/environment.py",
    "src/bolt_on/cli/main.py",
)


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 1 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [path for path in AUTHORITY_FILES if not (ROOT / path).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_import_boundary() -> None:
    # Stage verifiers inspect only the source authority owned by that stage.
    # Later stages may add separately qualified capabilities such as bounded
    # subprocess probes without retroactively violating Stage 1.
    for relative in STAGE_1_SOURCE_FILES:
        path = ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            forbidden = names & FORBIDDEN_IMPORTS
            if forbidden:
                fail(f"forbidden import {sorted(forbidden)} in {relative}")


def verify_vectors() -> None:
    snapshot = EnvironmentSnapshot(
        (3, 14, 6),
        "Windows",
        {"LOCALAPPDATA": "C:/Users/Example/AppData/Local"},
        "C:/Docker/docker.exe",
    )
    report = build_doctor_report(snapshot)
    if not report.ready:
        fail("qualified snapshot unexpectedly not ready")

    expected_body = {
        "authority_class": "OBSERVATION_ONLY",
        "checks": [
            {"check_id": "python.version", "detail": "3.14.6", "status": "PASS", "summary": "Python version"},
            {"check_id": "platform.system", "detail": "Windows", "status": "PASS", "summary": "Operating system"},
            {"check_id": "docker.cli", "detail": "C:/Docker/docker.exe", "status": "PASS", "summary": "Docker CLI discovery"},
            {"check_id": "storage.recommended_path", "detail": "C:\\Users\\Example\\AppData\\Local\\BoltOn\\Continuity", "status": "PASS", "summary": "Recommended local data path"},
            {"check_id": "authority.mode", "detail": "OBSERVATION_ONLY", "status": "PASS", "summary": "Authority mode"},
        ],
        "schema_version": 1,
    }
    if report.body() != expected_body:
        fail("canonical doctor structure mismatch")

    expected_json = json.dumps(expected_body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    if report.canonical_json() != expected_json:
        fail("canonical doctor serialization mismatch")


def manifest_digest() -> str:
    entries = []
    for relative in AUTHORITY_FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run() -> None:
    verify_files()
    verify_import_boundary()
    verify_vectors()
    print(f"STAGE 1 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 1 VERIFICATION PASSED")


if __name__ == "__main__":
    run()
