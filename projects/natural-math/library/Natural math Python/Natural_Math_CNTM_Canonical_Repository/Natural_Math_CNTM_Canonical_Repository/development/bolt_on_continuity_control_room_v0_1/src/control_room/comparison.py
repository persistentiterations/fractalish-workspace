"""Full-ID-only continuity classification and deterministic comparison receipt."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from .receipt import canonical_bytes
from .retention import RETAINED_SCHEMA, RetainedObservation, RetainedObservations

COMPARISON_SCHEMA = "bolt-on-continuity-control-room-comparison-receipt/v1"
FULL_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")

@dataclass(frozen=True)
class ComparisonResult:
    classification: str
    reason: str | None
    ordered_observations: tuple[RetainedObservation, ...]

@dataclass(frozen=True)
class ComparisonReceipt:
    schema: str
    receipt_id: str
    digest_algorithm: str
    digest_input: dict[str, object]

def compare_identity(document: RetainedObservations) -> ComparisonResult:
    if document.schema != RETAINED_SCHEMA or not isinstance(document.subject_selector, str) or not document.subject_selector:
        return ComparisonResult("INDETERMINATE", "invalid_record", ())
    ordered = tuple(sorted(document.observations, key=lambda item: item.observation_index))
    indices = [item.observation_index for item in ordered]
    if len(ordered) < 2:
        return ComparisonResult("INDETERMINATE", "insufficient_observations", ordered)
    if indices != list(range(1, len(ordered) + 1)):
        return ComparisonResult("INDETERMINATE", "invalid_order", ordered)
    if any(item.observation_schema != "bolt-on-continuity-control-room-observation/v1" or not re.fullmatch(r"sha256:[0-9a-f]{64}", item.observation_receipt_id) for item in ordered):
        return ComparisonResult("INDETERMINATE", "unverified_observation_receipt", ordered)
    if any(not isinstance(item.container_id, str) or not FULL_CONTAINER_ID.fullmatch(item.container_id) for item in ordered):
        return ComparisonResult("INDETERMINATE", "missing_identity", ordered)
    if len({item.container_id for item in ordered}) != 1:
        return ComparisonResult("INDETERMINATE", "identity_mismatch_out_of_scope", ordered)
    return ComparisonResult("SAME_SUBJECT", None, ordered)

def generate_comparison_receipt(document: RetainedObservations, result: ComparisonResult | None = None) -> ComparisonReceipt:
    result = result or compare_identity(document)
    digest_input = {"schema": COMPARISON_SCHEMA, "retained_observation_schema": RETAINED_SCHEMA, "subject_selector": document.subject_selector, "observations": [{"observation_index": item.observation_index, "container_id": item.container_id, "observation_receipt_id": item.observation_receipt_id} for item in result.ordered_observations], "classification": result.classification, "reason": result.reason}
    digest = hashlib.sha256(canonical_bytes(digest_input)).hexdigest()
    return ComparisonReceipt(COMPARISON_SCHEMA, f"sha256:{digest}", "SHA-256", digest_input)
