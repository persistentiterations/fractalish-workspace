#!/usr/bin/env python3
"""Projection-only adapter for v0.4 Stage 4.

This module binds frozen v0.3 ``HOLD`` and ``RELEASE`` requests to the ordinary
job-service operations ``PAUSE_JOB`` and ``RESUME_JOB``. It consumes plain
Stage 3 observation mappings and emits a deterministic command envelope.

It has no host import, no native authority token, no gateway callable, no
command transport, and no execution method. Every envelope reports
``executed=False``. The host-owned gateway independently validates the envelope
before it may construct a native command.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Mapping, Tuple

sys.dont_write_bytecode = True

PROJECTOR_ID = "ORDINARY-JOB-BOUNDED-ACTION-PROJECTOR"
PROJECTOR_VERSION = "1.0"
SCHEMA_VERSION = "BOUNDED-COMMAND-ENVELOPE-1"
MODE = "PROJECT_ONLY"
EXECUTION_AUTHORITY = "NONE"
COMMAND_TRANSPORT: Tuple[str, ...] = ()
ZERO_DIGEST = "0" * 64

HOLD = "HOLD"
RELEASE = "RELEASE"
PAUSE_JOB = "PAUSE_JOB"
RESUME_JOB = "RESUME_JOB"
RUNNING = "RUNNING"
PAUSED = "PAUSED"
ACTIVE = "ACTIVE"
HELD = "HELD"
ACTION_MAP = {HOLD: PAUSE_JOB, RELEASE: RESUME_JOB}
REQUIRED_NATIVE_STATE = {HOLD: RUNNING, RELEASE: PAUSED}
REQUIRED_OBSERVED_STATE = {HOLD: ACTIVE, RELEASE: HELD}

THIS_FILE = Path(__file__).resolve()
REPOSITORY_ROOT = THIS_FILE.parents[3]
FROZEN_CONTRACT_PATH = (
    REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.3" / "portability" / "portable_adapter_contract.py"
)

OBSERVATION_EVENT_KEYS = frozenset(
    {
        "applied",
        "native_after_state",
        "native_after_version",
        "native_before_state",
        "native_before_version",
        "native_operation",
        "observed_after_state",
        "observed_before_state",
        "observation_digest",
        "previous_observation_digest",
        "reason",
        "sequence",
        "source_command_digest",
        "source_receipt_digest",
        "subject_id",
    }
)
OBSERVED_SUBJECT_KEYS = frozenset(
    {
        "checkpoint_count",
        "native_state",
        "native_version",
        "observed_state",
        "source_record_digest",
        "subject_digest",
        "subject_id",
    }
)
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


class ProjectionRejected(ValueError):
    """Raised when portable or observed evidence cannot be projected safely."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _load_frozen_contract():
    existing = sys.modules.get("frozen_v03_contract_for_v04_stage4_projector")
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        "frozen_v03_contract_for_v04_stage4_projector", FROZEN_CONTRACT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load frozen contract from {FROZEN_CONTRACT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


frozen_v03 = _load_frozen_contract()


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


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ProjectionRejected(f"{name.upper()}_TYPE_INVALID")
    return value


def _exact_keys(value: Mapping[str, object], expected: frozenset[str], name: str) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            raise ProjectionRejected(f"{name.upper()}_FIELD_MISSING:{missing[0]}")
        raise ProjectionRejected(f"{name.upper()}_FIELD_EXTRA:{extra[0]}")


def _exact_int(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectionRejected(f"{name.upper()}_TYPE_INVALID")
    if value < minimum:
        raise ProjectionRejected(f"{name.upper()}_RANGE_INVALID")
    return value


def _nonempty_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectionRejected(f"{name.upper()}_INVALID")
    return value.strip()


@dataclass(frozen=True)
class ProjectorIdentity:
    projector_id: str
    projector_version: str
    schema_version: str
    mode: str
    execution_authority: str
    command_transport: Tuple[str, ...]
    supported_actions: Tuple[str, ...]
    identity_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "command_transport": list(self.command_transport),
            "execution_authority": self.execution_authority,
            "mode": self.mode,
            "projector_id": self.projector_id,
            "projector_version": self.projector_version,
            "schema_version": self.schema_version,
            "supported_actions": list(self.supported_actions),
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "identity_digest": self.identity_digest}


@dataclass(frozen=True)
class BoundedCommandEnvelope:
    schema_version: str
    envelope_id: str
    request_id: int
    action: str
    subject_id: str
    native_operation: str
    expected_native_state: str
    expected_native_version: int
    source_observation_digest: str
    source_receipt_digest: str
    source_request_digest: str
    governance_session_digest: str
    authority_digest: str
    projector_identity_digest: str
    would_dispatch: bool
    executed: bool
    idempotency_key: str
    envelope_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action": self.action,
            "authority_digest": self.authority_digest,
            "envelope_id": self.envelope_id,
            "executed": self.executed,
            "expected_native_state": self.expected_native_state,
            "expected_native_version": self.expected_native_version,
            "governance_session_digest": self.governance_session_digest,
            "idempotency_key": self.idempotency_key,
            "native_operation": self.native_operation,
            "projector_identity_digest": self.projector_identity_digest,
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "source_observation_digest": self.source_observation_digest,
            "source_receipt_digest": self.source_receipt_digest,
            "source_request_digest": self.source_request_digest,
            "subject_id": self.subject_id,
            "would_dispatch": self.would_dispatch,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "envelope_digest": self.envelope_digest}


