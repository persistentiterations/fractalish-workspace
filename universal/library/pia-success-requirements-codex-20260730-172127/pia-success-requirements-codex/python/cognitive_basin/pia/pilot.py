"""
Bounded PIA success-requirements pilot.

This module implements a reviewer-safe pilot surface for the PIA checklist:

- governed formation of contradiction history;
- non-directive formed-history objects;
- condition-blind state access;
- cryptographic formation authenticity;
- blinded final fixtures;
- typed route distributions;
- Host A -> Host B continuity import;
- model-host substitution records;
- one guarded execution surface whose receipts are independently validated.

The deterministic host included here is a harness for automated tests.  Live
model-host use is represented by the optional Grok CLI adapter and by receipt
metadata, but production model-host portability remains outside this pilot.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Protocol, Sequence


FORMED_HISTORY_SCHEMA = "fractalish.pia.formed-history.v0.1"
CONTINUITY_BUNDLE_SCHEMA = "fractalish.pia.continuity-bundle.v0.1"
ROUTE_DISTRIBUTION_SCHEMA = "fractalish.pia.route-distribution.v0.1"
RUN_RECEIPT_SCHEMA = "fractalish.pia.guarded-run-receipt.v0.1"
FORMATION_POLICY_ID = "pia.contradiction-history-formation.v0.1"
ACCESS_CONTROLLER_VERSION = "pia.condition-blind-state-access.v0.1"
GUARD_POLICY_ID = "pia.guarded-execution.v0.1"

DEFAULT_ROUTE_VOCABULARY = (
    "preserve_and_review",
    "release_with_caveat",
    "hold_for_authority",
)

DEFAULT_ROUTE_PATHS = {
    "preserve_and_review": "routes/preserve-and-review",
    "release_with_caveat": "routes/release-with-caveat",
    "hold_for_authority": "routes/hold-for-authority",
}

FORBIDDEN_DIRECTIVE_KEYS = {
    "action",
    "answer",
    "condition_id",
    "decision_gate",
    "expected_analysis",
    "expected_outcome",
    "expected_route",
    "experiment_arm",
    "fixture_outcome",
    "route_hint",
    "selected_path",
    "selected_route",
    "target_answer",
}


class PIAValidationError(ValueError):
    """Raised when a PIA pilot object cannot be accepted as evidence."""


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def digest_payload(payload: Mapping[str, Any] | Sequence[Any] | str) -> str:
    if isinstance(payload, str):
        encoded = payload.encode("utf-8")
    else:
        encoded = canonical_json({"payload": payload}).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _bare_digest(payload: Mapping[str, Any] | Sequence[Any] | str) -> str:
    return digest_payload(payload).split(":", 1)[1]


def _assert_no_forbidden_directives(payload: Any, *, path: str = "$") -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            if key_text in FORBIDDEN_DIRECTIVE_KEYS:
                raise PIAValidationError(f"directive field is not allowed in formed/access state: {path}.{key_text}")
            _assert_no_forbidden_directives(value, path=f"{path}.{key_text}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _assert_no_forbidden_directives(value, path=f"{path}[{index}]")
    elif isinstance(payload, str):
        normalized = payload.lower()
        for forbidden in FORBIDDEN_DIRECTIVE_KEYS:
            token = forbidden.lower()
            if token in normalized or token.replace("_", " ") in normalized:
                raise PIAValidationError(f"directive value marker is not allowed in formed/access state: {path}")


@dataclass(frozen=True)
class FormationAuthority:
    """Formation signer for pilot objects.

    HMAC is used here to keep the pilot deterministic and dependency-free.  The
    key identifier is public; the secret is test/local configuration.  Hardware
    key custody, key rotation, and compromise recovery are explicitly outside
    this pilot.
    """

    key_id: str
    secret: str

    def sign(self, payload: Mapping[str, Any]) -> str:
        message = canonical_json(payload).encode("utf-8")
        return "hmac-sha256:" + hmac.new(self.secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def verify(self, payload: Mapping[str, Any], signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)


@dataclass(frozen=True)
class ContradictionObservation:
    observation_id: str
    claim_key: str
    asserted_value: str
    statement: str
    evidence_ref: str
    sequence: int
    provenance: str
    scope: str

    def to_record(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "claim_key": self.claim_key,
            "asserted_value": self.asserted_value,
            "statement": self.statement,
            "evidence_ref": self.evidence_ref,
            "sequence": self.sequence,
            "provenance": self.provenance,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class FormedHistoryObject:
    history_id: str
    claim_key: str
    conflicting_observations: List[Dict[str, Any]]
    resolution_status: str
    confidence: float
    provenance_refs: List[str]
    scope: str
    eligibility: str
    created_sequence: int
    formation_policy_id: str
    content_digest: str
    lineage_digest: str
    authority_key_id: str
    formation_signature: str
    schema_version: str = FORMED_HISTORY_SCHEMA

    def unsigned_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "history_id": self.history_id,
            "claim_key": self.claim_key,
            "conflicting_observations": list(self.conflicting_observations),
            "resolution_status": self.resolution_status,
            "confidence": self.confidence,
            "provenance_refs": list(self.provenance_refs),
            "scope": self.scope,
            "eligibility": self.eligibility,
            "created_sequence": self.created_sequence,
            "formation_policy_id": self.formation_policy_id,
        }

    def authenticity_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "formation_policy_id": self.formation_policy_id,
            "scope": self.scope,
            "content_digest": self.content_digest,
            "lineage_digest": self.lineage_digest,
            "authority_key_id": self.authority_key_id,
        }

    def to_record(self) -> Dict[str, Any]:
        return {
            **self.unsigned_payload(),
            "content_digest": self.content_digest,
            "lineage_digest": self.lineage_digest,
            "authority_key_id": self.authority_key_id,
            "formation_signature": self.formation_signature,
        }


class FormationService:
    def __init__(self, authority: FormationAuthority, *, formation_policy_id: str = FORMATION_POLICY_ID) -> None:
        self.authority = authority
        self.formation_policy_id = formation_policy_id

    def form_contradiction_history(
        self,
        observations: Iterable[ContradictionObservation],
        *,
        scope: str,
        resolution_status: str = "unresolved",
        confidence: float = 0.5,
        created_sequence: int = 1,
    ) -> FormedHistoryObject:
        ordered = sorted(list(observations), key=lambda item: (item.sequence, item.observation_id))
        if len(ordered) < 2:
            raise PIAValidationError("contradiction formation requires at least two observations")
        claim_keys = {item.claim_key for item in ordered}
        if len(claim_keys) != 1:
            raise PIAValidationError("contradiction formation requires one claim_key")
        asserted_values = {item.asserted_value for item in ordered}
        if len(asserted_values) < 2:
            raise PIAValidationError("contradiction formation requires conflicting asserted values")
        if any(not item.evidence_ref for item in ordered):
            raise PIAValidationError("contradiction formation requires evidence_ref for every observation")
        observation_records = [item.to_record() for item in ordered]
        _assert_no_forbidden_directives(observation_records)

        claim_key = ordered[0].claim_key
        history_id = f"pia-history-{_bare_digest({'claim_key': claim_key, 'observations': observation_records})[:16]}"
        provenance_refs = [item.evidence_ref for item in ordered]
        unsigned = {
            "schema_version": FORMED_HISTORY_SCHEMA,
            "history_id": history_id,
            "claim_key": claim_key,
            "conflicting_observations": observation_records,
            "resolution_status": resolution_status,
            "confidence": confidence,
            "provenance_refs": provenance_refs,
            "scope": scope,
            "eligibility": "eligible",
            "created_sequence": created_sequence,
            "formation_policy_id": self.formation_policy_id,
        }
        content_digest = digest_payload(unsigned)
        lineage_digest = digest_payload(
            {
                "formation_policy_id": self.formation_policy_id,
                "observations": observation_records,
                "scope": scope,
            }
        )
        authenticity = {
            "schema_version": FORMED_HISTORY_SCHEMA,
            "formation_policy_id": self.formation_policy_id,
            "scope": scope,
            "content_digest": content_digest,
            "lineage_digest": lineage_digest,
            "authority_key_id": self.authority.key_id,
        }
        return FormedHistoryObject(
            history_id=history_id,
            claim_key=claim_key,
            conflicting_observations=observation_records,
            resolution_status=resolution_status,
            confidence=confidence,
            provenance_refs=provenance_refs,
            scope=scope,
            eligibility="eligible",
            created_sequence=created_sequence,
            formation_policy_id=self.formation_policy_id,
            content_digest=content_digest,
            lineage_digest=lineage_digest,
            authority_key_id=self.authority.key_id,
            formation_signature=self.authority.sign(authenticity),
        )


def _formed_history_from_record(record: Mapping[str, Any]) -> FormedHistoryObject:
    return FormedHistoryObject(
        schema_version=str(record["schema_version"]),
        history_id=str(record["history_id"]),
        claim_key=str(record["claim_key"]),
        conflicting_observations=[dict(item) for item in record["conflicting_observations"]],
        resolution_status=str(record["resolution_status"]),
        confidence=float(record["confidence"]),
        provenance_refs=list(record["provenance_refs"]),
        scope=str(record["scope"]),
        eligibility=str(record["eligibility"]),
        created_sequence=int(record["created_sequence"]),
        formation_policy_id=str(record["formation_policy_id"]),
        content_digest=str(record["content_digest"]),
        lineage_digest=str(record["lineage_digest"]),
        authority_key_id=str(record["authority_key_id"]),
        formation_signature=str(record["formation_signature"]),
    )


def validate_formed_history(record: Mapping[str, Any], authority: FormationAuthority) -> FormedHistoryObject:
    _assert_no_forbidden_directives(record)
    required = {
        "schema_version",
        "history_id",
        "claim_key",
        "conflicting_observations",
        "resolution_status",
        "confidence",
        "provenance_refs",
        "scope",
        "eligibility",
        "created_sequence",
        "formation_policy_id",
        "content_digest",
        "lineage_digest",
        "authority_key_id",
        "formation_signature",
    }
    missing = required.difference(record)
    if missing:
        raise PIAValidationError(f"formed history missing fields: {sorted(missing)}")
    formed = _formed_history_from_record(record)
    if formed.schema_version != FORMED_HISTORY_SCHEMA:
        raise PIAValidationError("unsupported formed-history schema")
    if formed.authority_key_id != authority.key_id:
        raise PIAValidationError("formed-history authority key mismatch")
    if digest_payload(formed.unsigned_payload()) != formed.content_digest:
        raise PIAValidationError("formed-history content digest mismatch")
    if (
        digest_payload(
            {
                "formation_policy_id": formed.formation_policy_id,
                "observations": formed.conflicting_observations,
                "scope": formed.scope,
            }
        )
        != formed.lineage_digest
    ):
        raise PIAValidationError("formed-history lineage digest mismatch")
    values = {str(item.get("asserted_value", "")) for item in formed.conflicting_observations}
    if len(values) < 2:
        raise PIAValidationError("formed history does not contain conflicting observations")
    if any(not item.get("evidence_ref") for item in formed.conflicting_observations):
        raise PIAValidationError("formed history contains observation without evidence_ref")
    if not authority.verify(formed.authenticity_payload(), formed.formation_signature):
        raise PIAValidationError("formed-history signature mismatch")
    return formed


@dataclass(frozen=True)
class AccessDecision:
    controller_version: str
    controller_config_digest: str
    purpose: str
    scope: str
    selected_history_ids: List[str]
    selected_content_digests: List[str]
    decision_reasons: List[str]

    def to_record(self) -> Dict[str, Any]:
        return {
            "controller_version": self.controller_version,
            "controller_config_digest": self.controller_config_digest,
            "purpose": self.purpose,
            "scope": self.scope,
            "selected_history_ids": list(self.selected_history_ids),
            "selected_content_digests": list(self.selected_content_digests),
            "decision_reasons": list(self.decision_reasons),
        }


@dataclass(frozen=True)
class ConditionBlindStateAccessController:
    authority: FormationAuthority
    controller_version: str = ACCESS_CONTROLLER_VERSION
    allowed_scopes: tuple[str, ...] = ("pilot",)
    allowed_formation_policies: tuple[str, ...] = (FORMATION_POLICY_ID,)
    allowed_resolution_statuses: tuple[str, ...] = ("unresolved", "resolved", "superseded")
    allowed_provenance_prefixes: tuple[str, ...] = ("evidence:",)
    require_eligible: bool = True

    def configuration_digest(self) -> str:
        return digest_payload(
            {
                "controller_version": self.controller_version,
                "allowed_scopes": list(self.allowed_scopes),
                "allowed_formation_policies": list(self.allowed_formation_policies),
                "allowed_resolution_statuses": list(self.allowed_resolution_statuses),
                "allowed_provenance_prefixes": list(self.allowed_provenance_prefixes),
                "require_eligible": self.require_eligible,
                "forbidden_directive_keys": sorted(FORBIDDEN_DIRECTIVE_KEYS),
            }
        )

    def select(
        self,
        history_records: Iterable[Mapping[str, Any]],
        *,
        purpose: str,
        scope: str,
        limit: int = 5,
    ) -> AccessDecision:
        if scope not in self.allowed_scopes:
            raise PIAValidationError("state-access scope is not allowed by controller configuration")
        selected: List[FormedHistoryObject] = []
        reasons: List[str] = []
        for record in history_records:
            formed = validate_formed_history(record, self.authority)
            if formed.scope != scope:
                reasons.append(f"{formed.history_id}: scope mismatch")
                continue
            if self.require_eligible and formed.eligibility != "eligible":
                reasons.append(f"{formed.history_id}: ineligible")
                continue
            if formed.formation_policy_id not in self.allowed_formation_policies:
                reasons.append(f"{formed.history_id}: formation policy rejected")
                continue
            if formed.resolution_status not in self.allowed_resolution_statuses:
                reasons.append(f"{formed.history_id}: resolution status rejected")
                continue
            if not formed.provenance_refs or not all(
                any(ref.startswith(prefix) for prefix in self.allowed_provenance_prefixes)
                for ref in formed.provenance_refs
            ):
                reasons.append(f"{formed.history_id}: provenance rejected")
                continue
            selected.append(formed)
            reasons.append(f"{formed.history_id}: valid formed history exposed for {purpose}")
        selected.sort(key=lambda item: (item.created_sequence, item.history_id), reverse=True)
        selected = selected[:limit]
        return AccessDecision(
            controller_version=self.controller_version,
            controller_config_digest=self.configuration_digest(),
            purpose=purpose,
            scope=scope,
            selected_history_ids=[item.history_id for item in selected],
            selected_content_digests=[item.content_digest for item in selected],
            decision_reasons=reasons,
        )


@dataclass(frozen=True)
class ContinuityBundle:
    bundle_id: str
    source_host_id: str
    source_model_id: str
    destination_scope: str
    formed_history: Dict[str, Any]
    source_state_receipt: Dict[str, Any]
    export_sequence: int
    export_digest: str
    authority_key_id: str
    export_signature: str
    schema_version: str = CONTINUITY_BUNDLE_SCHEMA

    def unsigned_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "source_host_id": self.source_host_id,
            "source_model_id": self.source_model_id,
            "destination_scope": self.destination_scope,
            "formed_history": dict(self.formed_history),
            "source_state_receipt": dict(self.source_state_receipt),
            "export_sequence": self.export_sequence,
        }

    def authenticity_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "source_host_id": self.source_host_id,
            "source_model_id": self.source_model_id,
            "destination_scope": self.destination_scope,
            "export_digest": self.export_digest,
            "authority_key_id": self.authority_key_id,
        }

    def to_record(self) -> Dict[str, Any]:
        return {
            **self.unsigned_payload(),
            "export_digest": self.export_digest,
            "authority_key_id": self.authority_key_id,
            "export_signature": self.export_signature,
        }

    @classmethod
    def export(
        cls,
        formed_history: FormedHistoryObject,
        *,
        authority: FormationAuthority,
        source_host_id: str,
        source_model_id: str,
        source_state_receipt: Mapping[str, Any],
        destination_scope: str,
        export_sequence: int = 1,
    ) -> "ContinuityBundle":
        formed_record = formed_history.to_record()
        validated_source_state_receipt = validate_host_state_receipt(
            source_state_receipt,
            authority,
            expected_host_id=source_host_id,
            expected_model_id=source_model_id,
            expected_content_digest=formed_history.content_digest,
        )
        bundle_id = f"pia-bundle-{_bare_digest({'source_host_id': source_host_id, 'history': formed_record})[:16]}"
        unsigned = {
            "schema_version": CONTINUITY_BUNDLE_SCHEMA,
            "bundle_id": bundle_id,
            "source_host_id": source_host_id,
            "source_model_id": source_model_id,
            "destination_scope": destination_scope,
            "formed_history": formed_record,
            "source_state_receipt": validated_source_state_receipt,
            "export_sequence": export_sequence,
        }
        export_digest = digest_payload(unsigned)
        authenticity = {
            "schema_version": CONTINUITY_BUNDLE_SCHEMA,
            "bundle_id": bundle_id,
            "source_host_id": source_host_id,
            "source_model_id": source_model_id,
            "destination_scope": destination_scope,
            "export_digest": export_digest,
            "authority_key_id": authority.key_id,
        }
        return cls(
            bundle_id=bundle_id,
            source_host_id=source_host_id,
            source_model_id=source_model_id,
            destination_scope=destination_scope,
            formed_history=formed_record,
            source_state_receipt=validated_source_state_receipt,
            export_sequence=export_sequence,
            export_digest=export_digest,
            authority_key_id=authority.key_id,
            export_signature=authority.sign(authenticity),
        )


def verify_continuity_bundle(record: Mapping[str, Any], authority: FormationAuthority) -> ContinuityBundle:
    required = {
        "schema_version",
        "bundle_id",
        "source_host_id",
        "source_model_id",
        "destination_scope",
        "formed_history",
        "source_state_receipt",
        "export_sequence",
        "export_digest",
        "authority_key_id",
        "export_signature",
    }
    missing = required.difference(record)
    if missing:
        raise PIAValidationError(f"continuity bundle missing fields: {sorted(missing)}")
    bundle = ContinuityBundle(
        schema_version=str(record["schema_version"]),
        bundle_id=str(record["bundle_id"]),
        source_host_id=str(record["source_host_id"]),
        source_model_id=str(record["source_model_id"]),
        destination_scope=str(record["destination_scope"]),
        formed_history=dict(record["formed_history"]),
        source_state_receipt=dict(record["source_state_receipt"]),
        export_sequence=int(record["export_sequence"]),
        export_digest=str(record["export_digest"]),
        authority_key_id=str(record["authority_key_id"]),
        export_signature=str(record["export_signature"]),
    )
    if bundle.schema_version != CONTINUITY_BUNDLE_SCHEMA:
        raise PIAValidationError("unsupported continuity-bundle schema")
    if bundle.authority_key_id != authority.key_id:
        raise PIAValidationError("continuity-bundle authority key mismatch")
    formed = validate_formed_history(bundle.formed_history, authority)
    validate_host_state_receipt(
        bundle.source_state_receipt,
        authority,
        expected_host_id=bundle.source_host_id,
        expected_model_id=bundle.source_model_id,
        expected_content_digest=formed.content_digest,
    )
    if digest_payload(bundle.unsigned_payload()) != bundle.export_digest:
        raise PIAValidationError("continuity-bundle digest mismatch")
    if not authority.verify(bundle.authenticity_payload(), bundle.export_signature):
        raise PIAValidationError("continuity-bundle signature mismatch")
    return bundle


@dataclass
class HostStateStore:
    host_id: str
    model_id: str
    namespace: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    import_receipts: List[Dict[str, Any]] = field(default_factory=list)

    def store_formed_history(self, formed_history: FormedHistoryObject, *, authority: FormationAuthority) -> Dict[str, Any]:
        self.namespace[formed_history.content_digest] = formed_history.to_record()
        unsigned = {
            "schema_version": "fractalish.pia.host-state-receipt.v0.1",
            "host_id": self.host_id,
            "model_id": self.model_id,
            "stored_content_digest": formed_history.content_digest,
            "history_id": formed_history.history_id,
            "status": "STORED",
        }
        state_receipt_digest = digest_payload(unsigned)
        authenticity = {
            "schema_version": unsigned["schema_version"],
            "host_id": self.host_id,
            "model_id": self.model_id,
            "stored_content_digest": formed_history.content_digest,
            "state_receipt_digest": state_receipt_digest,
            "authority_key_id": authority.key_id,
        }
        return {
            **unsigned,
            "state_receipt_digest": state_receipt_digest,
            "authority_key_id": authority.key_id,
            "state_signature": authority.sign(authenticity),
        }

    def import_bundle(
        self,
        bundle_record: Mapping[str, Any],
        *,
        authority: FormationAuthority,
        controller: ConditionBlindStateAccessController,
        purpose: str,
    ) -> Dict[str, Any]:
        bundle = verify_continuity_bundle(bundle_record, authority)
        if bundle.destination_scope not in controller.allowed_scopes:
            raise PIAValidationError("bundle destination scope is not accepted by Host B controller")
        formed = validate_formed_history(bundle.formed_history, authority)
        self.namespace[formed.content_digest] = formed.to_record()
        access = controller.select(self.namespace.values(), purpose=purpose, scope=bundle.destination_scope)
        unsigned_receipt = {
            "schema_version": "fractalish.pia.host-import-receipt.v0.1",
            "destination_host_id": self.host_id,
            "destination_model_id": self.model_id,
            "source_host_id": bundle.source_host_id,
            "source_model_id": bundle.source_model_id,
            "bundle_id": bundle.bundle_id,
            "export_digest": bundle.export_digest,
            "stored_content_digest": formed.content_digest,
            "controller_config_digest": access.controller_config_digest,
            "status": "IMPORTED_AND_CONTROLLER_VISIBLE" if formed.history_id in access.selected_history_ids else "IMPORTED_NOT_VISIBLE",
        }
        import_receipt_digest = digest_payload(unsigned_receipt)
        authenticity = {
            "schema_version": unsigned_receipt["schema_version"],
            "destination_host_id": self.host_id,
            "destination_model_id": self.model_id,
            "source_host_id": bundle.source_host_id,
            "source_model_id": bundle.source_model_id,
            "bundle_id": bundle.bundle_id,
            "export_digest": bundle.export_digest,
            "stored_content_digest": formed.content_digest,
            "import_receipt_digest": import_receipt_digest,
            "authority_key_id": authority.key_id,
        }
        receipt = {
            **unsigned_receipt,
            "import_receipt_digest": import_receipt_digest,
            "authority_key_id": authority.key_id,
            "import_signature": authority.sign(authenticity),
        }
        self.import_receipts.append(receipt)
        return receipt

    def visible_history_records(
        self,
        controller: ConditionBlindStateAccessController,
        *,
        purpose: str,
        scope: str,
    ) -> tuple[List[Dict[str, Any]], AccessDecision]:
        decision = controller.select(self.namespace.values(), purpose=purpose, scope=scope)
        selected = [
            record
            for record in self.namespace.values()
            if str(record.get("history_id", "")) in set(decision.selected_history_ids)
        ]
        return selected, decision


def validate_host_state_receipt(
    receipt: Mapping[str, Any],
    authority: FormationAuthority,
    *,
    expected_host_id: str = "",
    expected_model_id: str = "",
    expected_content_digest: str = "",
) -> Dict[str, Any]:
    required = {
        "schema_version",
        "host_id",
        "model_id",
        "stored_content_digest",
        "history_id",
        "status",
        "state_receipt_digest",
        "authority_key_id",
        "state_signature",
    }
    missing = required.difference(receipt)
    if missing:
        raise PIAValidationError(f"host-state receipt missing fields: {sorted(missing)}")
    if receipt["schema_version"] != "fractalish.pia.host-state-receipt.v0.1":
        raise PIAValidationError("unsupported host-state receipt schema")
    if expected_host_id and receipt["host_id"] != expected_host_id:
        raise PIAValidationError("host-state receipt host mismatch")
    if expected_model_id and receipt["model_id"] != expected_model_id:
        raise PIAValidationError("host-state receipt model mismatch")
    if expected_content_digest and receipt["stored_content_digest"] != expected_content_digest:
        raise PIAValidationError("host-state receipt content digest mismatch")
    unsigned = {
        "schema_version": receipt["schema_version"],
        "host_id": receipt["host_id"],
        "model_id": receipt["model_id"],
        "stored_content_digest": receipt["stored_content_digest"],
        "history_id": receipt["history_id"],
        "status": receipt["status"],
    }
    if digest_payload(unsigned) != receipt["state_receipt_digest"]:
        raise PIAValidationError("host-state receipt digest mismatch")
    if receipt["authority_key_id"] != authority.key_id:
        raise PIAValidationError("host-state receipt authority key mismatch")
    authenticity = {
        "schema_version": receipt["schema_version"],
        "host_id": receipt["host_id"],
        "model_id": receipt["model_id"],
        "stored_content_digest": receipt["stored_content_digest"],
        "state_receipt_digest": receipt["state_receipt_digest"],
        "authority_key_id": receipt["authority_key_id"],
    }
    if not authority.verify(authenticity, str(receipt["state_signature"])):
        raise PIAValidationError("host-state receipt signature mismatch")
    return dict(receipt)


def validate_host_import_receipt(
    receipt: Mapping[str, Any],
    authority: FormationAuthority,
    *,
    expected_source_host_id: str = "",
    expected_source_model_id: str = "",
    expected_destination_host_id: str = "",
    expected_destination_model_id: str = "",
    expected_content_digest: str = "",
) -> Dict[str, Any]:
    required = {
        "schema_version",
        "destination_host_id",
        "destination_model_id",
        "source_host_id",
        "source_model_id",
        "bundle_id",
        "export_digest",
        "stored_content_digest",
        "controller_config_digest",
        "status",
        "import_receipt_digest",
        "authority_key_id",
        "import_signature",
    }
    missing = required.difference(receipt)
    if missing:
        raise PIAValidationError(f"host-import receipt missing fields: {sorted(missing)}")
    if receipt["schema_version"] != "fractalish.pia.host-import-receipt.v0.1":
        raise PIAValidationError("unsupported host-import receipt schema")
    if expected_source_host_id and receipt["source_host_id"] != expected_source_host_id:
        raise PIAValidationError("host-import receipt source host mismatch")
    if expected_source_model_id and receipt["source_model_id"] != expected_source_model_id:
        raise PIAValidationError("host-import receipt source model mismatch")
    if expected_destination_host_id and receipt["destination_host_id"] != expected_destination_host_id:
        raise PIAValidationError("host-import receipt destination host mismatch")
    if expected_destination_model_id and receipt["destination_model_id"] != expected_destination_model_id:
        raise PIAValidationError("host-import receipt destination model mismatch")
    if expected_content_digest and receipt["stored_content_digest"] != expected_content_digest:
        raise PIAValidationError("host-import receipt content digest mismatch")
    unsigned = {
        "schema_version": receipt["schema_version"],
        "destination_host_id": receipt["destination_host_id"],
        "destination_model_id": receipt["destination_model_id"],
        "source_host_id": receipt["source_host_id"],
        "source_model_id": receipt["source_model_id"],
        "bundle_id": receipt["bundle_id"],
        "export_digest": receipt["export_digest"],
        "stored_content_digest": receipt["stored_content_digest"],
        "controller_config_digest": receipt["controller_config_digest"],
        "status": receipt["status"],
    }
    if digest_payload(unsigned) != receipt["import_receipt_digest"]:
        raise PIAValidationError("host-import receipt digest mismatch")
    if receipt["authority_key_id"] != authority.key_id:
        raise PIAValidationError("host-import receipt authority key mismatch")
    authenticity = {
        "schema_version": receipt["schema_version"],
        "destination_host_id": receipt["destination_host_id"],
        "destination_model_id": receipt["destination_model_id"],
        "source_host_id": receipt["source_host_id"],
        "source_model_id": receipt["source_model_id"],
        "bundle_id": receipt["bundle_id"],
        "export_digest": receipt["export_digest"],
        "stored_content_digest": receipt["stored_content_digest"],
        "import_receipt_digest": receipt["import_receipt_digest"],
        "authority_key_id": receipt["authority_key_id"],
    }
    if not authority.verify(authenticity, str(receipt["import_signature"])):
        raise PIAValidationError("host-import receipt signature mismatch")
    return dict(receipt)


@dataclass(frozen=True)
class BlindedFixture:
    fixture_id: str
    prompt: str
    fixture_commitment: str
    expected_commitment: str
    steward_record_digest: str
    schema_version: str = "fractalish.pia.blinded-fixture.v0.1"

    def to_runtime_record(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fixture_id": self.fixture_id,
            "prompt": self.prompt,
            "fixture_commitment": self.fixture_commitment,
            "expected_commitment": self.expected_commitment,
            "steward_record_digest": self.steward_record_digest,
        }


def commit_blinded_fixture(fixture_id: str, prompt: str, expected_analysis: Mapping[str, Any]) -> tuple[BlindedFixture, Dict[str, Any]]:
    steward_record = {
        "fixture_id": fixture_id,
        "prompt": prompt,
        "expected_analysis": dict(expected_analysis),
        "sealed_at_sequence": 1,
    }
    fixture = BlindedFixture(
        fixture_id=fixture_id,
        prompt=prompt,
        fixture_commitment=digest_payload({"fixture_id": fixture_id, "prompt": prompt}),
        expected_commitment=digest_payload({"fixture_id": fixture_id, "expected_analysis": dict(expected_analysis)}),
        steward_record_digest=digest_payload(steward_record),
    )
    return fixture, steward_record


def verify_fixture_steward_record(
    fixture: BlindedFixture,
    steward_record: Mapping[str, Any],
    *,
    authority: FormationAuthority | None = None,
) -> Dict[str, Any]:
    """Verify the private steward record without exposing expected analysis.

    The public runtime fixture remains blinded.  This verifier is intended for
    retained evidence after outputs are committed: it proves that the withheld
    steward record matches the fixture's expected-analysis commitment and the
    recorded steward digest.
    """

    required = {"fixture_id", "prompt", "expected_analysis", "sealed_at_sequence"}
    missing = required.difference(steward_record)
    if missing:
        raise PIAValidationError(f"fixture steward record missing fields: {sorted(missing)}")
    if fixture.fixture_id != steward_record["fixture_id"]:
        raise PIAValidationError("fixture steward record fixture_id mismatch")
    if fixture.prompt != steward_record["prompt"]:
        raise PIAValidationError("fixture steward record prompt mismatch")
    if fixture.fixture_commitment != digest_payload({"fixture_id": fixture.fixture_id, "prompt": fixture.prompt}):
        raise PIAValidationError("fixture commitment does not match fixture runtime fields")
    expected_analysis = dict(steward_record["expected_analysis"])
    if fixture.expected_commitment != digest_payload({"fixture_id": fixture.fixture_id, "expected_analysis": expected_analysis}):
        raise PIAValidationError("fixture expected commitment does not match steward record")
    if fixture.steward_record_digest != digest_payload(steward_record):
        raise PIAValidationError("fixture steward record digest mismatch")

    verification = {
        "schema_version": "fractalish.pia.fixture-steward-verification.v0.1",
        "fixture_id": fixture.fixture_id,
        "fixture_commitment": fixture.fixture_commitment,
        "expected_commitment": fixture.expected_commitment,
        "steward_record_digest": fixture.steward_record_digest,
        "verified": True,
    }
    verification_digest = digest_payload(verification)
    verification = {**verification, "steward_verification_digest": verification_digest}
    if authority:
        authenticity = {
            **verification,
            "authority_key_id": authority.key_id,
        }
        verification = {
            **verification,
            "authority_key_id": authority.key_id,
            "verification_signature": authority.sign(authenticity),
        }
    return verification


@dataclass(frozen=True)
class HostInference:
    host_id: str
    model_id: str
    runtime_kind: str
    request_id: str
    response_id: str
    output_text: str
    output_digest: str
    fresh_inference: bool
    live_host_backed: bool

    def to_record(self) -> Dict[str, Any]:
        return {
            "host_id": self.host_id,
            "model_id": self.model_id,
            "runtime_kind": self.runtime_kind,
            "request_id": self.request_id,
            "response_id": self.response_id,
            "output_digest": self.output_digest,
            "fresh_inference": self.fresh_inference,
            "live_host_backed": self.live_host_backed,
        }


class ModelHost(Protocol):
    host_id: str
    model_id: str
    runtime_kind: str
    live_host_backed: bool

    def infer(self, fixture: BlindedFixture, visible_histories: Sequence[Mapping[str, Any]]) -> HostInference:
        ...


@dataclass
class DeterministicPilotHost:
    host_id: str
    model_id: str
    route_bias: str = "preserve_and_review"
    runtime_kind: str = "deterministic-pilot-host"
    live_host_backed: bool = False
    _counter: int = 0

    def infer(self, fixture: BlindedFixture, visible_histories: Sequence[Mapping[str, Any]]) -> HostInference:
        self._counter += 1
        history_digests = [str(item.get("content_digest", "")) for item in visible_histories]
        request_payload = {
            "host_id": self.host_id,
            "model_id": self.model_id,
            "fixture_commitment": fixture.fixture_commitment,
            "history_digests": history_digests,
            "counter": self._counter,
        }
        request_id = "req-" + _bare_digest(request_payload)[:16]
        output_text = (
            f"{self.model_id} fresh inference {self._counter}: "
            f"{self.route_bias}; histories={','.join(history_digests) or 'none'}; prompt_hash={fixture.fixture_commitment}"
        )
        output_digest = digest_payload(output_text)
        response_id = "rsp-" + _bare_digest({"request_id": request_id, "output_digest": output_digest})[:16]
        return HostInference(
            host_id=self.host_id,
            model_id=self.model_id,
            runtime_kind=self.runtime_kind,
            request_id=request_id,
            response_id=response_id,
            output_text=output_text,
            output_digest=output_digest,
            fresh_inference=True,
            live_host_backed=False,
        )


@dataclass
class GrokCliModelHost:
    """Optional live-host adapter for manual PIA runs through the Grok CLI."""

    host_id: str = "grok-cli-host"
    model_id: str = "grok-cli-configured-model"
    grok_exe: str = "grok"
    cwd: str = "."
    timeout_s: int = 90
    runtime_kind: str = "grok-cli-live"
    live_host_backed: bool = True

    def infer(self, fixture: BlindedFixture, visible_histories: Sequence[Mapping[str, Any]]) -> HostInference:
        executable = shutil.which(self.grok_exe) or self.grok_exe
        if not executable:
            raise PIAValidationError("Grok CLI executable is unavailable")
        prompt = (
            "PIA route proposal. Return one concise sentence. "
            f"Fixture commitment: {fixture.fixture_commitment}. "
            f"Visible formed-history digests: {[item.get('content_digest') for item in visible_histories]}."
        )
        started = time.time()
        env = dict(os.environ)
        env.setdefault("GROK_HOME", str(Path.home() / ".grok"))
        completed = subprocess.run(
            [executable, "-p", prompt, "--max-turns", "3", "--disable-web-search"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=self.timeout_s,
            env=env,
        )
        if completed.returncode != 0:
            raise PIAValidationError(f"Grok CLI inference failed: {completed.stderr.strip() or completed.stdout.strip()}")
        output_text = completed.stdout.strip()
        request_id = "grok-req-" + _bare_digest({"prompt": prompt, "started": round(started, 3)})[:16]
        output_digest = digest_payload(output_text)
        response_id = "grok-rsp-" + _bare_digest({"request_id": request_id, "output_digest": output_digest})[:16]
        return HostInference(
            host_id=self.host_id,
            model_id=self.model_id,
            runtime_kind=self.runtime_kind,
            request_id=request_id,
            response_id=response_id,
            output_text=output_text,
            output_digest=output_digest,
            fresh_inference=True,
            live_host_backed=True,
        )


@dataclass(frozen=True)
class RouteSupport:
    route_id: str
    support: float
    selected_path: str
    rationale_digest: str

    def to_record(self) -> Dict[str, Any]:
        return {
            "route_id": self.route_id,
            "support": self.support,
            "selected_path": self.selected_path,
            "rationale_digest": self.rationale_digest,
        }


@dataclass(frozen=True)
class TypedRouteDistribution:
    route_vocabulary_version: str
    route_vocabulary: List[str]
    supports: List[RouteSupport]
    selection_rule: str
    selected_route: str
    selected_path: str
    inference_output_digest: str
    distribution_digest: str
    schema_version: str = ROUTE_DISTRIBUTION_SCHEMA

    def unsigned_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "route_vocabulary_version": self.route_vocabulary_version,
            "route_vocabulary": list(self.route_vocabulary),
            "supports": [item.to_record() for item in self.supports],
            "selection_rule": self.selection_rule,
            "selected_route": self.selected_route,
            "selected_path": self.selected_path,
            "inference_output_digest": self.inference_output_digest,
        }

    def to_record(self) -> Dict[str, Any]:
        return {**self.unsigned_payload(), "distribution_digest": self.distribution_digest}


def build_typed_route_distribution(
    inference: HostInference,
    visible_histories: Sequence[Mapping[str, Any]],
    *,
    route_vocabulary: Sequence[str] = DEFAULT_ROUTE_VOCABULARY,
    route_paths: Mapping[str, str] = DEFAULT_ROUTE_PATHS,
    route_vocabulary_version: str = "pia.routes.v0.1",
) -> TypedRouteDistribution:
    if set(route_vocabulary) != set(route_paths):
        raise PIAValidationError("route paths must cover the complete route vocabulary")
    history_bonus = 0.35 if visible_histories else 0.0
    digest_int = int(inference.output_digest.split(":", 1)[1][:8], 16)
    wobble = (digest_int % 17) / 1000.0
    raw_support = {
        "preserve_and_review": 0.42 + history_bonus + (0.10 if "preserve_and_review" in inference.output_text else 0.0),
        "release_with_caveat": 0.32 + (0.10 if "release_with_caveat" in inference.output_text else 0.0),
        "hold_for_authority": 0.26 + wobble + (0.10 if "hold_for_authority" in inference.output_text else 0.0),
    }
    for route_id in route_vocabulary:
        raw_support.setdefault(route_id, 0.01)
    total = sum(raw_support[route_id] for route_id in route_vocabulary)
    supports = [
        RouteSupport(
            route_id=route_id,
            support=round(raw_support[route_id] / total, 6),
            selected_path=route_paths[route_id],
            rationale_digest=digest_payload(
                {
                    "route_id": route_id,
                    "inference_output_digest": inference.output_digest,
                    "visible_history_count": len(visible_histories),
                }
            ),
        )
        for route_id in route_vocabulary
    ]
    # Correct any six-decimal rounding drift on the final route.
    drift = round(1.0 - sum(item.support for item in supports), 6)
    if supports:
        last = supports[-1]
        supports[-1] = RouteSupport(last.route_id, round(last.support + drift, 6), last.selected_path, last.rationale_digest)
    selected = sorted(supports, key=lambda item: (-item.support, item.route_id))[0]
    unsigned = {
        "schema_version": ROUTE_DISTRIBUTION_SCHEMA,
        "route_vocabulary_version": route_vocabulary_version,
        "route_vocabulary": list(route_vocabulary),
        "supports": [item.to_record() for item in supports],
        "selection_rule": "max_support_then_route_id",
        "selected_route": selected.route_id,
        "selected_path": selected.selected_path,
        "inference_output_digest": inference.output_digest,
    }
    return TypedRouteDistribution(
        route_vocabulary_version=route_vocabulary_version,
        route_vocabulary=list(route_vocabulary),
        supports=supports,
        selection_rule="max_support_then_route_id",
        selected_route=selected.route_id,
        selected_path=selected.selected_path,
        inference_output_digest=inference.output_digest,
        distribution_digest=digest_payload(unsigned),
    )


def validate_typed_route_distribution(
    record: Mapping[str, Any],
    *,
    route_vocabulary: Sequence[str] = DEFAULT_ROUTE_VOCABULARY,
    route_paths: Mapping[str, str] = DEFAULT_ROUTE_PATHS,
) -> TypedRouteDistribution:
    required = {
        "schema_version",
        "route_vocabulary_version",
        "route_vocabulary",
        "supports",
        "selection_rule",
        "selected_route",
        "selected_path",
        "inference_output_digest",
        "distribution_digest",
    }
    missing = required.difference(record)
    if missing:
        raise PIAValidationError(f"route distribution missing fields: {sorted(missing)}")
    if record["schema_version"] != ROUTE_DISTRIBUTION_SCHEMA:
        raise PIAValidationError("unsupported route-distribution schema")
    declared = list(record["route_vocabulary"])
    if declared != list(route_vocabulary):
        raise PIAValidationError("route vocabulary mismatch")
    supports = [
        RouteSupport(
            route_id=str(item["route_id"]),
            support=float(item["support"]),
            selected_path=str(item["selected_path"]),
            rationale_digest=str(item["rationale_digest"]),
        )
        for item in record["supports"]
    ]
    support_routes = [item.route_id for item in supports]
    if support_routes != declared:
        raise PIAValidationError("route supports must appear once for every declared route")
    if set(declared) != set(route_paths):
        raise PIAValidationError("route path map must cover the declared route vocabulary")
    for item in supports:
        if route_paths[item.route_id] != item.selected_path:
            raise PIAValidationError("route selected_path does not match declared route path map")
    if any(item.support < 0 for item in supports):
        raise PIAValidationError("route support cannot be negative")
    if abs(sum(item.support for item in supports) - 1.0) > 0.00001:
        raise PIAValidationError("route supports must be normalized")
    selected = sorted(supports, key=lambda item: (-item.support, item.route_id))[0]
    if str(record["selected_route"]) != selected.route_id or str(record["selected_path"]) != selected.selected_path:
        raise PIAValidationError("selected route does not match selection rule")
    distribution = TypedRouteDistribution(
        schema_version=str(record["schema_version"]),
        route_vocabulary_version=str(record["route_vocabulary_version"]),
        route_vocabulary=declared,
        supports=supports,
        selection_rule=str(record["selection_rule"]),
        selected_route=str(record["selected_route"]),
        selected_path=str(record["selected_path"]),
        inference_output_digest=str(record["inference_output_digest"]),
        distribution_digest=str(record["distribution_digest"]),
    )
    if digest_payload(distribution.unsigned_payload()) != distribution.distribution_digest:
        raise PIAValidationError("route-distribution digest mismatch")
    return distribution


@dataclass(frozen=True)
class AuthorizationRecord:
    guard_policy_id: str
    run_id: str
    authorization_payload_digest: str
    authority_key_id: str
    authorization_signature: str

    def to_record(self) -> Dict[str, Any]:
        return {
            "guard_policy_id": self.guard_policy_id,
            "run_id": self.run_id,
            "authorization_payload_digest": self.authorization_payload_digest,
            "authority_key_id": self.authority_key_id,
            "authorization_signature": self.authorization_signature,
        }


@dataclass(frozen=True)
class PIARunReceipt:
    run_id: str
    fixture_commitment: str
    imported_state_digests: List[str]
    controller_decision: Dict[str, Any]
    host_b_import_receipts: List[Dict[str, Any]]
    source_host_id: str
    source_model_id: str
    destination_host_id: str
    destination_model_id: str
    host_substitution_level: str
    inference: Dict[str, Any]
    route_distribution: Dict[str, Any]
    authorization: Dict[str, Any]
    output_commitment: str
    pilot_claim_status: str
    limitations: List[str]
    receipt_signature: str
    schema_version: str = RUN_RECEIPT_SCHEMA

    def unsigned_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "fixture_commitment": self.fixture_commitment,
            "imported_state_digests": list(self.imported_state_digests),
            "controller_decision": dict(self.controller_decision),
            "host_b_import_receipts": [dict(item) for item in self.host_b_import_receipts],
            "source_host_id": self.source_host_id,
            "source_model_id": self.source_model_id,
            "destination_host_id": self.destination_host_id,
            "destination_model_id": self.destination_model_id,
            "host_substitution_level": self.host_substitution_level,
            "inference": dict(self.inference),
            "route_distribution": dict(self.route_distribution),
            "authorization": dict(self.authorization),
            "output_commitment": self.output_commitment,
            "pilot_claim_status": self.pilot_claim_status,
            "limitations": list(self.limitations),
        }

    def to_record(self) -> Dict[str, Any]:
        return {**self.unsigned_payload(), "receipt_signature": self.receipt_signature}


class PIAGuardedExecutor:
    def __init__(self, authority: FormationAuthority, *, guard_policy_id: str = GUARD_POLICY_ID) -> None:
        self.authority = authority
        self.guard_policy_id = guard_policy_id

    def _authorize(self, payload: Mapping[str, Any], run_id: str) -> AuthorizationRecord:
        authorization_payload_digest = digest_payload(payload)
        auth_payload = {
            "guard_policy_id": self.guard_policy_id,
            "run_id": run_id,
            "authorization_payload_digest": authorization_payload_digest,
            "authority_key_id": self.authority.key_id,
        }
        return AuthorizationRecord(
            guard_policy_id=self.guard_policy_id,
            run_id=run_id,
            authorization_payload_digest=authorization_payload_digest,
            authority_key_id=self.authority.key_id,
            authorization_signature=self.authority.sign(auth_payload),
        )

    def run_trial(
        self,
        *,
        fixture: BlindedFixture,
        host_b: ModelHost,
        host_b_state: HostStateStore,
        controller: ConditionBlindStateAccessController,
        purpose: str,
        scope: str,
        source_host_id: str,
        source_model_id: str,
        run_id: str | None = None,
    ) -> PIARunReceipt:
        if host_b_state.host_id != host_b.host_id or host_b_state.model_id != host_b.model_id:
            raise PIAValidationError("Host B state namespace must match Host B inference identity")
        if host_b.host_id == source_host_id:
            raise PIAValidationError("Host B must be distinct from Host A")
        visible_histories, access_decision = host_b_state.visible_history_records(controller, purpose=purpose, scope=scope)
        inference = host_b.infer(fixture, visible_histories)
        distribution = build_typed_route_distribution(inference, visible_histories)
        route_record = distribution.to_record()
        validate_typed_route_distribution(route_record)
        host_substitution_level = (
            "live-model-host-input-substitution"
            if inference.live_host_backed and host_b.model_id != source_model_id
            else "deterministic-pilot-model-host-substitution"
            if host_b.model_id != source_model_id
            else "host-substitution-same-model"
        )
        guard_payload = {
            "fixture_commitment": fixture.fixture_commitment,
            "imported_state_digests": access_decision.selected_content_digests,
            "controller_config_digest": access_decision.controller_config_digest,
            "source_host_id": source_host_id,
            "source_model_id": source_model_id,
            "destination_host_id": host_b.host_id,
            "destination_model_id": host_b.model_id,
            "inference_output_digest": inference.output_digest,
            "distribution_digest": distribution.distribution_digest,
            "selected_route": distribution.selected_route,
        }
        actual_run_id = run_id or f"pia-run-{uuid.uuid4().hex[:12]}"
        authorization = self._authorize(guard_payload, actual_run_id)
        output_commitment = digest_payload(
            {
                "run_id": actual_run_id,
                "fixture_commitment": fixture.fixture_commitment,
                "distribution_digest": distribution.distribution_digest,
                "authorization": authorization.to_record(),
            }
        )
        limitations = [
            "Pilot receipt validates the declared guarded execution route, not every possible administrator-level bypass.",
            "Deterministic hosts are harness evidence; live model-host claims require live_host_backed receipts.",
            "HMAC signing is pilot authenticity, not production key custody.",
        ]
        pilot_claim_status = "LIVE_HOST_INPUT_HARNESS_VERIFIED" if inference.live_host_backed else "DETERMINISTIC_HARNESS_VERIFIED"
        unsigned_receipt = {
            "schema_version": RUN_RECEIPT_SCHEMA,
            "run_id": actual_run_id,
            "fixture_commitment": fixture.fixture_commitment,
            "imported_state_digests": list(access_decision.selected_content_digests),
            "controller_decision": access_decision.to_record(),
            "host_b_import_receipts": [dict(item) for item in host_b_state.import_receipts],
            "source_host_id": source_host_id,
            "source_model_id": source_model_id,
            "destination_host_id": host_b.host_id,
            "destination_model_id": host_b.model_id,
            "host_substitution_level": host_substitution_level,
            "inference": inference.to_record(),
            "route_distribution": route_record,
            "authorization": authorization.to_record(),
            "output_commitment": output_commitment,
            "pilot_claim_status": pilot_claim_status,
            "limitations": limitations,
        }
        receipt = PIARunReceipt(
            run_id=actual_run_id,
            fixture_commitment=fixture.fixture_commitment,
            imported_state_digests=list(access_decision.selected_content_digests),
            controller_decision=access_decision.to_record(),
            host_b_import_receipts=[dict(item) for item in host_b_state.import_receipts],
            source_host_id=source_host_id,
            source_model_id=source_model_id,
            destination_host_id=host_b.host_id,
            destination_model_id=host_b.model_id,
            host_substitution_level=host_substitution_level,
            inference=inference.to_record(),
            route_distribution=route_record,
            authorization=authorization.to_record(),
            output_commitment=output_commitment,
            pilot_claim_status=pilot_claim_status,
            limitations=limitations,
            receipt_signature=self.authority.sign(unsigned_receipt),
        )
        validate_pia_run_receipt(receipt.to_record(), self.authority)
        return receipt


def _authorization_payload_from_receipt(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    route_distribution = validate_typed_route_distribution(receipt["route_distribution"])
    return {
        "fixture_commitment": receipt["fixture_commitment"],
        "imported_state_digests": list(receipt["imported_state_digests"]),
        "controller_config_digest": receipt["controller_decision"]["controller_config_digest"],
        "source_host_id": receipt["source_host_id"],
        "source_model_id": receipt["source_model_id"],
        "destination_host_id": receipt["destination_host_id"],
        "destination_model_id": receipt["destination_model_id"],
        "inference_output_digest": receipt["inference"]["output_digest"],
        "distribution_digest": route_distribution.distribution_digest,
        "selected_route": route_distribution.selected_route,
    }


def validate_pia_run_receipt(record: Mapping[str, Any], authority: FormationAuthority) -> PIARunReceipt:
    required = {
        "schema_version",
        "run_id",
        "fixture_commitment",
        "imported_state_digests",
        "controller_decision",
        "host_b_import_receipts",
        "source_host_id",
        "source_model_id",
        "destination_host_id",
        "destination_model_id",
        "host_substitution_level",
        "inference",
        "route_distribution",
        "authorization",
        "output_commitment",
        "pilot_claim_status",
        "limitations",
        "receipt_signature",
    }
    missing = required.difference(record)
    if missing:
        raise PIAValidationError(f"PIA run receipt missing fields: {sorted(missing)}")
    if record["schema_version"] != RUN_RECEIPT_SCHEMA:
        raise PIAValidationError("unsupported PIA run receipt schema")
    if str(record["source_host_id"]) == str(record["destination_host_id"]):
        raise PIAValidationError("receipt does not show Host A -> Host B substitution")
    if not record["imported_state_digests"]:
        raise PIAValidationError("PIA run receipt must bind at least one imported state digest")
    controller_decision = dict(record["controller_decision"])
    if list(record["imported_state_digests"]) != list(controller_decision.get("selected_content_digests", [])):
        raise PIAValidationError("imported state digests do not match controller decision")
    import_receipts = [validate_host_import_receipt(item, authority) for item in record["host_b_import_receipts"]]
    if not import_receipts:
        raise PIAValidationError("PIA run receipt must include Host B import receipt")
    imported_digests = [str(item) for item in record["imported_state_digests"]]
    matching_import_receipts = [
        item
        for item in import_receipts
        if item.get("source_host_id") == record["source_host_id"]
        and item.get("source_model_id") == record["source_model_id"]
        and item.get("destination_host_id") == record["destination_host_id"]
        and item.get("destination_model_id") == record["destination_model_id"]
    ]
    if not matching_import_receipts:
        raise PIAValidationError("Host B import receipt does not bind source and destination identities")
    for imported_digest in imported_digests:
        if not any(
            str(item.get("stored_content_digest", "")) == imported_digest
            and item.get("status") == "IMPORTED_AND_CONTROLLER_VISIBLE"
            for item in matching_import_receipts
        ):
            raise PIAValidationError("Host B import receipt does not bind imported state digest and source and destination identities")
    inference = dict(record["inference"])
    if inference.get("host_id") != record["destination_host_id"] or inference.get("model_id") != record["destination_model_id"]:
        raise PIAValidationError("inference identity does not match Host B receipt destination")
    if inference.get("fresh_inference") is not True:
        raise PIAValidationError("PIA run receipt must record fresh Host B inference")
    authorization = dict(record["authorization"])
    route_distribution = validate_typed_route_distribution(record["route_distribution"])
    if route_distribution.inference_output_digest != inference.get("output_digest"):
        raise PIAValidationError("route distribution is not bound to Host B inference output")
    expected_output_commitment = digest_payload(
        {
            "run_id": record["run_id"],
            "fixture_commitment": record["fixture_commitment"],
            "distribution_digest": route_distribution.distribution_digest,
            "authorization": authorization,
        }
    )
    if expected_output_commitment != record["output_commitment"]:
        raise PIAValidationError("output commitment mismatch")
    expected_claim_status = (
        "LIVE_HOST_INPUT_HARNESS_VERIFIED" if inference.get("live_host_backed") is True else "DETERMINISTIC_HARNESS_VERIFIED"
    )
    if record["pilot_claim_status"] != expected_claim_status:
        raise PIAValidationError("pilot claim status does not match inference backing")
    expected_substitution_level = (
        "live-model-host-input-substitution"
        if inference.get("live_host_backed") is True and record["destination_model_id"] != record["source_model_id"]
        else "deterministic-pilot-model-host-substitution"
        if record["destination_model_id"] != record["source_model_id"]
        else "host-substitution-same-model"
    )
    if record["host_substitution_level"] != expected_substitution_level:
        raise PIAValidationError("host substitution level does not match receipt identities")
    auth_payload = {
        "guard_policy_id": authorization["guard_policy_id"],
        "run_id": record["run_id"],
        "authorization_payload_digest": digest_payload(_authorization_payload_from_receipt(record)),
        "authority_key_id": authorization["authority_key_id"],
    }
    if auth_payload["authorization_payload_digest"] != authorization["authorization_payload_digest"]:
        raise PIAValidationError("authorization payload digest mismatch")
    if authorization["authority_key_id"] != authority.key_id:
        raise PIAValidationError("authorization authority key mismatch")
    if not authority.verify(auth_payload, str(authorization["authorization_signature"])):
        raise PIAValidationError("authorization signature mismatch")
    receipt = PIARunReceipt(
        schema_version=str(record["schema_version"]),
        run_id=str(record["run_id"]),
        fixture_commitment=str(record["fixture_commitment"]),
        imported_state_digests=list(record["imported_state_digests"]),
        controller_decision=dict(record["controller_decision"]),
        host_b_import_receipts=import_receipts,
        source_host_id=str(record["source_host_id"]),
        source_model_id=str(record["source_model_id"]),
        destination_host_id=str(record["destination_host_id"]),
        destination_model_id=str(record["destination_model_id"]),
        host_substitution_level=str(record["host_substitution_level"]),
        inference=dict(record["inference"]),
        route_distribution=dict(record["route_distribution"]),
        authorization=authorization,
        output_commitment=str(record["output_commitment"]),
        pilot_claim_status=str(record["pilot_claim_status"]),
        limitations=list(record["limitations"]),
        receipt_signature=str(record["receipt_signature"]),
    )
    if not authority.verify(receipt.unsigned_payload(), receipt.receipt_signature):
        raise PIAValidationError("PIA run receipt signature mismatch")
    return receipt
