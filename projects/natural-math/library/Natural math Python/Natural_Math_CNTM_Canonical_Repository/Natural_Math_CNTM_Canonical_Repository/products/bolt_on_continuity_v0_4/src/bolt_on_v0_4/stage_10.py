"""Deterministic Stage 10 end-to-end evidence qualification."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 10
SCHEMA_VERSION = 1
QUALIFIED_STAGE_9_HEAD = "9915372ca7a63c0de60c2e65cf08765e262eff88"
STAGE_9_QUALIFICATION_RECORD_SHA256 = "da0442cf175e4b2d99f34cac7e3bd48cf2986ac0f2581cc0df2b7695cf1d9f27"
STAGE_9_VERIFIER_MANIFEST_SHA256 = "7085f2d3ee5ef9e247e013c46f13ac57c388eb38afe27a8c305f4cfea51619a6"

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
DIGEST = re.compile(r"^[0-9a-f]{64}$")

BOUNDED_CAPABILITIES = (
    "prerequisite_qualification",
    "read_only_discovery",
    "observation_only_enrollment",
    "canonical_configuration",
    "lifecycle_planning",
    "incident_review_and_replay",
    "operator_decision_recording",
    "recovery_classification",
    "installation_uninstall_planning",
)
EXCLUDED_CAPABILITIES = (
    "docker_mutation",
    "container_mutation",
    "filesystem_mutation",
    "native_execution",
    "automatic_recovery",
    "installation_execution",
    "receipt_deletion",
    "release_freeze",
    "merge",
    "tag_creation",
    "publication",
    "production_readiness_claim",
)
AUTHORITY = {
    "stage_9_evidence_consumption": True,
    "evidence_validation": True,
    "release_candidate_readiness_reporting": True,
    "docker_contact": False,
    "docker_mutation": False,
    "filesystem_mutation": False,
    "gateway_action": False,
    "service_control": False,
    "container_mutation": False,
    "native_execution": False,
    "installation_execution": False,
    "receipt_deletion": False,
    "release_freeze": False,
    "merge": False,
    "tag_creation": False,
    "publication": False,
    "production_readiness_claim": False,
}

class QualificationError(ValueError):
    """Stable fail-closed Stage 10 validation error."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class QualificationReport:
    body_value: Mapping[str, object]

    def body(self) -> dict[str, object]:
        return dict(self.body_value)

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body())

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")


def _base() -> dict[str, object]:
    return {
        "accepted": False,
        "authority": dict(AUTHORITY),
        "bounded_capabilities": list(BOUNDED_CAPABILITIES),
        "container_mutation_authorized": False,
        "evidence": [],
        "excluded_capabilities": list(EXCLUDED_CAPABILITIES),
        "frozen_regression_passed": False,
        "gateway_enabled": False,
        "merge_authorized": False,
        "native_execution_authorized": False,
        "observation_only": True,
        "product": PRODUCT,
        "production_readiness_claim_authorized": False,
        "publication_authorized": False,
        "qualified_stage_9_head": QUALIFIED_STAGE_9_HEAD,
        "readiness": "FAIL_CLOSED_NOT_READY",
        "release_candidate_preparation_authorized": False,
        "release_freeze_authorized": False,
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_9_qualification_record_sha256": STAGE_9_QUALIFICATION_RECORD_SHA256,
        "stage_9_verifier_manifest_sha256": STAGE_9_VERIFIER_MANIFEST_SHA256,
        "tag_creation_authorized": False,
    }


def qualify_evidence(value: object) -> QualificationReport:
    body = _base()
    reason = "MALFORMED_EVIDENCE_COLLECTION"
    summaries: list[dict[str, object]] = []

    if isinstance(value, list):
        seen: set[str] = set()
        valid = True
        reason = "RELEASE_CANDIDATE_READY"
        for item in value:
            if not isinstance(item, dict) or set(item) != {
                "stage", "status", "evidence_digest", "frozen_regression_passed", "authority_expanded"
            }:
                valid = False
                reason = "EVIDENCE_FIELDS_MISMATCH"
                break
            stage = item["stage"]
            if stage not in REQUIRED_STAGES:
                valid = False
                reason = "UNKNOWN_STAGE_EVIDENCE"
                break
            if stage in seen:
                valid = False
                reason = "DUPLICATE_STAGE_EVIDENCE"
                break
            seen.add(stage)
            if item["status"] != "PASS":
                valid = False
                reason = "STAGE_EVIDENCE_NOT_PASSING"
                break
            digest = item["evidence_digest"]
            if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
                valid = False
                reason = "INVALID_EVIDENCE_DIGEST"
                break
            if item["frozen_regression_passed"] is not True:
                valid = False
                reason = "FROZEN_REGRESSION_NOT_PROVEN"
                break
            if item["authority_expanded"] is not False:
                valid = False
                reason = "AUTHORITY_EXPANSION_DETECTED"
                break
            summaries.append({
                "authority_expanded": False,
                "evidence_digest": digest,
                "frozen_regression_passed": True,
                "stage": stage,
                "status": "PASS",
            })

        if valid and seen != set(REQUIRED_STAGES):
            valid = False
            reason = "MISSING_STAGE_EVIDENCE"

        if valid:
            summaries.sort(key=lambda item: REQUIRED_STAGES.index(str(item["stage"])))
            body.update({
                "accepted": True,
                "evidence": summaries,
                "frozen_regression_passed": True,
                "readiness": "RELEASE_CANDIDATE_READY",
                "release_candidate_preparation_authorized": True,
            })
        else:
            body["evidence"] = summaries
    body["reason_code"] = reason
    digest_base = dict(body)
    body["report_digest"] = sha256(canonical_bytes(digest_base))
    return QualificationReport(body)


def render_human(report: QualificationReport) -> str:
    body = report.body()
    return "\n".join([
        f"PASS stage9.binding: {body['qualified_stage_9_head']}",
        f"PASS accepted: {'TRUE' if body['accepted'] else 'FALSE'}",
        f"PASS readiness: {body['readiness']}",
        f"PASS evidence.count: {len(body['evidence'])}",
        f"PASS frozen.regression: {'TRUE' if body['frozen_regression_passed'] else 'FALSE'}",
        "PASS native.execution.authorized: FALSE",
        "PASS container.mutation.authorized: FALSE",
        "PASS release.freeze.authorized: FALSE",
        "PASS merge.authorized: FALSE",
        "PASS publication.authorized: FALSE",
        body["reason_code"],
        f"REPORT SHA-256 {body['report_digest']}",
    ])
