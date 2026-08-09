"""Deterministic Stage 4 verifier."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.configuration_stage4 import AUTHORITY, ConfigurationOptions, build_configuration, validate_configuration
from bolt_on.discovery import EnrollmentRecord
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/STAGE_4_CONTRACT.md",
    "docs/STAGE_4_GATES.md",
    "src/bolt_on/configuration_stage4.py",
    "tests/test_stage_4.py",
    "tools/verify_stage_4.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "os"}
CID = "a" * 64


def fail(message: str) -> None:
    raise SystemExit(f"STAGE 4 VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/configuration_stage4.py"
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
            fail(f"forbidden import {sorted(forbidden)}")
    if AUTHORITY != ("NO_ACTION", "HOLD", "RELEASE"):
        fail("authority vocabulary mismatch")


def enrollment() -> EnrollmentRecord:
    base = {
        "schema_version": 1,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "container_id": CID,
        "display_name": "demo",
        "image": "example:1",
        "observed_state": "running",
        "observation_only": True,
        "gateway_enabled": False,
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    return EnrollmentRecord(CID, "demo", "example:1", "running", digest)


def verify_vectors() -> None:
    built = build_configuration(enrollment(), ConfigurationOptions())
    if not built.canonical_bytes().endswith(b"\n") or built.canonical_bytes().endswith(b"\n\n"):
        fail("canonical newline contract mismatch")
    parsed = json.loads(built.canonical_bytes())
    if validate_configuration(parsed).canonical_bytes() != built.canonical_bytes():
        fail("configuration round-trip mismatch")
    base = dict(parsed)
    digest = base.pop("configuration_digest")
    expected = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    if digest != expected:
        fail("configuration digest mismatch")
    expected_subject = {"container_id": CID, "display_name": "demo", "image": "example:1"}
    if parsed["subject"] != expected_subject:
        fail("subject vector mismatch")
    if parsed["mode"] != {
        "observation_only": True,
        "gateway_enabled": False,
        "approval_required": True,
        "autonomous_actions": False,
    }:
        fail("safe mode mismatch")


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
    print(f"STAGE 4 MANIFEST SHA256 {manifest_digest()}")
    print("BOLT-ON CONTINUITY V0.3 STAGE 4 VERIFICATION PASSED")


if __name__ == "__main__":
    run()