def build_identity() -> ProjectorIdentity:
    unsigned = {
        "command_transport": [],
        "execution_authority": EXECUTION_AUTHORITY,
        "mode": MODE,
        "projector_id": PROJECTOR_ID,
        "projector_version": PROJECTOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "supported_actions": [HOLD, RELEASE],
    }
    return ProjectorIdentity(
        projector_id=PROJECTOR_ID,
        projector_version=PROJECTOR_VERSION,
        schema_version=SCHEMA_VERSION,
        mode=MODE,
        execution_authority=EXECUTION_AUTHORITY,
        command_transport=COMMAND_TRANSPORT,
        supported_actions=(HOLD, RELEASE),
        identity_digest=_digest_json(unsigned),
    )


def validate_identity(identity: object) -> Tuple[bool, str]:
    if not isinstance(identity, ProjectorIdentity):
        return False, "IDENTITY_TYPE_INVALID"
    expected = build_identity()
    if identity != expected:
        return False, "IDENTITY_MISMATCH"
    if identity.execution_authority != "NONE" or identity.command_transport:
        return False, "PROJECTOR_AUTHORITY_INVALID"
    return True, "VALID"


def _validate_observation_event(raw_event: object) -> Mapping[str, object]:
    event = _mapping(raw_event, "observation_event")
    _exact_keys(event, OBSERVATION_EVENT_KEYS, "observation_event")
    _exact_int(event["sequence"], "sequence", minimum=1)
    _exact_int(event["native_before_version"], "native_before_version")
    _exact_int(event["native_after_version"], "native_after_version")
    for name in (
        "subject_id",
        "native_operation",
        "native_before_state",
        "native_after_state",
        "observed_before_state",
        "observed_after_state",
        "reason",
    ):
        _nonempty_text(event[name], name)
    for name in (
        "source_command_digest",
        "source_receipt_digest",
        "previous_observation_digest",
        "observation_digest",
    ):
        if not _is_digest(event[name]):
            raise ProjectionRejected(f"{name.upper()}_INVALID")
    if not isinstance(event["applied"], bool):
        raise ProjectionRejected("APPLIED_TYPE_INVALID")
    unsigned = {key: event[key] for key in OBSERVATION_EVENT_KEYS if key != "observation_digest"}
    if _digest_json(unsigned) != event["observation_digest"]:
        raise ProjectionRejected("OBSERVATION_EVENT_DIGEST_MISMATCH")
    return event


