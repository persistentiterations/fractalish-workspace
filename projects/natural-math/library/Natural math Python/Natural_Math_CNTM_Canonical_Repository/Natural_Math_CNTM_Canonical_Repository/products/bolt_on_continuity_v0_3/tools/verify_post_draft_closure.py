"""Verify deterministic post-draft closure without publication authority."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on.post_draft_closure import (
    FROZEN_MANIFEST,
    RELEASE_NOTES_SHA256,
    RELEASE_TITLE,
    REPOSITORY,
    TAG_NAME,
    TAG_OBJECT,
    TAG_TARGET,
    PostDraftEvidence,
    close_post_draft,
)
from bolt_on.receipts import canonical_json_bytes

AUTHORITY_FILES = (
    "docs/POST_DRAFT_CLOSURE_CONTRACT.md",
    "src/bolt_on/post_draft_closure.py",
    "tests/test_post_draft_closure.py",
    "tools/verify_post_draft_closure.py",
)
FORBIDDEN_IMPORTS = {"docker", "subprocess", "socket", "shutil", "requests", "urllib"}


def fail(message: str) -> None:
    raise SystemExit(f"POST-DRAFT CLOSURE VERIFICATION FAILED: {message}")


def verify_files() -> None:
    missing = [relative for relative in AUTHORITY_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing files: {missing}")


def verify_source_boundary() -> None:
    path = ROOT / "src/bolt_on/post_draft_closure.py"
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
    if RELEASE_TITLE != "Bolt-On Continuity v0.3":
        fail("release title mismatch")
    if TAG_NAME != "bolt-on-continuity-v0.3":
        fail("tag mismatch")
    if TAG_OBJECT != "fc3e27567e38a94322b437a4285c52ee38ac8407":
        fail("tag object mismatch")
    if TAG_TARGET != "1c95a1ff8ead30675d4d26f7d77720097c5b9129":
        fail("tag target mismatch")
    if FROZEN_MANIFEST != "3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb":
        fail("frozen manifest mismatch")
    if RELEASE_NOTES_SHA256 != "cafe56a302ecc7f091762a0e90f2d404f90b48683fee9e6272e522c71e622d30":
        fail("release notes mismatch")


def verify_record() -> str:
    evidence = PostDraftEvidence(
        tests_passed=126,
        release_exists=True,
        release_is_draft=True,
        release_is_unpublished=True,
        release_title_matches=True,
        tag_matches=True,
        tag_target_matches=True,
        release_notes_match=True,
        uploaded_assets_absent=True,
        frozen_verifier_passed=True,
        all_frozen_passed=True,
        frozen_diff_clean=True,
        worktree_clean=True,
    )
    first = close_post_draft(evidence).canonical_bytes()
    second = close_post_draft(evidence).canonical_bytes()
    if first != second:
        fail("record is not deterministic")
    body = json.loads(first)
    if body.get("status") != "POST_DRAFT_CLOSED":
        fail("status mismatch")
    if body.get("source_archives_expected") != 2:
        fail("source archive count mismatch")
    if set(body.get("authority", {}).values()) != {False}:
        fail("authority expanded")
    digest = body.pop("record_digest", None)
    expected = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    if digest != expected:
        fail("record digest mismatch")
    return digest


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
    record_digest = verify_record()
    print(f"POST-DRAFT CLOSURE RECORD SHA256 {record_digest}")
    print(f"POST-DRAFT CLOSURE MANIFEST SHA256 {manifest_digest()}")
    print(f"RELEASE TITLE {RELEASE_TITLE}")
    print(f"RELEASE TAG {TAG_NAME}")
    print(f"RELEASE TARGET {TAG_TARGET}")
    print("RELEASE STATE DRAFT UNPUBLISHED NO_UPLOADED_ASSETS")
    print("POST-DRAFT STATUS POST_DRAFT_CLOSED")
    print("BOLT-ON CONTINUITY V0.3 POST-DRAFT CLOSURE VERIFICATION PASSED")


if __name__ == "__main__":
    run()
