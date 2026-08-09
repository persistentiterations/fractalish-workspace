"""Bounded, operator-confirmed running-to-stopped evidence."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json, re
from pathlib import Path
from .observation import ObservationRecord, build_record
from .observer import ContainerObserver
from .receipt import canonical_bytes, generate_receipt
from .retention import FROZEN_ROOT, RetainedObservation

TRANSITION_SCHEMA = "bolt-on-continuity-control-room-state-transition/v1"
RECEIPT_SCHEMA = "bolt-on-continuity-control-room-state-transition-receipt/v1"
FULL_ID = re.compile(r"^[0-9a-f]{64}$")

class TransitionError(ValueError): pass
@dataclass(frozen=True)
class TransitionObservation:
    retained: RetainedObservation
    canonical_fields: dict[str, object]
@dataclass(frozen=True)
class TransitionEvidence:
    schema: str
    subject_selector: str
    operator_stop_confirmed: bool
    earlier: TransitionObservation
    later: TransitionObservation | None
@dataclass(frozen=True)
class TransitionResult:
    classification: str
    reason: str | None
@dataclass(frozen=True)
class TransitionReceipt:
    schema: str
    receipt_id: str
    digest_input: dict[str, object]

def _entry(record: ObservationRecord, index: int) -> TransitionObservation:
    receipt = generate_receipt(record)
    retained = RetainedObservation(index, record.schema, receipt.receipt_id, record.canonical_fields.container_id, record.observed_at, record.source_interface)
    return TransitionObservation(retained, record.canonical_fields.as_dict())
def _capture(observer: ContainerObserver, subject: str, index: int) -> TransitionObservation:
    return _entry(build_record(subject, observer.inspect_one(subject), observer.source_interface, observer.source_command(subject)), index)
def _document_dict(evidence: TransitionEvidence) -> dict[str, object]:
    def value(item: TransitionObservation | None) -> object:
        return None if item is None else {"retained": asdict(item.retained), "canonical_fields": item.canonical_fields}
    return {"schema": evidence.schema, "subject_selector": evidence.subject_selector, "operator_stop_confirmed": evidence.operator_stop_confirmed, "earlier": value(evidence.earlier), "later": value(evidence.later)}
def save(evidence: TransitionEvidence, destination: Path) -> None:
    if destination.resolve().is_relative_to(FROZEN_ROOT.resolve()): raise TransitionError("transition evidence destination must not be inside frozen")
    destination.write_text(json.dumps(_document_dict(evidence), sort_keys=True, separators=(",", ":")), encoding="utf-8")
def load(source: Path) -> TransitionEvidence:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"schema", "subject_selector", "operator_stop_confirmed", "earlier", "later"}: raise TransitionError("invalid transition evidence")
    def parse(item: object) -> TransitionObservation | None:
        if item is None: return None
        if not isinstance(item, dict) or set(item) != {"retained", "canonical_fields"}: raise TransitionError("invalid transition observation")
        return TransitionObservation(RetainedObservation(**item["retained"]), item["canonical_fields"])
    earlier, later = parse(payload["earlier"]), parse(payload["later"])
    if earlier is None: raise TransitionError("missing earlier observation")
    return TransitionEvidence(payload["schema"], payload["subject_selector"], payload["operator_stop_confirmed"], earlier, later)
def capture_running(observer: ContainerObserver, subject: str, destination: Path) -> TransitionEvidence:
    earlier = _capture(observer, subject, 1)
    if earlier.canonical_fields.get("state") != "running" or earlier.canonical_fields.get("running") is not True: raise TransitionError("first observation is not running")
    evidence = TransitionEvidence(TRANSITION_SCHEMA, subject, False, earlier, None); save(evidence, destination); return evidence
def confirm_manual_stop(evidence: TransitionEvidence, destination: Path) -> TransitionEvidence:
    if evidence.later is not None: raise TransitionError("later observation already retained")
    confirmed = TransitionEvidence(evidence.schema, evidence.subject_selector, True, evidence.earlier, None); save(confirmed, destination); return confirmed
def capture_stopped(observer: ContainerObserver, evidence: TransitionEvidence, destination: Path) -> TransitionEvidence:
    if not evidence.operator_stop_confirmed: raise TransitionError("manual stop confirmation is required")
    later = _capture(observer, evidence.subject_selector, 2)
    captured = TransitionEvidence(evidence.schema, evidence.subject_selector, True, evidence.earlier, later); save(captured, destination); return captured
def _valid(item: TransitionObservation, subject: str, index: int) -> bool:
    r, fields = item.retained, item.canonical_fields
    expected = hashlib.sha256(canonical_bytes({"schema":"bolt-on-continuity-control-room-receipt/v1","subject":subject,"source_interface":r.source_interface,"canonical_fields":fields,"result":"observed"})).hexdigest()
    return r.observation_index == index and r.container_id == fields.get("container_id") and r.observation_receipt_id == f"sha256:{expected}"
def classify(evidence: TransitionEvidence) -> TransitionResult:
    if evidence.schema != TRANSITION_SCHEMA or not evidence.operator_stop_confirmed: return TransitionResult("INDETERMINATE", "operator_stop_unconfirmed")
    if evidence.later is None: return TransitionResult("INDETERMINATE", "insufficient_observations")
    if not _valid(evidence.earlier, evidence.subject_selector, 1) or not _valid(evidence.later, evidence.subject_selector, 2): return TransitionResult("INDETERMINATE", "unverified_observation_receipt")
    first, second = evidence.earlier.canonical_fields, evidence.later.canonical_fields
    if not isinstance(first.get("container_id"), str) or not FULL_ID.fullmatch(first["container_id"]) or not isinstance(second.get("container_id"), str) or not FULL_ID.fullmatch(second["container_id"]): return TransitionResult("INDETERMINATE", "missing_identity")
    if first["container_id"] != second["container_id"]: return TransitionResult("INDETERMINATE", "identity_mismatch_out_of_scope")
    if first.get("state") != "running" or first.get("running") is not True or second.get("state") != "exited" or second.get("running") is not False: return TransitionResult("INDETERMINATE", "unsupported_state_transition")
    return TransitionResult("SAME_SUBJECT_STOPPED", None)
def receipt(evidence: TransitionEvidence, result: TransitionResult | None = None) -> TransitionReceipt:
    result = result or classify(evidence)
    def item(observation: TransitionObservation | None) -> object:
        if observation is None: return None
        r, f = observation.retained, observation.canonical_fields
        return {"observation_index":r.observation_index,"container_id":r.container_id,"observation_receipt_id":r.observation_receipt_id,"state":f.get("state"),"running":f.get("running")}
    value={"schema":RECEIPT_SCHEMA,"transition_schema":TRANSITION_SCHEMA,"subject_selector":evidence.subject_selector,"earlier":item(evidence.earlier),"later":item(evidence.later),"classification":result.classification,"reason":result.reason}
    return TransitionReceipt(RECEIPT_SCHEMA, "sha256:"+hashlib.sha256(canonical_bytes(value)).hexdigest(), value)
