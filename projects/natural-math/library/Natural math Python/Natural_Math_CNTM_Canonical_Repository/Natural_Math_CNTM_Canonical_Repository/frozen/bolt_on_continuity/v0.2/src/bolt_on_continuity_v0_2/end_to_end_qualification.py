from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

PRODUCT = "Bolt-On Continuity for Docker"
PRODUCT_VERSION = "0.2"
SCHEMA_VERSION = "1"
READY = "RELEASE_CANDIDATE_READY"
NOT_READY = "FAIL_CLOSED_NOT_READY"
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_STAGES = (
    "stage_1_scaffold",
    "stage_2_prerequisites",
    "stage_3_enrollment",
    "stage_4_configuration",
    "stage_5_cli",
    "stage_6_incident_review",
    "stage_7_operator_control",
    "stage_8_recovery",
    "stage_9_installation_lifecycle",
)

QUALIFIED_CAPABILITIES = (
    "prerequisite checking",
    "exact container enrollment",
    "canonical configuration validation",
    "observation-only lifecycle planning",
    "incident listing and explanation",
    "offline replay and deterministic export",
    "operator-controlled approval and denial records",
    "restart and failure recovery classification",
    "installation and uninstall planning",
)

EXCLUDED_CAPABILITIES = (
    "real installation",
    "service registration",
    "daemon execution",
    "gateway execution",
    "Docker mutation",
    "release freeze",
    "merge to main",
    "artifact publication",
    "production-readiness claims",
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
}


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _report_digest(report: Mapping[str, Any]) -> str:
    payload = dict(report)
    payload.pop("report_digest", None)
    return "sha256:" + hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _failure(reason: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "authority": dict(SAFE_AUTHORITY),
        "outcome": NOT_READY,
        "product": PRODUCT,
        "product_version": PRODUCT_VERSION,
        "reason": reason,
        "schema_version": SCHEMA_VERSION,
    }
    report["report_digest"] = _report_digest(report)
    return report


def qualify_release_candidate(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        return _failure("evidence must be an object")
    if set(evidence) != set(REQUIRED_STAGES):
        return _failure("stage evidence set mismatch")

    ordered: list[dict[str, Any]] = []
    seen_digests: set[str] = set()
    for stage in REQUIRED_STAGES:
        item = evidence[stage]
        if not isinstance(item, Mapping):
            return _failure(f"malformed evidence: {stage}")
        if set(item) != {"stage", "status", "evidence_digest", "frozen_regression_passed", "authority_expanded"}:
            return _failure(f"evidence fields mismatch: {stage}")
        if item["stage"] != stage:
            return _failure(f"stage identity mismatch: {stage}")
        digest = item["evidence_digest"]
        if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
            return _failure(f"invalid evidence digest: {stage}")
        if digest in seen_digests:
            return _failure("duplicate evidence digest")
        seen_digests.add(digest)
        if item["status"] != "PASS":
            return _failure(f"stage did not pass: {stage}")
        if item["frozen_regression_passed"] is not True:
            return _failure(f"frozen regression missing: {stage}")
        if item["authority_expanded"] is not False:
            return _failure(f"authority expansion detected: {stage}")
        ordered.append({
            "authority_expanded": False,
            "evidence_digest": digest,
            "frozen_regression_passed": True,
            "stage": stage,
            "status": "PASS",
        })

    report: dict[str, Any] = {
        "authority": dict(SAFE_AUTHORITY),
        "excluded_capabilities": list(EXCLUDED_CAPABILITIES),
        "frozen_regression_passed": True,
        "outcome": READY,
        "product": PRODUCT,
        "product_version": PRODUCT_VERSION,
        "qualified_capabilities": list(QUALIFIED_CAPABILITIES),
        "schema_version": SCHEMA_VERSION,
        "stage_evidence": ordered,
    }
    report["report_digest"] = _report_digest(report)
    return report


def validate_qualification_report(report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        raise ValueError("report must be an object")
    digest = report.get("report_digest")
    if not isinstance(digest, str) or digest != _report_digest(report):
        raise ValueError("report digest mismatch")
    return json.loads(_canonical_bytes(report).decode("utf-8"))


def serialize_qualification_report(report: Mapping[str, Any]) -> bytes:
    return _canonical_bytes(validate_qualification_report(report))
