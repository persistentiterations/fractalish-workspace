"""Explicit local retention of verified Stage 1 observations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .observation import ObservationRecord, build_record
from .observer import ContainerObserver
from .receipt import Receipt, generate_receipt

RETAINED_SCHEMA = "bolt-on-continuity-control-room-retained-observations/v1"
REQUIRED_ENTRY_FIELDS = {"observation_index", "observation_schema", "observation_receipt_id", "container_id", "observed_at", "source_interface"}
FROZEN_ROOT = Path(__file__).resolve().parents[4] / "frozen"

class RetentionError(ValueError):
    pass

@dataclass(frozen=True)
class RetainedObservation:
    observation_index: int
    observation_schema: str
    observation_receipt_id: str
    container_id: str | None
    observed_at: str
    source_interface: str

@dataclass(frozen=True)
class RetainedObservations:
    schema: str
    subject_selector: str
    observations: tuple[RetainedObservation, ...]

    def as_dict(self) -> dict[str, object]:
        return {"schema": self.schema, "subject_selector": self.subject_selector, "observations": [asdict(item) for item in self.observations]}

def retain_verified(records: list[tuple[ObservationRecord, Receipt]]) -> RetainedObservations:
    if len(records) < 2:
        raise RetentionError("at least two observations are required")
    subject = records[0][0].subject
    retained: list[RetainedObservation] = []
    for index, (record, receipt) in enumerate(records, start=1):
        if record.subject != subject:
            raise RetentionError("exactly one subject selector is required")
        if receipt != generate_receipt(record):
            raise RetentionError("unverified observation receipt")
        retained.append(RetainedObservation(index, record.schema, receipt.receipt_id, record.canonical_fields.container_id, record.observed_at, record.source_interface))
    return RetainedObservations(RETAINED_SCHEMA, subject, tuple(retained))

def capture_and_retain(observer: ContainerObserver, subject: str, destination: Path, count: int = 2) -> RetainedObservations:
    if count < 2:
        raise RetentionError("at least two observations are required")
    if destination.resolve().is_relative_to(FROZEN_ROOT.resolve()):
        raise RetentionError("retained evidence destination must not be inside frozen")
    records: list[tuple[ObservationRecord, Receipt]] = []
    for _ in range(count):
        raw = observer.inspect_one(subject)
        record = build_record(subject, raw, observer.source_interface, observer.source_command(subject))
        records.append((record, generate_receipt(record)))
    document = retain_verified(records)
    destination.write_text(json.dumps(document.as_dict(), sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return document

def load_retained(source: Path) -> RetainedObservations:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"schema", "subject_selector", "observations"}:
        raise RetentionError("invalid retained document")
    entries = payload["observations"]
    if not isinstance(entries, list):
        raise RetentionError("invalid observations array")
    observations = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != REQUIRED_ENTRY_FIELDS:
            raise RetentionError("invalid retained observation entry")
        observations.append(RetainedObservation(**entry))
    return RetainedObservations(payload["schema"], payload["subject_selector"], tuple(observations))
