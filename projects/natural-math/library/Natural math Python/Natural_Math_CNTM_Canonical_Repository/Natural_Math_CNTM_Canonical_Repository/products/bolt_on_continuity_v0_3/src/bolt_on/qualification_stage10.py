"""Deterministic Stage 10 release-candidate evidence aggregation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping

from .receipts import canonical_json_bytes
from .version import __version__

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


class QualificationError(ValueError):
    """Stable fail-closed Stage 10 error."""


@dataclass(frozen=True)
class QualificationReport:
    body: Mapping[str, object]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")


def _validate_evidence(stage: str, value: object) -> dict[str, object]:
    required = {"stage", "status", "evidence_digest", "frozen_regression_passed", "authority_expanded"}
    if not isinstance(value, dict) or set(value) != required:
        raise QualificationError("MALFORMED_STAGE_EVIDENCE")
    if value["stage"] != stage or value["status"] != "PASS":
        raise QualificationError("FAILED_OR_CONFLICTING_STAGE_EVIDENCE")
    if not isinstance(value["evidence_digest"], str) or not DIGEST.fullmatch(value["evidence_digest"]):
        raise QualificationError("INVALID_EVIDENCE_DIGEST")
    if value["frozen_regression_passed"] is not True:
        raise QualificationError("FROZEN_REGRESSION_NOT_PROVEN")
    if value["authority_expanded"] is not False:
        raise QualificationError("AUTHORITY_EXPANSION_DETECTED")
    return {
        "authority_expanded": False,
        "evidence_digest": value["evidence_digest"],
        "frozen_regression_passed": True,
        "stage": stage,
        "status": "PASS",
    }


def qualify(evidence: Mapping[str, object]) -> QualificationReport:
    if not isinstance(evidence, Mapping) or set(evidence) != set(REQUIRED_STAGES):
        raise QualificationError("STAGE_EVIDENCE_SET_MISMATCH")
    ordered = [_validate_evidence(stage, evidence[stage]) for stage in REQUIRED_STAGES]
    base: dict[str, object] = {
        "authority_boundary_intact": True,
        "capabilities": [
            "environment_diagnosis",
            "bounded_prerequisite_probe",
            "exact_subject_enrollment",
            "canonical_configuration",
            "observation_lifecycle_planning",
            "offline_incident_review",
            "operator_approval_boundary",
            "restart_recovery_classification",
            "installation_lifecycle_planning",
        ],
        "excluded_capabilities": [
            "docker_mutation",
            "gateway_execution",
            "native_service_execution",
            "filesystem_installation",
            "release_freeze",
            "merge",
            "publication",
            "production_readiness_claim",
        ],
        "frozen_regression_passed": True,
        "product": "bolt-on-continuity-for-docker",
        "product_version": __version__,
        "readiness": "RELEASE_CANDIDATE_READY",
        "safety": {
            "container_mutation_authorized": False,
            "gateway_enabled": False,
            "merge_authorized": False,
            "native_execution_authorized": False,
            "observation_only": True,
            "production_readiness_claim_authorized": False,
            "publication_authorized": False,
            "release_freeze_authorized": False,
        },
        "schema_version": 1,
        "stage_evidence": ordered,
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    return QualificationReport({**base, "report_digest": digest})
