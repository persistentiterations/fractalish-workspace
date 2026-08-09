"""Deterministic release-candidate preparation for Bolt-On Continuity v0.4."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

PRODUCT = "Bolt-On Continuity v0.4"
RELEASE_CANDIDATE = "RC1"
QUALIFIED_STAGE_10_HEAD = "6e3843eed394cad1bc3ed00b4d148cdcaa2fbba9"

QUALIFIED_CHAIN = (
    (0, "fbe8043e56285446a4b07ef4cdf011e08b9ea772813fc20a37f8118f743e9f69", "650c4e222f6554bd6c67188478a464f92dd884ea3e1949a7b7b27311997c7279"),
    (1, "9fcd999f9d1e3817f53a60ff9b61193ec0576d808b14bdbbb7d806e86a83da2b", "d94edb9ada5857f56d2785ae81dcf58768791fda46e7c1fc6e13c74ac57eaf18"),
    (2, "97b92c58c6bf342c44dd793bfe0a78401b9c606ecaccd27ca1f9c48cd2d6141e", "6f1c6c119c8114ed20e84c6d28dc1e9de9000e6df861939e5775373e4d957192"),
    (3, "1715c97822c5639b4850a46f28f5620b09c19a981e1b32e93ecb4f9bbc741bf0", "f68cee14b5c47572e84b839cd2b2917f7c2c3f706bc87a7f83c0937b5e5fdbc9"),
    (4, "8ac44c29c207f6bf047f5291abc16b99394d1bfc139a15e57c35d0a37e2cebe9", "3628499eacbb59d457ccfd8333adb0ebcbfa4b0542891d4a26b24fdc2079ef8f"),
    (5, "6b1deab138bd52643ed797fc1195cf5d8a5fbcc2ea8a72c95ec871847f0e3ffc", "58ec59fdb6aa87ed934cea48581c7cdb3c790c39b7f980e10444aaff007e5e2f"),
    (6, "cd45ee04b1f872f6a98cbc2c52995ebdfcf4eb64feb9a1a6bb912072ef78af7d", "6a6df9fcae5fbcd8ea3987c8bdeed5ae959cef631820de3d4fdc0b2a653dd6bc"),
    (7, "cb8705634db07520a3bb2063cb0c1e34860e425486bc9b7043bb94eb889ea658", "4b2b9bddf658e53fa8488d29eb621adbf278d402dc8261b4b2072d5364db05d1"),
    (8, "b8c371184857f2c5d5d024562caca9e9195d16ca82115c467a774762ecb467b8", "09949caf33f16bbae695612fc4bd086f28d973a4277933f8f523c322e9bea6c0"),
    (9, "da0442cf175e4b2d99f34cac7e3bd48cf2986ac0f2581cc0df2b7695cf1d9f27", "7085f2d3ee5ef9e247e013c46f13ac57c388eb38afe27a8c305f4cfea51619a6"),
    (10, "39cdb080b6710b147e369e4b28b2414c04d7f8a34acf1cf1f7c1538b4bfbe943", "f22e0dd0931982ebd38f346bee0a4326d5ce2cc1f85b3d6a01d5c16e949df46b"),
)

AUTHORITY = {
    "qualified_chain_consumption": True,
    "rc_manifest_construction": True,
    "release_review_reporting": True,
    "frozen_tree_mutation": False,
    "merge": False,
    "tag_creation": False,
    "publication": False,
    "installation": False,
    "distribution": False,
    "native_execution": False,
    "docker_contact": False,
    "docker_mutation": False,
    "container_mutation": False,
    "filesystem_mutation": False,
    "production_readiness_claim": False,
}

CAPABILITIES = (
    "prerequisite_qualification",
    "read_only_discovery",
    "observation_only_enrollment",
    "canonical_configuration",
    "lifecycle_planning",
    "incident_review_and_replay",
    "operator_decision_recording",
    "recovery_classification",
    "installation_uninstall_planning",
    "release_candidate_readiness_reporting",
)

class RC1Error(ValueError):
    """Stable fail-closed RC1 validation error."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class RC1Report:
    value: Mapping[str, object]

    def body(self) -> dict[str, object]:
        return dict(self.value)

    def canonical_json(self) -> str:
        return canonical_bytes(self.body()).decode("utf-8")


