#!/usr/bin/env python3
"""Independently verify the immutable Bolt-On Demonstrator v0.4 frozen release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

RELEASE = "v0.4"
SOURCE_COMMIT = "b7992579104f9c9db9acd9d0fa78b622d9542037"
EXPECTED_ENTRIES = 25

THIS_FILE = Path(__file__).resolve()
REPO = THIS_FILE.parent.parent
FROZEN_ROOT = REPO / "frozen" / "bolt_on" / RELEASE
MANIFEST_PATH = FROZEN_ROOT / "FILE_MANIFEST_SHA256.txt"
RELEASE_DIGEST_PATH = FROZEN_ROOT / "RELEASE_MANIFEST_SHA256.txt"
METADATA_PATH = FROZEN_ROOT / "RELEASE_METADATA.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(reason: str) -> int:
    print(f"BOLT-ON v0.4 FROZEN VERIFICATION FAILED: {reason}")
    return 1


def git_bytes(relative_path: str) -> bytes:
    source_path = f"development/bolt_on_demonstrator_v0_4/{relative_path}"
    completed = subprocess.run(
        ["git", "show", f"{SOURCE_COMMIT}:{source_path}"],
        cwd=REPO,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(source_path)
    return completed.stdout


def parse_manifest(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        if "  " not in line:
            raise ValueError(f"line {number} malformed")
        digest, relative = line.split("  ", 1)
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"line {number} digest invalid")
        if not relative or relative.startswith("/") or "\\" in relative or ".." in Path(relative).parts:
            raise ValueError(f"line {number} path invalid")
        rows.append((relative, digest))
    return rows


def main() -> int:
    if not FROZEN_ROOT.is_dir():
        return fail("release directory missing")
    for required in (MANIFEST_PATH, RELEASE_DIGEST_PATH, METADATA_PATH):
        if not required.is_file():
            return fail(f"missing {required.name}")

    manifest_bytes = MANIFEST_PATH.read_bytes()
    try:
        manifest_text = manifest_bytes.decode("utf-8")
        rows = parse_manifest(manifest_text)
    except (UnicodeDecodeError, ValueError) as exc:
        return fail(str(exc))

    if len(rows) != EXPECTED_ENTRIES:
        return fail(f"expected {EXPECTED_ENTRIES} manifest entries, found {len(rows)}")
    paths = [path for path, _ in rows]
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        return fail("manifest paths are not unique canonical order")

    expected_release_digest = RELEASE_DIGEST_PATH.read_text(encoding="ascii").strip()
    actual_release_digest = sha256(manifest_bytes)
    if expected_release_digest != actual_release_digest:
        return fail("release manifest digest mismatch")

    try:
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fail("metadata invalid")
    expected_metadata = {
        "entry_count": EXPECTED_ENTRIES,
        "freeze_commit_pending": True,
        "release": RELEASE,
        "release_manifest_sha256": actual_release_digest,
        "source_commit": SOURCE_COMMIT,
        "source_root": "development/bolt_on_demonstrator_v0_4",
        "status": "FROZEN",
    }
    if metadata != expected_metadata:
        return fail("metadata mismatch")

    payload_files = sorted(
        path.relative_to(FROZEN_ROOT).as_posix()
        for path in FROZEN_ROOT.rglob("*")
        if path.is_file()
        and path.name not in {
            "FILE_MANIFEST_SHA256.txt",
            "RELEASE_MANIFEST_SHA256.txt",
            "RELEASE_METADATA.json",
        }
    )
    if payload_files != paths:
        return fail("frozen payload set differs from manifest")

    for relative, expected_digest in rows:
        frozen = FROZEN_ROOT / relative
        data = frozen.read_bytes()
        if sha256(data) != expected_digest:
            return fail(f"file digest mismatch: {relative}")
        try:
            committed = git_bytes(relative)
        except RuntimeError:
            return fail(f"source commit path missing: {relative}")
        if data != committed:
            return fail(f"frozen file differs from source commit: {relative}")

    print(f"BOLT-ON v0.4 FROZEN VERIFICATION PASSED: {EXPECTED_ENTRIES} files")
    print(f"Source commit: {SOURCE_COMMIT}")
    print(f"Release manifest SHA-256: {actual_release_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
