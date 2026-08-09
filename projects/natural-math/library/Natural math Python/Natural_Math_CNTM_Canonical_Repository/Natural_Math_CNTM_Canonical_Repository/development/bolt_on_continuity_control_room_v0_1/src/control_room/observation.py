"""Canonicalize the bounded subset of a Docker container inspection."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

SCHEMA = "bolt-on-continuity-control-room-observation/v1"

def _value(value: object) -> str | bool | None:
    return value if isinstance(value, bool) else value if isinstance(value, str) and value else None

@dataclass(frozen=True)
class CanonicalObservation:
    container_id: str | None
    container_name: str | None
    configured_image: str | None
    resolved_image: str | None
    state: str | None
    running: bool | None
    created_at: str | None
    started_at: str | None
    def as_dict(self) -> dict[str, object]:
        return asdict(self)

@dataclass(frozen=True)
class ObservationRecord:
    schema: str
    subject: str
    source_interface: str
    source_command: str
    observed_at: str
    result: str
    canonical_fields: CanonicalObservation

def canonicalize(raw: Mapping[str, Any]) -> CanonicalObservation:
    config = raw.get("Config") if isinstance(raw.get("Config"), Mapping) else {}
    state = raw.get("State") if isinstance(raw.get("State"), Mapping) else {}
    name = _value(raw.get("Name"))
    return CanonicalObservation(_value(raw.get("Id")), name.lstrip("/") if isinstance(name, str) else None, _value(config.get("Image")), _value(raw.get("Image")), _value(state.get("Status")), _value(state.get("Running")), _value(raw.get("Created")), _value(state.get("StartedAt")))

def build_record(subject: str, raw: Mapping[str, Any], source_interface: str, source_command: str, observed_at: str | None = None) -> ObservationRecord:
    timestamp = observed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return ObservationRecord(SCHEMA, subject, source_interface, source_command, timestamp, "observed", canonicalize(raw))