def qualified_evidence() -> list[dict[str, object]]:
    return [
        {
            "authority_expanded": False,
            "qualification_record_sha256": record,
            "stage": stage,
            "verifier_manifest_sha256": manifest,
        }
        for stage, record, manifest in QUALIFIED_CHAIN
    ]


def prepare_rc1(evidence: object, source_head: object) -> RC1Report:
    accepted = True
    reason = "RC1_REVIEW_READY"
    if source_head != QUALIFIED_STAGE_10_HEAD:
        accepted, reason = False, "SOURCE_HEAD_MISMATCH"
    if not isinstance(evidence, list):
        accepted, reason = False, "MALFORMED_EVIDENCE"
        evidence = []

    expected = qualified_evidence()
    normalized: list[dict[str, object]] = []
    if accepted:
        if len(evidence) != len(expected):
            accepted, reason = False, "INCOMPLETE_EVIDENCE_CHAIN"
        else:
            for index, item in enumerate(evidence):
                if not isinstance(item, dict) or set(item) != set(expected[index]):
                    accepted, reason = False, "MALFORMED_EVIDENCE"
                    break
                normalized.append(dict(item))
                if item != expected[index]:
                    if item.get("authority_expanded") is True:
                        reason = "AUTHORITY_EXPANSION_DETECTED"
                    else:
                        reason = "EVIDENCE_CHAIN_MISMATCH"
                    accepted = False
                    break

    body: dict[str, object] = {
        "accepted": accepted,
        "authority": dict(AUTHORITY),
        "bounded_capabilities": list(CAPABILITIES),
        "container_mutation_authorized": False,
        "distribution_authorized": False,
        "evidence": normalized if normalized else [],
        "evidence_count": len(normalized),
        "frozen_tree_mutation_authorized": False,
        "installation_authorized": False,
        "merge_authorized": False,
        "native_execution_authorized": False,
        "product": PRODUCT,
        "production_readiness_claim_authorized": False,
        "publication_authorized": False,
        "reason_code": reason,
        "release_candidate": RELEASE_CANDIDATE,
        "release_review_authorized": accepted,
        "release_freeze_authorized": False,
        "schema_version": 1,
        "source_head": source_head,
        "tag_creation_authorized": False,
    }
    manifest_base = {
        "evidence": body["evidence"],
        "product": PRODUCT,
        "release_candidate": RELEASE_CANDIDATE,
        "source_head": source_head,
    }
    body["rc_manifest_digest"] = sha256(canonical_bytes(manifest_base))
    body["report_digest"] = sha256(canonical_bytes(body))
    return RC1Report(body)


def render_human(report: RC1Report) -> str:
    body = report.body()
    return "\n".join([
        f"PASS stage10.binding: {body['source_head']}",
        f"PASS accepted: {'TRUE' if body['accepted'] else 'FALSE'}",
        f"PASS outcome: {body['reason_code']}",
        f"PASS evidence.count: {body['evidence_count']}",
        f"PASS release.review.authorized: {'TRUE' if body['release_review_authorized'] else 'FALSE'}",
        "PASS release.freeze.authorized: FALSE",
        "PASS merge.authorized: FALSE",
        "PASS tag.creation.authorized: FALSE",
        "PASS publication.authorized: FALSE",
        "PASS native.execution.authorized: FALSE",
        str(body["reason_code"]),
        f"RC MANIFEST SHA-256 {body['rc_manifest_digest']}",
        f"REPORT SHA-256 {body['report_digest']}",
    ])
