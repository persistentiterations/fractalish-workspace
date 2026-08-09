"""Verify deterministic GitHub release preparation without publishing."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.receipts import canonical_json_bytes
from bolt_on.release_preparation import (
    FROZEN_MANIFEST,
    RELEASE_NOTES,
    RELEASE_TITLE,
    REPOSITORY,
    TAG_NAME,
    TAG_OBJECT,
    TAG_TARGET,
    ReleasePreparationEvidence,
    prepare_release,
)

AUTHORITY_FILES = (
    "docs/RELEASE_PREPARATION_CONTRACT.md",
    "src/bolt_on/release_preparation.py",
    "tests/test_release_preparation.py",
    "tools/verify_release_preparation.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "shutil", "requests"}


def fail(message: str) -> None:
    raise SystemExit(f"RELEASE PREPARATION VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/release_preparation.py"
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
    if REPOSITORY != "BonAcqui-LLC/cntm-natural-math-canonical-library":
        fail("repository mismatch")
    if TAG_NAME != "bolt-on-continuity-v0.3":
        fail("tag mismatch")
    if TAG_OBJECT != "fc3e27567e38a94322b437a4285c52ee38ac8407":
        fail("tag object mismatch")
    if TAG_TARGET != "1c95a1ff8ead30675d4d26f7d77720097c5b9129":
        fail("tag target mismatch")
    if FROZEN_MANIFEST != "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb":
        fail("frozen manifest mismatch")
    if RELEASE_TITLE != "Bolt-On Continuity v0.3":
        fail("release title mismatch")


def verify_notes() -> str:
    lowered = RELEASE_NOTES.lower()
    required = (
        "observation-only",
        "does not run a background observer",
        "mutate containers",
        "does not claim production readiness",
        "release assets: none",
    )
    missing = [phrase for phrase in required if phrase not in lowered]
    if missing:
        fail(f"release-note boundary missing: {missing}")
    return hashlib.sha256(RELEASE_NOTES.encode("utf-8")).hexdigest()


def verify_record() -> tuple[str, str]:
    evidence = ReleasePreparationEvidence(110, True, True, True, True, True, True)
    first = prepare_release(evidence).canonical_bytes()
    second = prepare_release(evidence).canonical_bytes()
    if first != second:
        fail("record is not deterministic")
    body = json.loads(first)
    if body.get("status") != "READY_FOR_RELEASE_DECISION":
        fail("status mismatch")
    if body.get("draft") is not True or body.get("prerelease") is not True:
        fail("release mode mismatch")
    if body.get("assets") != []:
        fail("assets must be empty")
    if set(body.get("authority", {}).values()) != {False}:
        fail("authority expanded")
    digest = body.pop("record_digest", None)
    expected = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    if digest != expected:
        fail("record digest mismatch")
    return digest, body["release_notes_sha256"]


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
    notes_digest = verify_notes()
    record_digest, record_notes_digest = verify_record()
    if notes_digest != record_notes_digest:
        fail("release notes digest mismatch")
    print(f"RELEASE PREPARATION RECORD SHA256 {record_digest}")
    print(f"RELEASE PREPARATION MANIFEST SHA256 {manifest_digest()}")
    print(f"RELEASE NOTES SHA256 {notes_digest}")
    print(f"RELEASE TAG {TAG_NAME}")
    print(f"RELEASE TARGET {TAG_TARGET}")
    print("RELEASE MODE DRAFT PRERELEASE NO_ASSETS")
    print("RELEASE STATUS READY_FOR_RELEASE_DECISION")
    print("BOLT-ON CONTINUITY V0.3 RELEASE PREPARATION VERIFICATION PASSED")


if __name__ == "__main__":
    run()
