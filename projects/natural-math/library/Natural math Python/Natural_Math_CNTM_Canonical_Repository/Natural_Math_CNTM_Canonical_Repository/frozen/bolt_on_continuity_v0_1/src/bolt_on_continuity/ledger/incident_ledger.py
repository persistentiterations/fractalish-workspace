from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1"
ZERO_DIGEST = "sha256:" + "0"*64
EVENT_TYPES = {
    "INCIDENT_OPENED",
    "OBSERVATION_RECORDED",
    "STATE_CHANGED",
    "INCIDENT_NOTE",
    "INCIDENT_CLOSED",
}

class LedgerRejected(ValueError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code

def _no_floats(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("floating-point values are not canonical")
    if isinstance(value, dict):
        for item in value.values(): _no_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value: _no_floats(item)

def canonical_json(value: Any) -> bytes:
    _no_floats(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()

def valid_digest(value: str) -> bool:
    return isinstance(value, str) and len(value)==71 and value.startswith("sha256:") and all(c in "0123456789abcdef" for c in value[7:])

@dataclass
class IncidentLedger:
    incident_id: str
    container_id: str
    configuration_digest: str

    def __post_init__(self):
        if not isinstance(self.incident_id, str) or len(self.incident_id) < 8:
            raise ValueError("incident_id too short")
        if not isinstance(self.container_id, str) or not 12 <= len(self.container_id) <= 128:
            raise ValueError("container_id invalid")
        if any(c not in "0123456789abcdefABCDEF" for c in self.container_id):
            raise ValueError("container_id must be hexadecimal")
        self.container_id = self.container_id.lower()
        if not valid_digest(self.configuration_digest):
            raise ValueError("configuration_digest invalid")
        self._entries: list[dict[str, Any]] = []

    @property
    def entries(self) -> tuple[dict[str, Any], ...]:
        return tuple(json.loads(json.dumps(e)) for e in self._entries)

    @property
    def closed(self) -> bool:
        return bool(self._entries and self._entries[-1]["event_type"] == "INCIDENT_CLOSED")

    def append(self, event_type: str, recorded_at_epoch: int,
               evidence_digest: str, payload: dict[str, Any]) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise LedgerRejected("UNSUPPORTED_EVENT", "event type unsupported")
        if type(recorded_at_epoch) is not int or recorded_at_epoch < 0:
            raise LedgerRejected("MALFORMED_ENTRY", "recorded time invalid")
        if not valid_digest(evidence_digest):
            raise LedgerRejected("MALFORMED_ENTRY", "evidence digest invalid")
        if not isinstance(payload, dict):
            raise LedgerRejected("MALFORMED_ENTRY", "payload must be object")
        _no_floats(payload)
        if self.closed:
            raise LedgerRejected("INCIDENT_CLOSED", "entry after closure")
        if not self._entries and event_type != "INCIDENT_OPENED":
            raise LedgerRejected("OPEN_REQUIRED", "first entry must open incident")
        if self._entries and event_type == "INCIDENT_OPENED":
            raise LedgerRejected("DUPLICATE_OPEN", "incident already opened")
        if self._entries and recorded_at_epoch < self._entries[-1]["recorded_at_epoch"]:
            raise LedgerRejected("TIME_REVERSED", "time decreased")

        body = {
            "schema_version": SCHEMA_VERSION,
            "incident_id": self.incident_id,
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "sequence": len(self._entries),
            "event_type": event_type,
            "recorded_at_epoch": recorded_at_epoch,
            "evidence_digest": evidence_digest,
            "payload": payload,
            "previous_entry_digest": self._entries[-1]["entry_digest"] if self._entries else ZERO_DIGEST,
        }
        entry = {**body, "entry_digest": digest(body)}
        self._entries.append(entry)
        return json.loads(json.dumps(entry))

    def export(self) -> dict[str, Any]:
        if not self._entries:
            raise LedgerRejected("EMPTY_LEDGER", "cannot export empty ledger")
        body = {
            "schema_version": SCHEMA_VERSION,
            "incident_id": self.incident_id,
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "entry_count": len(self._entries),
            "closed": self.closed,
            "entries": list(self.entries),
            "terminal_entry_digest": self._entries[-1]["entry_digest"],
        }
        return {**body, "export_digest": digest(body)}

    @classmethod
    def replay_export(cls, export: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(export, dict):
            raise LedgerRejected("MALFORMED_EXPORT", "export must be object")
        required = {"schema_version","incident_id","container_id","configuration_digest",
                    "entry_count","closed","entries","terminal_entry_digest","export_digest"}
        if set(export) != required:
            raise LedgerRejected("MALFORMED_EXPORT", "export fields differ")
        body = dict(export); claimed_export_digest = body.pop("export_digest")
        if digest(body) != claimed_export_digest:
            raise LedgerRejected("TAMPERED_EXPORT", "export digest differs")
        entries = export["entries"]
        if not isinstance(entries, (list, tuple)) or not entries:
            raise LedgerRejected("MALFORMED_EXPORT", "entries missing")
        if export["entry_count"] != len(entries):
            raise LedgerRejected("COUNT_MISMATCH", "entry count differs")

        ledger = cls(export["incident_id"], export["container_id"], export["configuration_digest"])
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise LedgerRejected("MALFORMED_ENTRY", "entry not object")
            expected_keys = {"schema_version","incident_id","container_id","configuration_digest",
                             "sequence","event_type","recorded_at_epoch","evidence_digest","payload",
                             "previous_entry_digest","entry_digest"}
            if set(entry) != expected_keys:
                raise LedgerRejected("MALFORMED_ENTRY", "entry fields differ")
            body = dict(entry); claimed = body.pop("entry_digest")
            if digest(body) != claimed:
                raise LedgerRejected("TAMPERED_ENTRY", f"entry {index} digest differs")
            if entry["sequence"] != index:
                raise LedgerRejected("SEQUENCE_MISMATCH", f"entry {index} sequence differs")
            if entry["incident_id"] != ledger.incident_id:
                raise LedgerRejected("INCIDENT_MISMATCH", "incident differs")
            if entry["container_id"] != ledger.container_id:
                raise LedgerRejected("SUBJECT_MISMATCH", "container differs")
            if entry["configuration_digest"] != ledger.configuration_digest:
                raise LedgerRejected("CONFIGURATION_MISMATCH", "configuration differs")
            expected_previous = ledger._entries[-1]["entry_digest"] if ledger._entries else ZERO_DIGEST
            if entry["previous_entry_digest"] != expected_previous:
                raise LedgerRejected("CHAIN_MISMATCH", "previous digest differs")
            reproduced = ledger.append(entry["event_type"], entry["recorded_at_epoch"],
                                       entry["evidence_digest"], entry["payload"])
            if reproduced != entry:
                raise LedgerRejected("REPLAY_MISMATCH", "reproduced entry differs")

        if export["terminal_entry_digest"] != ledger._entries[-1]["entry_digest"]:
            raise LedgerRejected("TERMINAL_MISMATCH", "terminal digest differs")
        if export["closed"] != ledger.closed:
            raise LedgerRejected("CLOSURE_MISMATCH", "closed flag differs")
        return {
            "replay_pass": True,
            "incident_id": ledger.incident_id,
            "entry_count": len(ledger._entries),
            "closed": ledger.closed,
            "terminal_entry_digest": ledger._entries[-1]["entry_digest"],
            "export_digest": claimed_export_digest,
        }
