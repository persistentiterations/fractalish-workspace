from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

PRODUCT = "Bolt-On Continuity for Docker"
VERSION = "0.2"
CANDIDATE = "v0.2-rc1"
QUALIFIED_RC1_HEAD = "e183ddb6b4fd245229e1e466304e87c9e3cb762f"
PROPOSED_DESTINATION = "frozen/bolt_on_continuity/v0.2"
REQUIRED_TEST_COUNT = 142
READY = "PROPOSED_FREEZE_READY_FOR_APPROVAL"
NOT_READY = "FAIL_CLOSED_RELEASE_REVIEW"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROHIBITED_CLAIMS = (
    "production ready", "production-ready", "zero drift", "zero failure",
    "universal compatibility", "autonomous remediation",
)
SAFE_AUTHORITY = {
    "container_mutation_authorized": False,
    "gateway_enabled": False,
    "merge_authorized": False,
    "native_execution_authorized": False,
    "observation_only": True,
    "production_readiness_claim_authorized": False,
    "publication_authorized": False,
    "release_freeze_authorized": False,
    "tag_authorized": False,
}


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("review_digest", None)
    return "sha256:" + hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _normalize_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith(("/", "~")) or ":" in value:
        raise ValueError("unsafe manifest path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("unsafe manifest path")
    return path.as_posix()


def build_proposed_snapshot_manifest(files: Mapping[str, bytes]) -> dict[str, Any]:
    if not isinstance(files, Mapping) or not files:
        raise ValueError("files must be a non-empty mapping")
    entries = []
    seen: set[str] = set()
    for raw_path, content in files.items():
        path = _normalize_path(raw_path)
        if path in seen:
            raise ValueError("duplicate manifest path")
        if not isinstance(content, bytes):
            raise ValueError("manifest content must be bytes")
        seen.add(path)
        entries.append({"byte_count": len(content), "path": path, "sha256": hashlib.sha256(content).hexdigest()})
    entries.sort(key=lambda item: item["path"])
    manifest: dict[str, Any] = {
        "candidate": CANDIDATE,
        "entry_count": len(entries),
        "entries": entries,
        "product": PRODUCT,
        "proposed_destination": PROPOSED_DESTINATION,
        "qualified_rc1_head": QUALIFIED_RC1_HEAD,
        "version": VERSION,
    }
    manifest["manifest_digest"] = "sha256:" + hashlib.sha256(_canonical_bytes(manifest)).hexdigest()
    return manifest


def _failure(reason: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "authority": dict(SAFE_AUTHORITY),
        "candidate": CANDIDATE,
        "outcome": NOT_READY,
        "product": PRODUCT,
        "reason": reason,
        "version": VERSION,
    }
    report["review_digest"] = _digest(report)
    return report


def review_proposed_freeze(
    manifest: Mapping[str, Any], *, rc1_verification_passed: bool, test_count: int,
    tests_passed: bool, frozen_regression_passed: bool, frozen_diff_empty: bool,
    working_tree_clean: bool, claims: Sequence[str] = (),
) -> dict[str, Any]:
    try:
        if manifest.get("qualified_rc1_head") != QUALIFIED_RC1_HEAD:
            return _failure("RC1 identity mismatch")
        if manifest.get("proposed_destination") != PROPOSED_DESTINATION:
            return _failure("proposed destination mismatch")
        digest = manifest.get("manifest_digest")
        payload = dict(manifest)
        payload.pop("manifest_digest", None)
        expected = "sha256:" + hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if not isinstance(digest, str) or digest != expected:
            return _failure("manifest digest mismatch")
        entries = manifest.get("entries")
        if not isinstance(entries, list) or manifest.get("entry_count") != len(entries):
            return _failure("manifest entries mismatch")
        paths = [entry.get("path") for entry in entries if isinstance(entry, Mapping)]
        if len(paths) != len(entries) or paths != sorted(paths) or len(set(paths)) != len(paths):
            return _failure("manifest path ordering or uniqueness failure")
        for entry in entries:
            _normalize_path(entry["path"])
            if type(entry.get("byte_count")) is not int or entry["byte_count"] < 0:
                return _failure("invalid byte count")
            if not isinstance(entry.get("sha256"), str) or SHA256_RE.fullmatch(entry["sha256"]) is None:
                return _failure("invalid file digest")
    except (KeyError, TypeError, ValueError):
        return _failure("malformed manifest")

    if rc1_verification_passed is not True or tests_passed is not True or test_count != REQUIRED_TEST_COUNT:
        return _failure("qualification evidence mismatch")
    if frozen_regression_passed is not True or frozen_diff_empty is not True or working_tree_clean is not True:
        return _failure("repository safety evidence mismatch")
    normalized_claims = tuple(str(claim).lower() for claim in claims)
    if any(prohibited in claim for claim in normalized_claims for prohibited in PROHIBITED_CLAIMS):
        return _failure("prohibited claim detected")

    report: dict[str, Any] = {
        "authority": dict(SAFE_AUTHORITY),
        "candidate": CANDIDATE,
        "claim": "Internally qualified observation-only release candidate prepared for explicit freeze approval.",
        "evidence": {
            "frozen_diff_empty": True,
            "frozen_regression_passed": True,
            "rc1_verification_passed": True,
            "test_count": REQUIRED_TEST_COUNT,
            "tests_passed": True,
            "working_tree_clean": True,
        },
        "manifest_digest": manifest["manifest_digest"],
        "outcome": READY,
        "product": PRODUCT,
        "proposed_destination": PROPOSED_DESTINATION,
        "qualified_rc1_head": QUALIFIED_RC1_HEAD,
        "version": VERSION,
    }
    report["review_digest"] = _digest(report)
    return report


def validate_review(report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(report, Mapping) or report.get("review_digest") != _digest(report):
        raise ValueError("review digest mismatch")
    return json.loads(_canonical_bytes(report).decode("utf-8"))


def serialize_review(report: Mapping[str, Any]) -> bytes:
    return _canonical_bytes(validate_review(report))
