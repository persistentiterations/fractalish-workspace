from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any, Mapping

CANDIDATE = "v0.2-rc1"
QUALIFIED_SOURCE_COMMIT = "31dc5ad0740bf1b262de362f334ed64893a027c2"
REQUIRED_TEST_COUNT = 127
READY = "RC1_READY_FOR_RELEASE_REVIEW"
NOT_READY = "FAIL_CLOSED_RC1_NOT_READY"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

SAFE_AUTHORITY = {
    "container_mutation_authorized": False,
    "gateway_enabled": False,
    "merge_authorized": False,
    "native_execution_authorized": False,
    "observation_only": True,
    "production_readiness_claim_authorized": False,
    "publication_authorized": False,
    "release_freeze_authorized": False,
}

EXCLUDED_CLAIMS = (
    "production ready",
    "universal compatibility",
    "zero drift",
    "zero failure",
)


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest_without(value: Mapping[str, Any], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return "sha256:" + hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _normalize_path(path: Any) -> str:
    if not isinstance(path, str) or not path or path.strip() != path or "\\" in path or ":" in path:
        raise ValueError("invalid manifest path")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValueError("unsafe manifest path")
    return str(parsed)


def build_manifest(files: Mapping[str, bytes]) -> dict[str, Any]:
    if not isinstance(files, Mapping) or not files:
        raise ValueError("files must be a non-empty mapping")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_path, raw_bytes in files.items():
        path = _normalize_path(raw_path)
        if path in seen:
            raise ValueError("duplicate manifest path")
        seen.add(path)
        if not isinstance(raw_bytes, bytes):
            raise ValueError("manifest content must be bytes")
        entries.append({
            "byte_count": len(raw_bytes),
            "path": path,
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        })
    entries.sort(key=lambda item: item["path"])
    manifest: dict[str, Any] = {
        "candidate": CANDIDATE,
        "entries": entries,
        "entry_count": len(entries),
        "qualified_source_commit": QUALIFIED_SOURCE_COMMIT,
    }
    manifest["manifest_digest"] = _digest_without(manifest, "manifest_digest")
    return manifest


def validate_manifest(manifest: Mapping[str, Any], files: Mapping[str, bytes]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping) or set(manifest) != {
        "candidate", "entries", "entry_count", "manifest_digest", "qualified_source_commit"
    }:
        raise ValueError("manifest fields mismatch")
    expected = build_manifest(files)
    if manifest != expected:
        raise ValueError("manifest content mismatch")
    return json.loads(_canonical_bytes(manifest).decode("utf-8"))


def qualify_rc1(
    manifest: Mapping[str, Any],
    files: Mapping[str, bytes],
    *,
    test_count: int,
    tests_passed: bool,
    frozen_regression_passed: bool,
    claims: tuple[str, ...] = (),
) -> dict[str, Any]:
    reason = "qualified"
    outcome = READY
    try:
        validated = validate_manifest(manifest, files)
    except (TypeError, ValueError) as exc:
        validated = None
        outcome = NOT_READY
        reason = str(exc)

    if outcome == READY and (type(test_count) is not int or test_count != REQUIRED_TEST_COUNT or tests_passed is not True):
        outcome = NOT_READY
        reason = "test qualification mismatch"
    if outcome == READY and frozen_regression_passed is not True:
        outcome = NOT_READY
        reason = "frozen regression missing"
    if outcome == READY:
        normalized_claims = tuple(claim.strip().lower() for claim in claims if isinstance(claim, str))
        if any(excluded in normalized_claims for excluded in EXCLUDED_CLAIMS):
            outcome = NOT_READY
            reason = "prohibited claim detected"

    report: dict[str, Any] = {
        "authority": dict(SAFE_AUTHORITY),
        "candidate": CANDIDATE,
        "frozen_regression_passed": frozen_regression_passed is True,
        "manifest_digest": validated["manifest_digest"] if validated is not None else None,
        "outcome": outcome,
        "qualified_source_commit": QUALIFIED_SOURCE_COMMIT,
        "reason": reason,
        "test_count": test_count,
        "tests_passed": tests_passed is True,
    }
    report["review_digest"] = _digest_without(report, "review_digest")
    return report


def validate_review_report(report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        raise ValueError("review report must be an object")
    digest = report.get("review_digest")
    if not isinstance(digest, str) or digest != _digest_without(report, "review_digest"):
        raise ValueError("review digest mismatch")
    return json.loads(_canonical_bytes(report).decode("utf-8"))


def serialize_review_report(report: Mapping[str, Any]) -> bytes:
    return _canonical_bytes(validate_review_report(report))
