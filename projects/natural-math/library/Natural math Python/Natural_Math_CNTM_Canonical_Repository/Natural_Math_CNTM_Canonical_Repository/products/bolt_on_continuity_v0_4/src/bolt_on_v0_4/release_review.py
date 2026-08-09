"""Deterministic, data-only release review for Bolt-On Continuity v0.4."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping, Sequence

PRODUCT = "Bolt-On Continuity v0.4"
CANDIDATE = "v0.4-rc1"
QUALIFIED_RC1_HEAD = "caede7dcec30c4e30a79f1d1721dae5402e1f95b"
RC1_QUALIFICATION_RECORD_SHA256 = "eea0b17fa192e07f35b9b35e8f4cadfff40ce1549405ae1f27b12e4151f75826"
RC1_VERIFIER_MANIFEST_SHA256 = "be9c50205cf06e81d0a2be7d13f6519c50573bcecf996876d27bec43f4e1d558"
PROPOSED_DESTINATION = "frozen/bolt_on_continuity/v0.4"
REQUIRED_TEST_COUNT = 234
READY = "PROPOSED_FREEZE_READY_FOR_APPROVAL"
NOT_READY = "FAIL_CLOSED_RELEASE_REVIEW"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PROHIBITED_CLAIMS = ("production ready", "production-ready", "zero failure", "zero drift", "universal compatibility", "autonomous remediation")

AUTHORITY = {
    "release_review_reporting": True,
    "proposed_snapshot_manifest_construction": True,
    "rc1_evidence_consumption": True,
    "frozen_tree_mutation": False,
    "release_freeze": False,
    "merge": False,
    "tag_creation": False,
    "publication": False,
    "installation": False,
    "distribution": False,
    "native_execution": False,
    "container_mutation": False,
    "filesystem_mutation": False,
    "production_readiness_claim": False,
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith(("/", "~")) or ":" in value:
        raise ValueError("UNSAFE_MANIFEST_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("UNSAFE_MANIFEST_PATH")
    return path.as_posix()


@dataclass(frozen=True)
class ReviewResult:
    body_value: Mapping[str, object]
    def body(self) -> dict[str, object]:
        return dict(self.body_value)
    def canonical_json(self) -> str:
        return canonical_bytes(self.body()).decode("utf-8")


def build_manifest(files: Mapping[str, bytes]) -> dict[str, object]:
    if not isinstance(files, Mapping) or not files:
        raise ValueError("EMPTY_MANIFEST")
    entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw_path, content in files.items():
        path = _safe_path(raw_path)
        if path in seen or not isinstance(content, bytes):
            raise ValueError("INVALID_MANIFEST_ENTRY")
        seen.add(path)
        entries.append({"path": path, "byte_count": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    entries.sort(key=lambda item: str(item["path"]))
    base = {
        "candidate": CANDIDATE,
        "entry_count": len(entries),
        "entries": entries,
        "product": PRODUCT,
        "proposed_destination": PROPOSED_DESTINATION,
        "qualified_rc1_head": QUALIFIED_RC1_HEAD,
        "rc1_qualification_record_sha256": RC1_QUALIFICATION_RECORD_SHA256,
        "rc1_verifier_manifest_sha256": RC1_VERIFIER_MANIFEST_SHA256,
    }
    return {**base, "manifest_digest": digest(base)}


def _base(outcome: str, reason: str) -> dict[str, object]:
    return {
        "accepted": outcome == READY,
        "authority": dict(AUTHORITY),
        "candidate": CANDIDATE,
        "container_mutation_authorized": False,
        "frozen_tree_mutation_authorized": False,
        "installation_authorized": False,
        "merge_authorized": False,
        "native_execution_authorized": False,
        "outcome": outcome,
        "product": PRODUCT,
        "production_readiness_claim_authorized": False,
        "publication_authorized": False,
        "reason_code": reason,
        "release_freeze_authorized": False,
        "tag_creation_authorized": False,
        "distribution_authorized": False,
    }


def _finish(body: dict[str, object]) -> ReviewResult:
    return ReviewResult({**body, "review_digest": digest(body)})


def review_release(value: object) -> ReviewResult:
    if not isinstance(value, dict):
        return _finish(_base(NOT_READY, "MALFORMED_REVIEW_INPUT"))
    required = {"source_head", "manifest", "rc1_verification_passed", "test_count", "tests_passed", "frozen_regression_passed", "frozen_diff_empty", "working_tree_clean", "claims_boundary_approved", "authority_boundary_approved", "claims"}
    if set(value) != required:
        return _finish(_base(NOT_READY, "REVIEW_FIELDS_MISMATCH"))
    manifest = value["manifest"]
    if value["source_head"] != QUALIFIED_RC1_HEAD:
        return _finish(_base(NOT_READY, "RC1_HEAD_MISMATCH"))
    if not isinstance(manifest, dict):
        return _finish(_base(NOT_READY, "MALFORMED_MANIFEST"))
    payload = dict(manifest)
    supplied = payload.pop("manifest_digest", None)
    if supplied != digest(payload):
        return _finish(_base(NOT_READY, "MANIFEST_DIGEST_MISMATCH"))
    if manifest.get("qualified_rc1_head") != QUALIFIED_RC1_HEAD or manifest.get("proposed_destination") != PROPOSED_DESTINATION:
        return _finish(_base(NOT_READY, "MANIFEST_IDENTITY_MISMATCH"))
    entries = manifest.get("entries")
    if not isinstance(entries, list) or manifest.get("entry_count") != len(entries) or not entries:
        return _finish(_base(NOT_READY, "MANIFEST_ENTRIES_MISMATCH"))
    paths: list[str] = []
    try:
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"path", "byte_count", "sha256"}:
                raise ValueError
            path = _safe_path(entry["path"])
            if type(entry["byte_count"]) is not int or entry["byte_count"] < 0 or not isinstance(entry["sha256"], str) or not SHA256.fullmatch(entry["sha256"]):
                raise ValueError
            paths.append(path)
    except (ValueError, TypeError):
        return _finish(_base(NOT_READY, "MALFORMED_MANIFEST_ENTRY"))
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        return _finish(_base(NOT_READY, "MANIFEST_PATH_CONFLICT"))
    if value["rc1_verification_passed"] is not True or value["tests_passed"] is not True or value["test_count"] != REQUIRED_TEST_COUNT:
        return _finish(_base(NOT_READY, "QUALIFICATION_EVIDENCE_MISMATCH"))
    if value["frozen_regression_passed"] is not True or value["frozen_diff_empty"] is not True or value["working_tree_clean"] is not True:
        return _finish(_base(NOT_READY, "REPOSITORY_SAFETY_EVIDENCE_MISMATCH"))
    if value["claims_boundary_approved"] is not True or value["authority_boundary_approved"] is not True:
        return _finish(_base(NOT_READY, "BOUNDARY_APPROVAL_MISSING"))
    claims = value["claims"]
    if not isinstance(claims, list) or any(not isinstance(item, str) for item in claims):
        return _finish(_base(NOT_READY, "MALFORMED_CLAIMS"))
    lowered = [item.lower() for item in claims]
    if any(term in claim for claim in lowered for term in PROHIBITED_CLAIMS):
        return _finish(_base(NOT_READY, "PROHIBITED_CLAIM_DETECTED"))
    body = _base(READY, READY)
    body.update({
        "claim": "Internally qualified observation-only release candidate prepared for explicit freeze approval.",
        "evidence": {
            "authority_boundary_approved": True,
            "claims_boundary_approved": True,
            "frozen_diff_empty": True,
            "frozen_regression_passed": True,
            "rc1_verification_passed": True,
            "test_count": REQUIRED_TEST_COUNT,
            "tests_passed": True,
            "working_tree_clean": True,
        },
        "manifest_digest": supplied,
        "proposed_destination": PROPOSED_DESTINATION,
        "qualified_rc1_head": QUALIFIED_RC1_HEAD,
    })
    return _finish(body)


def render_human(result: ReviewResult) -> str:
    body = result.body()
    return "\n".join([
        f"PASS rc1.binding: {QUALIFIED_RC1_HEAD}",
        f"PASS accepted: {'TRUE' if body['accepted'] else 'FALSE'}",
        f"PASS outcome: {body['outcome']}",
        f"PASS release.freeze.authorized: {'TRUE' if body['release_freeze_authorized'] else 'FALSE'}",
        f"PASS merge.authorized: {'TRUE' if body['merge_authorized'] else 'FALSE'}",
        f"PASS tag.creation.authorized: {'TRUE' if body['tag_creation_authorized'] else 'FALSE'}",
        f"PASS publication.authorized: {'TRUE' if body['publication_authorized'] else 'FALSE'}",
        f"PASS native.execution.authorized: {'TRUE' if body['native_execution_authorized'] else 'FALSE'}",
        str(body['reason_code']),
        f"REVIEW SHA-256 {body['review_digest']}",
    ])
