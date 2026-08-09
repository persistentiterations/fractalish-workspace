#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "frozen" / "bolt_on_continuity" / "v0.2"
MANIFEST = SNAPSHOT / "MANIFEST.json"
EXPECTED_PRODUCT = "Bolt-On Continuity for Docker"
EXPECTED_VERSION = "0.2"
EXPECTED_REVIEW_HEAD = "3574021a3b6735696c759579651abbb2ed9f2b2c"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def fail(message: str) -> int:
    print(f"BOLT-ON CONTINUITY v0.2 FROZEN VERIFICATION FAILED: {message}")
    return 1


def main() -> int:
    if not MANIFEST.is_file():
        return fail("missing MANIFEST.json")

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid manifest: {exc}")

    expected_fields = {
        "entry_count", "entries", "manifest_digest", "product",
        "qualified_release_review_head", "schema_version", "version",
    }
    if set(manifest) != expected_fields:
        return fail("manifest fields mismatch")
    if manifest["product"] != EXPECTED_PRODUCT or manifest["version"] != EXPECTED_VERSION:
        return fail("manifest product identity mismatch")
    if manifest["qualified_release_review_head"] != EXPECTED_REVIEW_HEAD:
        return fail("qualified review head mismatch")

    digest = manifest.get("manifest_digest")
    payload = dict(manifest)
    payload.pop("manifest_digest", None)
    expected_manifest_digest = "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()
    if digest != expected_manifest_digest:
        return fail("manifest digest mismatch")

    entries = manifest.get("entries")
    if not isinstance(entries, list) or manifest.get("entry_count") != len(entries):
        return fail("manifest entry count mismatch")

    declared: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"bytes", "path", "sha256"}:
            return fail("malformed manifest entry")
        relative = entry["path"]
        if not isinstance(relative, str) or not relative or relative in declared:
            return fail("invalid or duplicate manifest path")
        declared.add(relative)
        path = SNAPSHOT / relative
        if not path.is_file():
            return fail(f"missing file: {relative}")
        data = path.read_bytes()
        if entry["bytes"] != len(data):
            return fail(f"byte count mismatch: {relative}")
        if entry["sha256"] != hashlib.sha256(data).hexdigest():
            return fail(f"digest mismatch: {relative}")

    actual = {
        path.relative_to(SNAPSHOT).as_posix()
        for path in SNAPSHOT.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    if actual != declared:
        missing = sorted(declared - actual)
        extra = sorted(actual - declared)
        return fail(f"snapshot file-set mismatch; missing={missing}, extra={extra}")

    release_record = SNAPSHOT / "RELEASE_RECORD.json"
    if not release_record.is_file():
        return fail("missing RELEASE_RECORD.json")
    try:
        record = json.loads(release_record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid release record: {exc}")
    if record.get("release_status") != "FROZEN_INTERNAL_RELEASE":
        return fail("release status mismatch")
    if record.get("test_count_at_release_review") != 156:
        return fail("release test count mismatch")
    if record.get("qualified_release_review_head") != EXPECTED_REVIEW_HEAD:
        return fail("release review head mismatch")

    print(f"BOLT-ON CONTINUITY v0.2 FROZEN VERIFICATION PASSED: {len(entries)} files")
    print(f"Qualified review head: {EXPECTED_REVIEW_HEAD}")
    print(f"Release manifest SHA-256: {digest.removeprefix('sha256:')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
