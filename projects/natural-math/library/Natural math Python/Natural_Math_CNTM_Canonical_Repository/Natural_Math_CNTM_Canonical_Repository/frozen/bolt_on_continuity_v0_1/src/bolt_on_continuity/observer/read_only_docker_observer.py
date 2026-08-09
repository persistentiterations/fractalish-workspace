from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import subprocess
from typing import Any, Protocol, Sequence

CONTRACT_VERSION = "BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_1_STAGE_0"
SCHEMA_VERSION = "1"
ZERO_DIGEST = "sha256:" + ("0" * 64)

STATE_MAP = {
    "running": "RUNNING",
    "paused": "PAUSED",
    "exited": "EXITED",
    "restarting": "RESTARTING",
    "dead": "UNAVAILABLE",
    "created": "UNKNOWN",
}
HEALTH_MAP = {
    "healthy": "HEALTHY",
    "unhealthy": "UNHEALTHY",
    "starting": "STARTING",
    "none": "NOT_CONFIGURED",
    "": "NOT_CONFIGURED",
}

class ObservationRejected(ValueError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code

class ReadOnlyTransport(Protocol):
    def inspect_one(self, container_id: str) -> str: ...
    def events_for(self, container_id: str, since_epoch: int, until_epoch: int) -> Sequence[str]: ...
    def logs_for(self, container_id: str, since_epoch: int, max_bytes: int) -> bytes: ...

@dataclass(frozen=True)
class CollectionBounds:
    max_events: int = 100
    max_log_bytes: int = 65536
    max_evidence_age_seconds: int = 30
    max_future_skew_seconds: int = 5

    def validate(self) -> None:
        values = (self.max_events, self.max_log_bytes,
                  self.max_evidence_age_seconds, self.max_future_skew_seconds)
        if any(type(v) is not int or v < 0 for v in values):
            raise ValueError("bounds must be non-negative integers")
        if self.max_events == 0 or self.max_log_bytes == 0:
            raise ValueError("event and log bounds must be positive")

def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("floating-point values are not canonical")
    if isinstance(value, dict):
        for item in value.values():
            _reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_floats(item)

def canonical_json(value: Any) -> bytes:
    _reject_floats(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()

def bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()

def _is_sha256(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(ch in "0123456789abcdef" for ch in value[7:])
    )

class DockerCLIReadOnlyTransport:
    """Fixed read-only Docker CLI transport with no generic command method."""

    _READ_OPERATIONS = frozenset({"inspect", "events", "logs", "version"})

    def __init__(self, docker_executable: str = "docker", timeout_seconds: int = 10):
        if not docker_executable or any(ch in docker_executable for ch in "\r\n\0"):
            raise ValueError("invalid Docker executable")
        if type(timeout_seconds) is not int or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._docker_executable = docker_executable
        self._timeout_seconds = timeout_seconds

    @property
    def allowed_operations(self) -> frozenset[str]:
        return self._READ_OPERATIONS

    def inspect_one(self, container_id: str) -> str:
        self._validate_subject(container_id)
        return self._run_fixed(["inspect", "--type", "container", container_id]).decode("utf-8")

    def events_for(self, container_id: str, since_epoch: int, until_epoch: int) -> Sequence[str]:
        self._validate_subject(container_id)
        self._validate_epoch(since_epoch)
        self._validate_epoch(until_epoch)
        if until_epoch < since_epoch:
            raise ValueError("until precedes since")
        return self._run_fixed([
            "events", "--filter", f"container={container_id}",
            "--since", str(since_epoch), "--until", str(until_epoch),
            "--format", "{{json .}}"
        ]).decode("utf-8").splitlines()

    def logs_for(self, container_id: str, since_epoch: int, max_bytes: int) -> bytes:
        self._validate_subject(container_id)
        self._validate_epoch(since_epoch)
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        output = self._run_fixed(["logs", "--since", str(since_epoch), "--timestamps", container_id])
        if len(output) > max_bytes:
            raise ObservationRejected("LIMIT_EXCEEDED", "log output exceeded configured bound")
        return output

    def version(self) -> str:
        return self._run_fixed(["version", "--format", "{{json .}}"]).decode("utf-8")

    def _run_fixed(self, args: list[str]) -> bytes:
        if not args or args[0] not in self._READ_OPERATIONS:
            raise RuntimeError("non-read Docker operation rejected")
        try:
            completed = subprocess.run(
                [self._docker_executable, *args],
                shell=False,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self._timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ObservationRejected("TRANSPORT_FAILURE", str(exc)) from exc
        return completed.stdout

    @staticmethod
    def _validate_subject(container_id: str) -> None:
        if not isinstance(container_id, str) or not 12 <= len(container_id) <= 128:
            raise ValueError("container_id must be an immutable Docker identifier")
        if any(ch not in "0123456789abcdefABCDEF" for ch in container_id):
            raise ValueError("container_id must be hexadecimal")

    @staticmethod
    def _validate_epoch(value: int) -> None:
        if type(value) is not int or value < 0:
            raise ValueError("epoch must be a non-negative integer")

class ReadOnlyDockerObserver:
    def __init__(self, configured_container_id: str, configuration_digest: str,
                 bounds: CollectionBounds | None = None):
        DockerCLIReadOnlyTransport._validate_subject(configured_container_id)
        if not _is_sha256(configuration_digest):
            raise ValueError("configuration_digest must be sha256-prefixed")
        self.container_id = configured_container_id.lower()
        self.configuration_digest = configuration_digest
        self.bounds = bounds or CollectionBounds()
        self.bounds.validate()

    def collect(self, transport: ReadOnlyTransport, collection_sequence: int,
                collected_at_epoch: int) -> dict[str, Any]:
        self._validate_sequence_and_time(collection_sequence, collected_at_epoch)
        since = max(0, collected_at_epoch - self.bounds.max_evidence_age_seconds)
        return self.normalize_capture(
            raw_inspect=transport.inspect_one(self.container_id),
            raw_events=list(transport.events_for(self.container_id, since, collected_at_epoch)),
            raw_logs=transport.logs_for(self.container_id, since, self.bounds.max_log_bytes),
            collection_sequence=collection_sequence,
            collected_at_epoch=collected_at_epoch,
        )

    def normalize_capture(self, *, raw_inspect: str, raw_events: Sequence[str],
                          raw_logs: bytes, collection_sequence: int,
                          collected_at_epoch: int) -> dict[str, Any]:
        self._validate_sequence_and_time(collection_sequence, collected_at_epoch)
        if not isinstance(raw_logs, bytes):
            raise ObservationRejected("MALFORMED_EVENT", "raw logs must be bytes")
        if len(raw_logs) > self.bounds.max_log_bytes or len(raw_events) > self.bounds.max_events:
            raise ObservationRejected("LIMIT_EXCEEDED", "collection bound exceeded")

        inspect = self._parse_inspect(raw_inspect)
        events = self._parse_events(raw_events, collected_at_epoch)
        observed_id = inspect.get("Id")
        if not isinstance(observed_id, str):
            raise ObservationRejected("MALFORMED_INSPECT", "inspect Id missing")
        if observed_id.lower() != self.container_id:
            raise ObservationRejected("WRONG_SUBJECT", "inspect subject differs")

        state_obj = inspect.get("State")
        if not isinstance(state_obj, dict):
            raise ObservationRejected("MALFORMED_INSPECT", "inspect State missing")
        raw_state = state_obj.get("Status")
        if raw_state not in STATE_MAP:
            raise ObservationRejected("UNSUPPORTED_STATE", f"unsupported state {raw_state!r}")

        health = state_obj.get("Health")
        if health is None:
            raw_health = "none"
        elif isinstance(health, dict):
            raw_health = health.get("Status", "")
        else:
            raise ObservationRejected("MALFORMED_INSPECT", "Health must be an object")

        name = inspect.get("Name", "")
        if not isinstance(name, str):
            raise ObservationRejected("MALFORMED_INSPECT", "Name must be text")
        display_name = name[1:] if name.startswith("/") else name

        raw_capture = {
            "inspect": inspect,
            "events": events,
            "logs": {"byte_count": len(raw_logs), "digest": bytes_digest(raw_logs)},
        }
        raw_capture_digest = canonical_digest(raw_capture)
        normalized_body = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "container_id": self.container_id,
            "display_name": display_name,
            "collection_sequence": collection_sequence,
            "observed_state": STATE_MAP[raw_state],
            "health_state": HEALTH_MAP.get(raw_health, "UNKNOWN"),
            "collected_at_epoch": collected_at_epoch,
            "configuration_digest": self.configuration_digest,
            "event_count": len(events),
            "log_byte_count": len(raw_logs),
            "log_digest": bytes_digest(raw_logs),
            "raw_capture_digest": raw_capture_digest,
            "truncation": {"events_truncated": False, "logs_truncated": False},
        }
        normalized = {**normalized_body, "evidence_digest": canonical_digest(normalized_body)}
        receipt_body = {
            "schema_version": SCHEMA_VERSION,
            "receipt_type": "EVIDENCE_ACCEPTED",
            "subject_id": self.container_id,
            "collection_sequence": collection_sequence,
            "evidence_digest": normalized["evidence_digest"],
            "raw_capture_digest": raw_capture_digest,
            "previous_receipt_digest": ZERO_DIGEST,
        }
        receipt = {**receipt_body, "receipt_digest": canonical_digest(receipt_body)}
        return {"normalized_evidence": normalized, "receipt": receipt, "raw_capture": raw_capture}

    def replay(self, bundle: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(bundle, dict) or set(bundle) != {"normalized_evidence", "receipt", "raw_capture"}:
            raise ObservationRejected("TAMPERED_EVIDENCE", "capture bundle differs")
        normalized = bundle["normalized_evidence"]
        raw_capture = bundle["raw_capture"]
        if not isinstance(normalized, dict) or not isinstance(raw_capture, dict):
            raise ObservationRejected("TAMPERED_EVIDENCE", "capture bundle malformed")

        expected_raw_digest = canonical_digest(raw_capture)
        if expected_raw_digest != normalized.get("raw_capture_digest"):
            raise ObservationRejected("TAMPERED_EVIDENCE", "raw capture digest differs")

        normalized_body = dict(normalized)
        claimed_evidence_digest = normalized_body.pop("evidence_digest", None)
        if canonical_digest(normalized_body) != claimed_evidence_digest:
            raise ObservationRejected("TAMPERED_EVIDENCE", "evidence digest differs")

        receipt_body = dict(bundle["receipt"])
        claimed_receipt_digest = receipt_body.pop("receipt_digest", None)
        if canonical_digest(receipt_body) != claimed_receipt_digest:
            raise ObservationRejected("TAMPERED_EVIDENCE", "receipt digest differs")
        if receipt_body.get("evidence_digest") != claimed_evidence_digest:
            raise ObservationRejected("TAMPERED_EVIDENCE", "receipt evidence binding differs")
        if receipt_body.get("raw_capture_digest") != expected_raw_digest:
            raise ObservationRejected("TAMPERED_EVIDENCE", "receipt raw binding differs")

        return {"replay_pass": True, "evidence_digest": claimed_evidence_digest,
                "receipt_digest": claimed_receipt_digest}

    def _parse_inspect(self, raw_inspect: str) -> dict[str, Any]:
        if not isinstance(raw_inspect, str):
            raise ObservationRejected("MALFORMED_INSPECT", "inspect must be text")
        try:
            value = json.loads(raw_inspect)
        except json.JSONDecodeError as exc:
            raise ObservationRejected("MALFORMED_INSPECT", str(exc)) from exc
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
            raise ObservationRejected("AMBIGUOUS_SUBJECT", "inspect must contain exactly one object")
        return value[0]

    def _parse_events(self, raw_events: Sequence[str], collected_at_epoch: int) -> list[dict[str, Any]]:
        parsed = []
        previous_time = None
        for index, line in enumerate(raw_events):
            if not isinstance(line, str):
                raise ObservationRejected("MALFORMED_EVENT", f"event {index} is not text")
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ObservationRejected("MALFORMED_EVENT", f"event {index}: {exc}") from exc
            if not isinstance(event, dict):
                raise ObservationRejected("MALFORMED_EVENT", f"event {index} not an object")
            actor = event.get("Actor")
            if not isinstance(actor, dict) or not isinstance(actor.get("ID"), str):
                raise ObservationRejected("MALFORMED_EVENT", f"event {index} actor missing")
            if actor["ID"].lower() != self.container_id:
                raise ObservationRejected("WRONG_SUBJECT", f"event {index} subject differs")
            event_time = event.get("time")
            if type(event_time) is not int:
                raise ObservationRejected("MALFORMED_EVENT", f"event {index} time not integer")
            if event_time < collected_at_epoch - self.bounds.max_evidence_age_seconds:
                raise ObservationRejected("STALE_EVIDENCE", f"event {index} stale")
            if event_time > collected_at_epoch + self.bounds.max_future_skew_seconds:
                raise ObservationRejected("FUTURE_EVIDENCE", f"event {index} future")
            if previous_time is not None and event_time < previous_time:
                raise ObservationRejected("MALFORMED_EVENT", "events out of order")
            previous_time = event_time
            parsed.append({"type": event.get("Type", ""), "action": event.get("Action", ""),
                           "actor_id": actor["ID"].lower(), "time": event_time})
        return parsed

    @staticmethod
    def _validate_sequence_and_time(sequence: int, epoch: int) -> None:
        if type(sequence) is not int or sequence < 0:
            raise ValueError("collection_sequence must be non-negative integer")
        if type(epoch) is not int or epoch < 0:
            raise ValueError("collected_at_epoch must be non-negative integer")
