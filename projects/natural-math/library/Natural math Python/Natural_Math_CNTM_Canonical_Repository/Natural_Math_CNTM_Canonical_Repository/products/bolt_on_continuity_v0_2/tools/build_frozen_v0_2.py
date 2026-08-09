from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "products" / "bolt_on_continuity_v0_2"
DESTINATION = ROOT / "frozen" / "bolt_on_continuity" / "v0.2"
QUALIFIED_REVIEW_HEAD = "3574021a3b6735696c759579651abbb2ed9f2b2c"
PRODUCT = "Bolt-On Continuity for Docker"
VERSION = "0.2"
EXCLUDED_TOP_LEVEL = {"release_freeze"}
EXCLUDED_NAMES = {"__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)


def approved_source_files() -> list[Path]:
    files: list[Path] = []
    for path in SOURCE.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE)
        if relative.parts and relative.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        if any(part in EXCLUDED_NAMES for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        if relative.as_posix() == "tools/build_frozen_v0_2.py":
            continue
        if relative.as_posix() == "tools/verify_freeze_preparation.py":
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(SOURCE).as_posix())


def main() -> int:
    if DESTINATION.exists():
        print(f"REFUSING TO OVERWRITE EXISTING SNAPSHOT: {DESTINATION}")
        return 1

    status = git("status", "--porcelain")
    if status.returncode != 0 or status.stdout.strip():
        print("FREEZE ABORTED: working tree must be clean")
        return 1

    ancestor = git("merge-base", "--is-ancestor", QUALIFIED_REVIEW_HEAD, "HEAD")
    if ancestor.returncode != 0:
        print("FREEZE ABORTED: qualified release-review head is not an ancestor of HEAD")
        return 1

    source_files = approved_source_files()
    if not source_files:
        print("FREEZE ABORTED: no approved source files found")
        return 1

    DESTINATION.mkdir(parents=True, exist_ok=False)
    try:
        for source_path in source_files:
            relative = source_path.relative_to(SOURCE)
            destination_path = DESTINATION / relative
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination_path)

        release_record = {
            "authority": {
                "container_mutation_authorized": False,
                "gateway_enabled": False,
                "merge_authorized": False,
                "native_execution_authorized": False,
                "observation_only": True,
                "production_readiness_claim_authorized": False,
                "publication_authorized": False,
                "tag_authorized": False,
            },
            "frozen_destination": "frozen/bolt_on_continuity/v0.2",
            "product": PRODUCT,
            "qualified_release_review_head": QUALIFIED_REVIEW_HEAD,
            "release_status": "FROZEN_INTERNAL_RELEASE",
            "test_count_at_release_review": 156,
            "version": VERSION,
        }
        (DESTINATION / "RELEASE_RECORD.json").write_bytes(canonical_bytes(release_record))

        entries: list[dict[str, Any]] = []
        for path in sorted(DESTINATION.rglob("*")):
            if not path.is_file() or path.name == "MANIFEST.json":
                continue
            data = path.read_bytes()
            entries.append({
                "bytes": len(data),
                "path": path.relative_to(DESTINATION).as_posix(),
                "sha256": sha256(data),
            })

        manifest: dict[str, Any] = {
            "entry_count": len(entries),
            "entries": entries,
            "product": PRODUCT,
            "qualified_release_review_head": QUALIFIED_REVIEW_HEAD,
            "schema_version": "1",
            "version": VERSION,
        }
        manifest["manifest_digest"] = "sha256:" + sha256(canonical_bytes(manifest))
        (DESTINATION / "MANIFEST.json").write_bytes(canonical_bytes(manifest))
    except Exception:
        shutil.rmtree(DESTINATION, ignore_errors=True)
        raise

    print("BOLT-ON CONTINUITY V0.2 FROZEN SNAPSHOT CREATED")
    print(f"Destination: {DESTINATION.relative_to(ROOT)}")
    print(f"Manifest entries: {manifest['entry_count']}")
    print(f"Manifest digest: {manifest['manifest_digest']}")
    print("The snapshot is not merged, tagged, or published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