def _validate_observed_subject(raw_subject: object) -> Mapping[str, object]:
    subject = _mapping(raw_subject, "observed_subject")
    _exact_keys(subject, OBSERVED_SUBJECT_KEYS, "observed_subject")
    _nonempty_text(subject["subject_id"], "subject_id")
    _nonempty_text(subject["native_state"], "native_state")
    _nonempty_text(subject["observed_state"], "observed_state")
    _exact_int(subject["native_version"], "native_version", minimum=1)
    _exact_int(subject["checkpoint_count"], "checkpoint_count")
    if not _is_digest(subject["source_record_digest"]) or not _is_digest(subject["subject_digest"]):
        raise ProjectionRejected("OBSERVED_SUBJECT_DIGEST_INVALID")
    unsigned = {key: subject[key] for key in OBSERVED_SUBJECT_KEYS if key != "subject_digest"}
    if _digest_json(unsigned) != subject["subject_digest"]:
        raise ProjectionRejected("OBSERVED_SUBJECT_DIGEST_MISMATCH")
    return subject


def build_portable_request(
    *,
    request_id: int,
    action: str,
    subject_id: str,
    source_observation_digest: str,
    governance_session_digest: str,
    authority_digest: str,
    observed_state: str,
    current_epoch: int,
):
    return frozen_v03.build_action_request(
        request_id=request_id,
        action=action,
        subject_id=subject_id,
        source_event_digest=source_observation_digest,
        governance_session_digest=governance_session_digest,
        authority_digest=authority_digest,
        expected_state_digest=frozen_v03.state_digest(observed_state),
        current_epoch=current_epoch,
    )


def validate_envelope_record(raw_envelope: object) -> Tuple[bool, str]:
    try:
        envelope = _mapping(raw_envelope, "envelope")
        _exact_keys(envelope, ENVELOPE_KEYS, "envelope")
        if envelope["schema_version"] != SCHEMA_VERSION:
            return False, "SCHEMA_VERSION_MISMATCH"
        _nonempty_text(envelope["envelope_id"], "envelope_id")
        _exact_int(envelope["request_id"], "request_id", minimum=1)
        action = _nonempty_text(envelope["action"], "action").upper()
        if action not in ACTION_MAP:
            return False, "ACTION_UNSUPPORTED"
        if envelope["native_operation"] != ACTION_MAP[action]:
            return False, "NATIVE_OPERATION_MAPPING_INVALID"
        if envelope["expected_native_state"] != REQUIRED_NATIVE_STATE[action]:
            return False, "EXPECTED_NATIVE_STATE_INVALID"
        _exact_int(envelope["expected_native_version"], "expected_native_version", minimum=1)
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
                return False, f"{name.upper()}_INVALID"
        if envelope["projector_identity_digest"] != build_identity().identity_digest:
            return False, "PROJECTOR_IDENTITY_MISMATCH"
        if envelope["would_dispatch"] is not True:
            return False, "WOULD_DISPATCH_INVALID"
        if envelope["executed"] is not False:
            return False, "HIDDEN_EXECUTION_AUTHORITY"
        _nonempty_text(envelope["idempotency_key"], "idempotency_key")
        expected_id = "ENV-" + _digest_json(
            {
                "request_digest": envelope["source_request_digest"],
                "source_observation_digest": envelope["source_observation_digest"],
            }
        )[:24].upper()
        if envelope["envelope_id"] != expected_id:
            return False, "ENVELOPE_ID_MISMATCH"
        expected_key = f"BAG-{int(envelope['request_id']):06d}-{str(envelope['source_request_digest'])[:16]}"
        if envelope["idempotency_key"] != expected_key:
            return False, "IDEMPOTENCY_KEY_MISMATCH"
        unsigned = {key: envelope[key] for key in ENVELOPE_KEYS if key != "envelope_digest"}
        if _digest_json(unsigned) != envelope["envelope_digest"]:
            return False, "ENVELOPE_DIGEST_MISMATCH"
    except ProjectionRejected as exc:
        return False, exc.reason
    return True, "VALID"


