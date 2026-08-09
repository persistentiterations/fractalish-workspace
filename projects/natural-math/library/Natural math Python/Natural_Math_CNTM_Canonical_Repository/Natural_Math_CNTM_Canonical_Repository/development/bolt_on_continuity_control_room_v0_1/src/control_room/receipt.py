"""Deterministic receipt generation for one observation record."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from .observation import ObservationRecord

RECEIPT_SCHEMA = "bolt-on-continuity-control-room-receipt/v1"
def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
@dataclass(frozen=True)
class Receipt:
    schema: str
    receipt_id: str
    digest_algorithm: str
    digest_input: dict[str, object]
def generate_receipt(record: ObservationRecord) -> Receipt:
    digest_input = {"schema": RECEIPT_SCHEMA, "subject": record.subject, "source_interface": record.source_interface, "canonical_fields": record.canonical_fields.as_dict(), "result": record.result}
    digest = hashlib.sha256(canonical_bytes(digest_input)).hexdigest()
    return Receipt(RECEIPT_SCHEMA, f"sha256:{digest}", "SHA-256", digest_input)
