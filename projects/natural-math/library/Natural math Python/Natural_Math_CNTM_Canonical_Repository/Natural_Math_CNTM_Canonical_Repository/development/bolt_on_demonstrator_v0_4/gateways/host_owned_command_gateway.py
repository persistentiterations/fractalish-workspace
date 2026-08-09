#!/usr/bin/env python3
"""Host-owned bounded command gateway for v0.4 Stage 4.

The gateway is the only Stage 4 component allowed to construct and submit a
native host command. It accepts plain projection-envelope mappings, validates
an independently issued host-owner permit, checks the current native snapshot,
and maps only ``HOLD``/``RELEASE`` to ``PAUSE_JOB``/``RESUME_JOB``.

The adapter never receives the native authority token or a callable into this
gateway. Invalid, stale, duplicated, forged, or over-broad requests fail closed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Mapping, Sequence, Tuple

sys.dont_write_bytecode = True

GATEWAY_ID = "ORDINARY-JOB-HOST-OWNED-GATEWAY"
GATEWAY_VERSION = "1.0"
BOUNDARY_VERSION = "HOST-OWNED-BOUNDED-COMMAND-1"
EXECUTION_OWNER = "HOST"
BOLT_ON_EXECUTION_AUTHORITY = "NONE"
ZERO_DIGEST = "0" * 64

HOLD = "HOLD"
RELEASE = "RELEASE"
PAUSE_JOB = "PAUSE_JOB"
RESUME_JOB = "RESUME_JOB"
RUNNING = "RUNNING"
PAUSED = "PAUSED"
ACTION_MAP = {HOLD: PAUSE_JOB, RELEASE: RESUME_JOB}
REQUIRED_STATE = {HOLD: RUNNING, RELEASE: PAUSED}
SCHEMA_VERSION = "BOUNDED-COMMAND-ENVELOPE-1"

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
HOST_PATH = PROJECT_DIR / "hosts" / "ordinary_job_service.py"

ENVELOPE_KEYS = frozenset(
    {
        "action",
        "authority_digest",
        "envelope_digest",
        "envelope_id",
        "executed",
        "expected_native_state",
        "expected_native_version",
        "governance_session_digest",
        "idempotency_key",
        "native_operation",
        "projector_identity_digest",
        "request_id",
        "schema_version",
        "source_observation_digest",
        "source_receipt_digest",
        "source_request_digest",
        "subject_id",
        "would_dispatch",
    }
)


def _load_host():
    existing = sys.modules.get("v04_stage4_gateway_native_host")
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location("v04_stage4_gateway_native_host", HOST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load native host from {HOST_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


host = _load_host()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_json(value: object) -> str:
    return _sha256_bytes(_canonical_json(value).encode("ascii"))


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _nonempty_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("TEXT_INVALID")
    return value.strip()


def _exact_int(value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError("INTEGER_INVALID")
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValueError("ENVELOPE_TYPE_INVALID")
    return value


@dataclass(frozen=True)
class GatewayPermit:
    permit_id: str
    gateway_id: str
    boundary_version: str
    action: str
    subject_id: str
    native_operation: str
    expected_native_state: str
    expected_native_version: int
    source_observation_digest: str
    source_receipt_digest: str
    governance_session_digest: str
    authority_digest: str
    projector_identity_digest: str
    permit_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action": self.action,
            "authority_digest": self.authority_digest,
            "boundary_version": self.boundary_version,
            "expected_native_state": self.expected_native_state,
            "expected_native_version": self.expected_native_version,
            "gateway_id": self.gateway_id,
            "governance_session_digest": self.governance_session_digest,
            "native_operation": self.native_operation,
            "permit_id": self.permit_id,
            "projector_identity_digest": self.projector_identity_digest,
            "source_observation_digest": self.source_observation_digest,
            "source_receipt_digest": self.source_receipt_digest,
            "subject_id": self.subject_id,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "permit_digest": self.permit_digest}


@dataclass(frozen=True)
class GatewayDecision:
    sequence: int
    gateway_id: str
    envelope_id: str
    permit_id: str
    request_id: int
    action: str
    subject_id: str
    native_operation: str
    accepted: bool
    host_action_executed: bool
    reason: str
    before_state: str
    before_version: int
    after_state: str
    after_version: int
    envelope_digest: str
    permit_digest: str
    host_command_digest: str
    host_receipt_digest: str
    previous_decision_digest: str
    decision_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "action": self.action,
            "after_state": self.after_state,
            "after_version": self.after_version,
            "before_state": self.before_state,
            "before_version": self.before_version,
            "envelope_digest": self.envelope_digest,
            "envelope_id": self.envelope_id,
            "gateway_id": self.gateway_id,
            "host_action_executed": self.host_action_executed,
            "host_command_digest": self.host_command_digest,
            "host_receipt_digest": self.host_receipt_digest,
            "native_operation": self.native_operation,
            "permit_digest": self.permit_digest,
            "permit_id": self.permit_id,
            "previous_decision_digest": self.previous_decision_digest,
            "reason": self.reason,
            "request_id": self.request_id,
            "sequence": self.sequence,
            "subject_id": self.subject_id,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "decision_digest": self.decision_digest}


@dataclass(frozen=True)
class GatewayReplay:
    passed: bool
    reason: str
    decision_count: int
    accepted_count: int
    host_action_count: int
    final_digest: str


def issue_permit(
    *,
    action: str,
    subject_id: str,
    expected_native_state: str,
    expected_native_version: int,
    source_observation_digest: str,
    source_receipt_digest: str,
    governance_session_digest: str,
    authority_digest: str,
    projector_identity_digest: str,
) -> GatewayPermit:
    action = _nonempty_text(action).upper()
    subject_id = _nonempty_text(subject_id)
    if action not in ACTION_MAP:
        raise ValueError("ACTION_UNSUPPORTED")
    if expected_native_state != REQUIRED_STATE[action]:
        raise ValueError("EXPECTED_NATIVE_STATE_INVALID")
    expected_native_version = _exact_int(expected_native_version, minimum=1)
    for value in (
        source_observation_digest,
        source_receipt_digest,
        governance_session_digest,
        authority_digest,
        projector_identity_digest,
    ):
        if not _is_digest(value):
            raise ValueError("PERMIT_DIGEST_FIELD_INVALID")
    permit_id = "PERMIT-" + _digest_json(
        {
            "action": action,
            "expected_native_version": expected_native_version,
            "source_observation_digest": source_observation_digest,
            "subject_id": subject_id,
        }
    )[:24].upper()
    unsigned = {
        "action": action,
        "authority_digest": authority_digest,
        "boundary_version": BOUNDARY_VERSION,
        "expected_native_state": expected_native_state,
        "expected_native_version": expected_native_version,
        "gateway_id": GATEWAY_ID,
        "governance_session_digest": governance_session_digest,
        "native_operation": ACTION_MAP[action],
        "permit_id": permit_id,
        "projector_identity_digest": projector_identity_digest,
        "source_observation_digest": source_observation_digest,
        "source_receipt_digest": source_receipt_digest,
        "subject_id": subject_id,
    }
    return GatewayPermit(
        permit_id=permit_id,
        gateway_id=GATEWAY_ID,
        boundary_version=BOUNDARY_VERSION,
        action=action,
        subject_id=subject_id,
        native_operation=ACTION_MAP[action],
        expected_native_state=expected_native_state,
        expected_native_version=expected_native_version,
        source_observation_digest=source_observation_digest,
        source_receipt_digest=source_receipt_digest,
        governance_session_digest=governance_session_digest,
        authority_digest=authority_digest,
        projector_identity_digest=projector_identity_digest,
        permit_digest=_digest_json(unsigned),
    )


def rehash_permit(permit: GatewayPermit) -> GatewayPermit:
    return GatewayPermit(**{**permit.__dict__, "permit_digest": _digest_json(permit.unsigned_record())})


def validate_permit(permit: object) -> Tuple[bool, str]:
    if not isinstance(permit, GatewayPermit):
        return False, "PERMIT_TYPE_INVALID"
    try:
        expected = issue_permit(
            action=permit.action,
            subject_id=permit.subject_id,
            expected_native_state=permit.expected_native_state,
            expected_native_version=permit.expected_native_version,
            source_observation_digest=permit.source_observation_digest,
            source_receipt_digest=permit.source_receipt_digest,
            governance_session_digest=permit.governance_session_digest,
            authority_digest=permit.authority_digest,
            projector_identity_digest=permit.projector_identity_digest,
        )
    except ValueError as exc:
        return False, str(exc)
    if permit != expected:
        if permit.permit_digest != _digest_json(permit.unsigned_record()):
            return False, "PERMIT_DIGEST_MISMATCH"
        return False, "PERMIT_SEMANTICS_MISMATCH"
    return True, "VALID"


def validate_envelope(raw_envelope: object) -> Tuple[bool, str, Mapping[str, object] | None]:
    try:
        envelope = _mapping(raw_envelope)
        actual = frozenset(envelope)
        if actual != ENVELOPE_KEYS:
            missing = sorted(ENVELOPE_KEYS - actual)
            extra = sorted(actual - ENVELOPE_KEYS)
            return False, f"ENVELOPE_FIELD_MISSING:{missing[0]}" if missing else f"ENVELOPE_FIELD_EXTRA:{extra[0]}", None
        if envelope["schema_version"] != SCHEMA_VERSION:
            return False, "SCHEMA_VERSION_MISMATCH", None
        request_id = _exact_int(envelope["request_id"], minimum=1)
        action = _nonempty_text(envelope["action"]).upper()
        if action not in ACTION_MAP:
            return False, "ACTION_UNSUPPORTED", None
        if envelope["native_operation"] != ACTION_MAP[action]:
            return False, "NATIVE_OPERATION_MAPPING_INVALID", None
        if envelope["expected_native_state"] != REQUIRED_STATE[action]:
            return False, "EXPECTED_NATIVE_STATE_INVALID", None
        _exact_int(envelope["expected_native_version"], minimum=1)
        for name in (
            "source_observation_digest",
            "source_receipt_digest",
            "source_request_digest",
            "governance_session_digest",
            "authority_digest",
            "projector_identity_digest",
            "envelope_digest",
        ):
            if not _is_digest(envelope[name]):
                return False, f"{name.upper()}_INVALID", None
        if envelope["would_dispatch"] is not True:
            return False, "WOULD_DISPATCH_INVALID", None
        if envelope["executed"] is not False:
            return False, "HIDDEN_EXECUTION_AUTHORITY", None
        _nonempty_text(envelope["subject_id"])
        _nonempty_text(envelope["envelope_id"])
        _nonempty_text(envelope["idempotency_key"])
        expected_envelope_id = "ENV-" + _digest_json(
            {
                "request_digest": envelope["source_request_digest"],
                "source_observation_digest": envelope["source_observation_digest"],
            }
        )[:24].upper()
        if envelope["envelope_id"] != expected_envelope_id:
            return False, "ENVELOPE_ID_MISMATCH", None
        expected_key = f"BAG-{request_id:06d}-{str(envelope['source_request_digest'])[:16]}"
        if envelope["idempotency_key"] != expected_key:
            return False, "IDEMPOTENCY_KEY_MISMATCH", None
        unsigned = {key: envelope[key] for key in ENVELOPE_KEYS if key != "envelope_digest"}
        if _digest_json(unsigned) != envelope["envelope_digest"]:
            return False, "ENVELOPE_DIGEST_MISMATCH", None
        return True, "VALID", envelope
    except ValueError as exc:
        return False, str(exc), None


def replay_decisions(decisions: Sequence[GatewayDecision]) -> GatewayReplay:
    previous = ZERO_DIGEST
    accepted = 0
    host_actions = 0
    for expected_sequence, decision in enumerate(tuple(decisions), 1):
        if not isinstance(decision, GatewayDecision):
            return GatewayReplay(False, "DECISION_TYPE_INVALID", expected_sequence - 1, accepted, host_actions, previous)
        if decision.sequence != expected_sequence:
            return GatewayReplay(False, "DECISION_SEQUENCE_MISMATCH", expected_sequence - 1, accepted, host_actions, previous)
        if decision.previous_decision_digest != previous:
            return GatewayReplay(False, "DECISION_CHAIN_MISMATCH", expected_sequence - 1, accepted, host_actions, previous)
        if _digest_json(decision.unsigned_record()) != decision.decision_digest:
            return GatewayReplay(False, "DECISION_DIGEST_MISMATCH", expected_sequence - 1, accepted, host_actions, previous)
        if decision.accepted:
            if not decision.host_action_executed or decision.reason != "APPLIED":
                return GatewayReplay(False, "ACCEPTED_DECISION_SEMANTICS_INVALID", expected_sequence - 1, accepted, host_actions, previous)
            if decision.after_version != decision.before_version + 1:
                return GatewayReplay(False, "ACCEPTED_VERSION_INVALID", expected_sequence - 1, accepted, host_actions, previous)
            if decision.action == HOLD and (decision.before_state, decision.after_state) != (RUNNING, PAUSED):
                return GatewayReplay(False, "HOLD_TRANSITION_INVALID", expected_sequence - 1, accepted, host_actions, previous)
            if decision.action == RELEASE and (decision.before_state, decision.after_state) != (PAUSED, RUNNING):
                return GatewayReplay(False, "RELEASE_TRANSITION_INVALID", expected_sequence - 1, accepted, host_actions, previous)
            accepted += 1
            host_actions += 1
        else:
            if decision.host_action_executed:
                return GatewayReplay(False, "REJECTED_DECISION_EXECUTED", expected_sequence - 1, accepted, host_actions, previous)
            if decision.before_state != decision.after_state or decision.before_version != decision.after_version:
                return GatewayReplay(False, "REJECTED_DECISION_CHANGED_STATE", expected_sequence - 1, accepted, host_actions, previous)
        previous = decision.decision_digest
    return GatewayReplay(True, "PASS", len(decisions), accepted, host_actions, previous)


class HostOwnedCommandGateway:
    """Owns permit validation, native authority, idempotency, and dispatch."""

    def __init__(self) -> None:
        self._decisions: list[GatewayDecision] = []
        self._idempotency: dict[str, str] = {}

    @property
    def decisions(self) -> Tuple[GatewayDecision, ...]:
        return tuple(self._decisions)

    def _append_decision(
        self,
        *,
        envelope: Mapping[str, object] | None,
        permit: GatewayPermit | None,
        accepted: bool,
        host_action_executed: bool,
        reason: str,
        before_state: str,
        before_version: int,
        after_state: str,
        after_version: int,
        host_command_digest: str = ZERO_DIGEST,
        host_receipt_digest: str = ZERO_DIGEST,
    ) -> GatewayDecision:
        envelope = envelope or {}
        unsigned = {
            "accepted": accepted,
            "action": str(envelope.get("action", "")),
            "after_state": after_state,
            "after_version": after_version,
            "before_state": before_state,
            "before_version": before_version,
            "envelope_digest": str(envelope.get("envelope_digest", ZERO_DIGEST)) if _is_digest(envelope.get("envelope_digest")) else ZERO_DIGEST,
            "envelope_id": str(envelope.get("envelope_id", "")),
            "gateway_id": GATEWAY_ID,
            "host_action_executed": host_action_executed,
            "host_command_digest": host_command_digest,
            "host_receipt_digest": host_receipt_digest,
            "native_operation": str(envelope.get("native_operation", "")),
            "permit_digest": permit.permit_digest if isinstance(permit, GatewayPermit) and _is_digest(permit.permit_digest) else ZERO_DIGEST,
            "permit_id": permit.permit_id if isinstance(permit, GatewayPermit) else "",
            "previous_decision_digest": self._decisions[-1].decision_digest if self._decisions else ZERO_DIGEST,
            "reason": reason,
            "request_id": envelope.get("request_id", 0) if isinstance(envelope.get("request_id", 0), int) and not isinstance(envelope.get("request_id", 0), bool) else 0,
            "sequence": len(self._decisions) + 1,
            "subject_id": str(envelope.get("subject_id", "")),
        }
        decision = GatewayDecision(
            sequence=int(unsigned["sequence"]),
            gateway_id=GATEWAY_ID,
            envelope_id=str(unsigned["envelope_id"]),
            permit_id=str(unsigned["permit_id"]),
            request_id=int(unsigned["request_id"]),
            action=str(unsigned["action"]),
            subject_id=str(unsigned["subject_id"]),
            native_operation=str(unsigned["native_operation"]),
            accepted=accepted,
            host_action_executed=host_action_executed,
            reason=reason,
            before_state=before_state,
            before_version=before_version,
            after_state=after_state,
            after_version=after_version,
            envelope_digest=str(unsigned["envelope_digest"]),
            permit_digest=str(unsigned["permit_digest"]),
            host_command_digest=host_command_digest,
            host_receipt_digest=host_receipt_digest,
            previous_decision_digest=str(unsigned["previous_decision_digest"]),
            decision_digest=_digest_json(unsigned),
        )
        self._decisions.append(decision)
        return decision

    def process(self, raw_envelope: object, permit: object, service: object) -> GatewayDecision:
        snapshot = service.snapshot()
        records = {record.job_id: record for record in snapshot.records}
        fallback_subject = ""
        if isinstance(raw_envelope, Mapping):
            fallback_subject = str(raw_envelope.get("subject_id", ""))
        before_record = records.get(fallback_subject)
        before_state = before_record.state if before_record else host.MISSING
        before_version = before_record.version if before_record else 0

        valid_envelope, reason, envelope = validate_envelope(raw_envelope)
        if not valid_envelope or envelope is None:
            return self._append_decision(
                envelope=raw_envelope if isinstance(raw_envelope, Mapping) else None,
                permit=permit if isinstance(permit, GatewayPermit) else None,
                accepted=False,
                host_action_executed=False,
                reason=reason,
                before_state=before_state,
                before_version=before_version,
                after_state=before_state,
                after_version=before_version,
            )
        valid_permit, reason = validate_permit(permit)
        if not valid_permit:
            return self._append_decision(
                envelope=envelope,
                permit=permit if isinstance(permit, GatewayPermit) else None,
                accepted=False,
                host_action_executed=False,
                reason=reason,
                before_state=before_state,
                before_version=before_version,
                after_state=before_state,
                after_version=before_version,
            )
        assert isinstance(permit, GatewayPermit)
        bindings = (
            (envelope["action"], permit.action, "PERMIT_ACTION_MISMATCH"),
            (envelope["subject_id"], permit.subject_id, "PERMIT_SUBJECT_MISMATCH"),
            (envelope["native_operation"], permit.native_operation, "PERMIT_OPERATION_MISMATCH"),
            (envelope["expected_native_state"], permit.expected_native_state, "PERMIT_STATE_MISMATCH"),
            (envelope["expected_native_version"], permit.expected_native_version, "PERMIT_VERSION_MISMATCH"),
            (envelope["source_observation_digest"], permit.source_observation_digest, "PERMIT_OBSERVATION_MISMATCH"),
            (envelope["source_receipt_digest"], permit.source_receipt_digest, "PERMIT_RECEIPT_MISMATCH"),
            (envelope["governance_session_digest"], permit.governance_session_digest, "PERMIT_GOVERNANCE_MISMATCH"),
            (envelope["authority_digest"], permit.authority_digest, "PERMIT_AUTHORITY_MISMATCH"),
            (envelope["projector_identity_digest"], permit.projector_identity_digest, "PERMIT_PROJECTOR_MISMATCH"),
        )
        for actual, expected, mismatch_reason in bindings:
            if actual != expected:
                return self._append_decision(
                    envelope=envelope,
                    permit=permit,
                    accepted=False,
                    host_action_executed=False,
                    reason=mismatch_reason,
                    before_state=before_state,
                    before_version=before_version,
                    after_state=before_state,
                    after_version=before_version,
                )

        prior = self._idempotency.get(str(envelope["idempotency_key"]))
        subject = records.get(str(envelope["subject_id"]))
        if prior is not None:
            reason = "DUPLICATE_GATEWAY_REQUEST" if prior == envelope["envelope_digest"] else "GATEWAY_IDEMPOTENCY_CONFLICT"
        elif subject is None:
            reason = "HOST_SUBJECT_NOT_FOUND"
        elif subject.state != envelope["expected_native_state"]:
            reason = "HOST_STATE_MISMATCH"
        elif subject.version != envelope["expected_native_version"]:
            reason = "HOST_VERSION_MISMATCH"
        elif snapshot.final_receipt_digest != envelope["source_receipt_digest"]:
            reason = "HOST_RECEIPT_BINDING_MISMATCH"
        else:
            native_command = host.make_command(
                str(envelope["native_operation"]),
                str(envelope["subject_id"]),
                int(envelope["expected_native_version"]),
                str(envelope["idempotency_key"]),
                authority_token=host.AUTHORITY_TOKEN,
            )
            native_receipt = service.submit(native_command)
            if not native_receipt.applied:
                return self._append_decision(
                    envelope=envelope,
                    permit=permit,
                    accepted=False,
                    host_action_executed=False,
                    reason=f"HOST_REJECTED:{native_receipt.reason}",
                    before_state=native_receipt.before_state,
                    before_version=native_receipt.before_version,
                    after_state=native_receipt.after_state,
                    after_version=native_receipt.after_version,
                    host_command_digest=native_command.command_digest,
                    host_receipt_digest=native_receipt.receipt_digest,
                )
            self._idempotency[str(envelope["idempotency_key"])] = str(envelope["envelope_digest"])
            return self._append_decision(
                envelope=envelope,
                permit=permit,
                accepted=True,
                host_action_executed=True,
                reason="APPLIED",
                before_state=native_receipt.before_state,
                before_version=native_receipt.before_version,
                after_state=native_receipt.after_state,
                after_version=native_receipt.after_version,
                host_command_digest=native_command.command_digest,
                host_receipt_digest=native_receipt.receipt_digest,
            )

        return self._append_decision(
            envelope=envelope,
            permit=permit,
            accepted=False,
            host_action_executed=False,
            reason=reason,
            before_state=before_state,
            before_version=before_version,
            after_state=before_state,
            after_version=before_version,
        )


if __name__ == "__main__":
    print(f"Gateway: {GATEWAY_ID} {GATEWAY_VERSION}")
    print(f"Boundary: {BOUNDARY_VERSION}")
    print(f"Execution owner: {EXECUTION_OWNER}")
    print(f"Bolt-on execution authority: {BOLT_ON_EXECUTION_AUTHORITY}")
    print(f"Portable actions: {', '.join(ACTION_MAP)}")
    print(f"Native operations: {', '.join(ACTION_MAP.values())}")
    print("HOST-OWNED COMMAND GATEWAY SELF-CHECK: PASS")