class BoundedActionProjector:
    """Produces a command envelope but cannot send or execute it."""

    def identity(self) -> ProjectorIdentity:
        return build_identity()

    def project(
        self,
        request: object,
        raw_event: object,
        raw_subject: object,
    ) -> BoundedCommandEnvelope:
        valid_request, reason = frozen_v03.validate_action_request(request)
        if not valid_request:
            raise ProjectionRejected(reason)
        event = _validate_observation_event(raw_event)
        subject = _validate_observed_subject(raw_subject)
        action = str(request.action)
        if action not in ACTION_MAP:
            raise ProjectionRejected("ACTION_UNSUPPORTED")
        if request.subject_id != event["subject_id"] or request.subject_id != subject["subject_id"]:
            raise ProjectionRejected("SUBJECT_BINDING_MISMATCH")
        if request.source_event_digest != event["observation_digest"]:
            raise ProjectionRejected("SOURCE_OBSERVATION_MISMATCH")
        if event["native_after_state"] != subject["native_state"]:
            raise ProjectionRejected("SOURCE_STATE_MISMATCH")
        if event["native_after_version"] != subject["native_version"]:
            raise ProjectionRejected("SOURCE_VERSION_MISMATCH")
        if event["observed_after_state"] != subject["observed_state"]:
            raise ProjectionRejected("OBSERVED_STATE_MISMATCH")
        if subject["native_state"] != REQUIRED_NATIVE_STATE[action]:
            raise ProjectionRejected("ACTION_STATE_NOT_ELIGIBLE")
        if subject["observed_state"] != REQUIRED_OBSERVED_STATE[action]:
            raise ProjectionRejected("ACTION_OBSERVED_STATE_NOT_ELIGIBLE")
        if request.expected_state_digest != frozen_v03.state_digest(subject["observed_state"]):
            raise ProjectionRejected("EXPECTED_STATE_DIGEST_MISMATCH")
        if request.current_epoch != subject["native_version"]:
            raise ProjectionRejected("REQUEST_EPOCH_MISMATCH")

        identity = self.identity()
        envelope_id = "ENV-" + _digest_json(
            {
                "request_digest": request.request_digest,
                "source_observation_digest": event["observation_digest"],
            }
        )[:24].upper()
        idempotency_key = f"BAG-{request.request_id:06d}-{request.request_digest[:16]}"
        unsigned = {
            "action": action,
            "authority_digest": request.authority_digest,
            "envelope_id": envelope_id,
            "executed": False,
            "expected_native_state": REQUIRED_NATIVE_STATE[action],
            "expected_native_version": int(subject["native_version"]),
            "governance_session_digest": request.governance_session_digest,
            "idempotency_key": idempotency_key,
            "native_operation": ACTION_MAP[action],
            "projector_identity_digest": identity.identity_digest,
            "request_id": request.request_id,
            "schema_version": SCHEMA_VERSION,
            "source_observation_digest": event["observation_digest"],
            "source_receipt_digest": event["source_receipt_digest"],
            "source_request_digest": request.request_digest,
            "subject_id": request.subject_id,
            "would_dispatch": True,
        }
        return BoundedCommandEnvelope(
            schema_version=SCHEMA_VERSION,
            envelope_id=envelope_id,
            request_id=request.request_id,
            action=action,
            subject_id=request.subject_id,
            native_operation=ACTION_MAP[action],
            expected_native_state=REQUIRED_NATIVE_STATE[action],
            expected_native_version=int(subject["native_version"]),
            source_observation_digest=str(event["observation_digest"]),
            source_receipt_digest=str(event["source_receipt_digest"]),
            source_request_digest=request.request_digest,
            governance_session_digest=request.governance_session_digest,
            authority_digest=request.authority_digest,
            projector_identity_digest=identity.identity_digest,
            would_dispatch=True,
            executed=False,
            idempotency_key=idempotency_key,
            envelope_digest=_digest_json(unsigned),
        )


if __name__ == "__main__":
    identity = build_identity()
    valid, reason = validate_identity(identity)
    print(f"Projector: {identity.projector_id} {identity.projector_version}")
    print(f"Schema: {identity.schema_version}")
    print(f"Mode: {identity.mode}")
    print(f"Execution authority: {identity.execution_authority}")
    print(f"Command transport entries: {len(identity.command_transport)}")
    print(f"Supported actions: {', '.join(identity.supported_actions)}")
    print(f"Identity digest: {identity.identity_digest}")
    print("BOUNDED ACTION PROJECTOR SELF-CHECK: PASS" if valid else f"BOUNDED ACTION PROJECTOR SELF-CHECK: FAIL:{reason}")
