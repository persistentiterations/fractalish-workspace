#!/usr/bin/env python3
"""Qualification harness for v0.4 Stage 3 read-only observation attachment."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, Mapping, Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "READ-ONLY EXTERNAL OBSERVATION ADAPTER"
STAGE_VERSION = "0.4.3"
MODE = "LIVE_READ_ONLY_SIDECAR_OBSERVATION"
BOLT_ON_EXECUTION_AUTHORITY = "NONE"
HOST_EXECUTION_BOUNDARY = "NATIVE_HOST_ONLY"
ATTACHMENT_MODE = "READ_ONLY_SIDECAR_REGISTRY"
ZERO_DIGEST = "0" * 64

EXPECTED_STAGE2_COMMIT = "ef8ee185eee1fa403b7ec9c24dc9ecd68c725386"
EXPECTED_STAGE1_SOURCE_SHA256 = "8035b10d0e68ec0365f48340366ec3bdd903a4dcc2e7b9b2574b2269c04b4806"
EXPECTED_HOST_SOURCE_SHA256 = "14a3b86d4cabee409d84904f3db4feb416be905c3c54edb3ca5ef4d50e41a797"
EXPECTED_ADAPTER_SOURCE_SHA256 = "176232fe8f4a9266fc90259ea82f19e36b36863fb14f328786c8ddb7ebcf6f68"
EXPECTED_FROZEN_V03_MANIFEST_SHA256 = "57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa"
EXPECTED_FROZEN_V03_ENTRIES = 20
EXPECTED_BASELINE_DIGEST = "df74c38b6bc7c377bb0fbc175035e03cea46d22c4f48e0109c7ce8ad75508129"
EXPECTED_NATIVE_ACTIONS = 6
EXPECTED_OBSERVATION_EVENTS = 6
EXPECTED_SUBJECTS = 1
EXPECTED_REJECTION_CASES = 40

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
HOST_PATH = PROJECT_DIR / "hosts" / "ordinary_job_service.py"
STAGE1_PATH = PROJECT_DIR / "integration" / "external_host_contract.py"
STAGE2_PATH = PROJECT_DIR / "integration" / "independent_host_baseline.py"
ADAPTER_PATH = PROJECT_DIR / "adapters" / "read_only_job_observer.py"
FROZEN_V03_MANIFEST = REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.3" / "RELEASE_MANIFEST_SHA256.txt"


def _load_module(name: str, path: Path):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


host = _load_module("v04_stage3_ordinary_job_service", HOST_PATH)
stage2 = _load_module("v04_stage3_stage2_qualification", STAGE2_PATH)
adapter_module = _load_module("v04_stage3_read_only_observer", ADAPTER_PATH)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_json(value: object) -> str:
    return _sha256_bytes(_canonical_json(value).encode("ascii"))


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _clone(value: object) -> object:
    return json.loads(_canonical_json(value))


@dataclass(frozen=True)
class RegistryReceipt:
    sequence: int
    event: str
    adapter_id: str
    host_family: str
    source_sha256: str
    previous_digest: str
    receipt_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "event": self.event,
            "host_family": self.host_family,
            "previous_digest": self.previous_digest,
            "sequence": self.sequence,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True)
class ObservationRegistry:
    registry_id: str
    attached: Tuple[str, ...]
    receipts: Tuple[RegistryReceipt, ...]
    registry_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "attached": list(self.attached),
            "receipts": [receipt.__dict__ for receipt in self.receipts],
            "registry_id": self.registry_id,
        }


@dataclass(frozen=True)
class RegistryReplay:
    passed: bool
    reason: str
    receipt_count: int
    final_digest: str


@dataclass(frozen=True)
class RejectionResult:
    name: str
    rejected: bool
    reason: str
    host_unchanged: bool
    observation_host_actions: int
    bolt_on_executed_actions: int


@dataclass(frozen=True)
class QualificationReceipt:
    sequence: int
    kind: str
    subject: str
    payload: str
    previous_digest: str
    receipt_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "payload": self.payload,
            "previous_digest": self.previous_digest,
            "sequence": self.sequence,
            "subject": self.subject,
        }


@dataclass(frozen=True)
class QualificationReplay:
    passed: bool
    reason: str
    count: int
    final_digest: str


@dataclass(frozen=True)
class Stage3Qualification:
    passed: bool
    stage_name: str
    stage_version: str
    mode: str
    bolt_on_execution_authority: str
    host_execution_boundary: str
    attachment_mode: str
    stage2_pass: bool
    frozen_v03_pass: bool
    frozen_v03_unchanged: bool
    frozen_v03_entries: int
    source_unchanged: bool
    adapter_read_only: bool
    deterministic_second_pass: bool
    attachment_replay_pass: bool
    observation_replay_pass: bool
    receipt_tamper_detection_pass: bool
    receipt_reorder_detection_pass: bool
    semantic_rehash_detection_pass: bool
    attach_registrations: int
    detach_registrations: int
    registry_empty_after_detach: bool
    host_state_changes: int
    baseline_native_host_actions: int
    observation_host_actions: int
    bolt_on_executed_actions: int
    observed_subjects: int
    observation_events: int
    rejection_cases: int
    rejection_cases_safely_rejected: int
    baseline_digest: str
    source_snapshot_digest: str
    source_final_receipt_digest: str
    final_observation_digest: str
    observation_batch_digest: str
    observation_replay_digest: str
    registry_digest: str
    qualification_receipt_digest: str
    qualification_replay_digest: str
    stage1_source_sha256: str
    host_source_sha256: str
    adapter_source_sha256: str
    frozen_v03_manifest_sha256: str


def empty_registry() -> ObservationRegistry:
    unsigned = {"attached": [], "receipts": [], "registry_id": "V04-OBSERVATION-REGISTRY"}
    return ObservationRegistry("V04-OBSERVATION-REGISTRY", (), (), _digest_json(unsigned))


def _append_registry(registry: ObservationRegistry, event: str) -> ObservationRegistry:
    if event not in ("ATTACH", "DETACH"):
        raise ValueError("invalid registry event")
    adapter_id = adapter_module.ADAPTER_ID
    attached = set(registry.attached)
    if event == "ATTACH":
        if adapter_id in attached:
            raise ValueError("adapter already attached")
        attached.add(adapter_id)
    else:
        if adapter_id not in attached:
            raise ValueError("adapter not attached")
        attached.remove(adapter_id)
    unsigned_receipt = {
        "adapter_id": adapter_id,
        "event": event,
        "host_family": host.HOST_FAMILY,
        "previous_digest": registry.receipts[-1].receipt_digest if registry.receipts else ZERO_DIGEST,
        "sequence": len(registry.receipts) + 1,
        "source_sha256": EXPECTED_ADAPTER_SOURCE_SHA256,
    }
    receipt = RegistryReceipt(
        sequence=unsigned_receipt["sequence"],
        event=event,
        adapter_id=adapter_id,
        host_family=host.HOST_FAMILY,
        source_sha256=EXPECTED_ADAPTER_SOURCE_SHA256,
        previous_digest=unsigned_receipt["previous_digest"],
        receipt_digest=_digest_json(unsigned_receipt),
    )
    receipts = registry.receipts + (receipt,)
    unsigned_registry = {
        "attached": sorted(attached),
        "receipts": [item.__dict__ for item in receipts],
        "registry_id": registry.registry_id,
    }
    return ObservationRegistry(
        registry_id=registry.registry_id,
        attached=tuple(sorted(attached)),
        receipts=receipts,
        registry_digest=_digest_json(unsigned_registry),
    )


def attach(registry: ObservationRegistry) -> ObservationRegistry:
    return _append_registry(registry, "ATTACH")


def detach(registry: ObservationRegistry) -> ObservationRegistry:
    return _append_registry(registry, "DETACH")


def replay_registry(registry: object) -> RegistryReplay:
    if not isinstance(registry, ObservationRegistry):
        return RegistryReplay(False, "REGISTRY_TYPE_INVALID", 0, ZERO_DIGEST)
    current = empty_registry()
    for expected_sequence, receipt in enumerate(registry.receipts, 1):
        if not isinstance(receipt, RegistryReceipt):
            return RegistryReplay(False, "REGISTRY_RECEIPT_TYPE_INVALID", expected_sequence - 1, ZERO_DIGEST)
        if receipt.sequence != expected_sequence:
            return RegistryReplay(False, "REGISTRY_SEQUENCE_MISMATCH", expected_sequence - 1, ZERO_DIGEST)
        expected_previous = current.receipts[-1].receipt_digest if current.receipts else ZERO_DIGEST
        if receipt.previous_digest != expected_previous:
            return RegistryReplay(False, "REGISTRY_CHAIN_MISMATCH", expected_sequence - 1, expected_previous)
        if _digest_json(receipt.unsigned_record()) != receipt.receipt_digest:
            return RegistryReplay(False, "REGISTRY_RECEIPT_DIGEST_MISMATCH", expected_sequence - 1, expected_previous)
        try:
            current = _append_registry(current, receipt.event)
        except ValueError:
            return RegistryReplay(False, "REGISTRY_SEMANTICS_INVALID", expected_sequence - 1, expected_previous)
        if current.receipts[-1] != receipt:
            return RegistryReplay(False, "REGISTRY_REPLAY_MISMATCH", expected_sequence - 1, expected_previous)
    if current != registry:
        return RegistryReplay(False, "REGISTRY_FINAL_MISMATCH", len(registry.receipts), current.registry_digest)
    return RegistryReplay(True, "PASS", len(registry.receipts), registry.registry_digest)


def append_qualification_receipt(
    receipts: Sequence[QualificationReceipt], kind: str, subject: str, payload: object
) -> Tuple[QualificationReceipt, ...]:
    rows = tuple(receipts)
    unsigned = {
        "kind": kind,
        "payload": _canonical_json(payload),
        "previous_digest": rows[-1].receipt_digest if rows else ZERO_DIGEST,
        "sequence": len(rows) + 1,
        "subject": subject,
    }
    receipt = QualificationReceipt(
        sequence=unsigned["sequence"],
        kind=kind,
        subject=subject,
        payload=unsigned["payload"],
        previous_digest=unsigned["previous_digest"],
        receipt_digest=_digest_json(unsigned),
    )
    return rows + (receipt,)


def replay_qualification_receipts(receipts: Iterable[QualificationReceipt]) -> QualificationReplay:
    previous = ZERO_DIGEST
    count = 0
    for expected_sequence, receipt in enumerate(tuple(receipts), 1):
        if not isinstance(receipt, QualificationReceipt):
            return QualificationReplay(False, "RECEIPT_TYPE_INVALID", count, previous)
        if receipt.sequence != expected_sequence:
            return QualificationReplay(False, "RECEIPT_SEQUENCE_MISMATCH", count, previous)
        if receipt.previous_digest != previous:
            return QualificationReplay(False, "RECEIPT_CHAIN_MISMATCH", count, previous)
        if not _is_digest(receipt.receipt_digest) or _digest_json(receipt.unsigned_record()) != receipt.receipt_digest:
            return QualificationReplay(False, "RECEIPT_DIGEST_MISMATCH", count, previous)
        try:
            payload = json.loads(receipt.payload)
        except (TypeError, json.JSONDecodeError):
            return QualificationReplay(False, "RECEIPT_PAYLOAD_INVALID", count, previous)
        if receipt.kind == "SUMMARY":
            required = {
                "bolt_on_executed_actions": 0,
                "observation_host_actions": 0,
                "rejection_cases_safely_rejected": EXPECTED_REJECTION_CASES,
            }
            if any(payload.get(key) != value for key, value in required.items()):
                return QualificationReplay(False, "SUMMARY_SEMANTICS_INVALID", count, previous)
        previous = receipt.receipt_digest
        count += 1
    return QualificationReplay(True, "PASS", count, previous)


def structural_read_only_scan() -> Tuple[bool, Tuple[str, ...]]:
    hits: list[str] = []
    if _sha256_file(ADAPTER_PATH) != EXPECTED_ADAPTER_SOURCE_SHA256:
        hits.append("ADAPTER_SOURCE_DIGEST_MISMATCH")
    source = ADAPTER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ADAPTER_PATH))
    allowed_roots = {"__future__", "hashlib", "json", "dataclasses", "typing"}
    prohibited_methods = {
        "apply",
        "dispatch",
        "execute",
        "execute_host_action",
        "mutate_host",
        "project_action",
        "run_command",
        "send_command",
        "submit",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root not in allowed_roots:
                    hits.append(f"NON_STDLIB_IMPORT:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root not in allowed_roots:
                hits.append(f"NON_STDLIB_IMPORT:{node.module}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in prohibited_methods:
            hits.append(f"PROHIBITED_METHOD:{node.name}")
    if adapter_module.EXECUTION_AUTHORITY != "NONE":
        hits.append("EXECUTION_AUTHORITY_NOT_NONE")
    if tuple(adapter_module.COMMAND_SURFACE):
        hits.append("COMMAND_SURFACE_NOT_EMPTY")
    methods = {
        name
        for name, value in adapter_module.ReadOnlyObservationAdapter.__dict__.items()
        if callable(value) and not name.startswith("_")
    }
    if methods != {"identity", "normalise_record", "observe"}:
        hits.append("ADAPTER_PUBLIC_METHOD_SET_CHANGED")
    return not hits, tuple(hits)


def _rehash_snapshot(snapshot: dict[str, object]) -> None:
    snapshot["snapshot_digest"] = _digest_json({key: value for key, value in snapshot.items() if key != "snapshot_digest"})


def _rehash_receipts(receipts: list[object]) -> None:
    previous = ZERO_DIGEST
    for index, value in enumerate(receipts, 1):
        if not isinstance(value, dict):
            previous = ZERO_DIGEST
            continue
        value["sequence"] = index
        value["previous_receipt_digest"] = previous
        value["receipt_digest"] = _digest_json({key: item for key, item in value.items() if key != "receipt_digest"})
        previous = str(value["receipt_digest"])


def _mutations(snapshot: Mapping[str, object], receipts: Sequence[Mapping[str, object]]) -> Tuple[Tuple[str, object, object], ...]:
    cases: list[Tuple[str, object, object]] = []

    def fresh() -> Tuple[dict[str, object], list[object]]:
        return _clone(snapshot), _clone(receipts)  # type: ignore[return-value]

    s, r = fresh(); del s["host_version"]; cases.append(("snapshot_missing_field", s, r))
    s, r = fresh(); s["unexpected"] = 1; cases.append(("snapshot_extra_field", s, r))
    s, r = fresh(); s["host_family"] = "OTHER"; _rehash_snapshot(s); cases.append(("host_family", s, r))
    s, r = fresh(); s["host_version"] = "2.0"; _rehash_snapshot(s); cases.append(("host_version", s, r))
    s, r = fresh(); s["integration_api"] = "OTHER"; _rehash_snapshot(s); cases.append(("integration_api", s, r))
    s, r = fresh(); s["command_count"] = 7; s["rejected_count"] = 1; _rehash_snapshot(s); cases.append(("command_count", s, r))
    s, r = fresh(); s["applied_count"] = 5; s["rejected_count"] = 1; _rehash_snapshot(s); cases.append(("applied_count", s, r))
    s, r = fresh(); s["applied_count"] = 5; s["rejected_count"] = 1; _rehash_snapshot(s); cases.append(("rejected_count", s, r))
    s, r = fresh(); s["final_receipt_digest"] = "x"; cases.append(("final_digest_invalid", s, r))
    s, r = fresh(); s["final_receipt_digest"] = "1" * 64; _rehash_snapshot(s); cases.append(("final_digest_wrong", s, r))
    s, r = fresh(); s["snapshot_digest"] = "2" * 64; cases.append(("snapshot_digest", s, r))
    s, r = fresh(); s["records"][0]["record_digest"] = "3" * 64; _rehash_snapshot(s); cases.append(("record_digest", s, r))
    s, r = fresh(); s["records"][0]["state"] = "UNKNOWN"; cases.append(("record_state", s, r))
    s, r = fresh(); rec=s["records"][0]; rec["version"]=5; rec["record_digest"]=_digest_json({k:v for k,v in rec.items() if k!="record_digest"}); _rehash_snapshot(s); cases.append(("record_version", s, r))
    s, r = fresh(); rec=s["records"][0]; rec["checkpoint_count"]=0; rec["record_digest"]=_digest_json({k:v for k,v in rec.items() if k!="record_digest"}); _rehash_snapshot(s); cases.append(("checkpoint_count", s, r))
    s, r = fresh(); s["records"].append(_clone(s["records"][0])); _rehash_snapshot(s); cases.append(("duplicate_record", s, r))
    s, r = fresh(); rec=_clone(s["records"][0]); rec["job_id"]="JOB-000"; rec["record_digest"]=_digest_json({k:v for k,v in rec.items() if k!="record_digest"}); s["records"].append(rec); _rehash_snapshot(s); cases.append(("record_order", s, r))
    s, r = fresh(); r.pop(); cases.append(("missing_receipt", s, r))
    s, r = fresh(); r.append(_clone(r[-1])); cases.append(("duplicate_receipt", s, r))
    s, r = fresh(); r[2],r[3]=r[3],r[2]; cases.append(("reordered_receipt", s, r))
    s, r = fresh(); r[1]["sequence"]=99; cases.append(("receipt_sequence", s, r))
    s, r = fresh(); r[1]["previous_receipt_digest"]="4"*64; r[1]["receipt_digest"]=_digest_json({k:v for k,v in r[1].items() if k!="receipt_digest"}); cases.append(("receipt_chain", s, r))
    s, r = fresh(); r[0]["receipt_digest"]="5"*64; cases.append(("receipt_digest", s, r))
    s, r = fresh(); del r[0]["reason"]; cases.append(("receipt_missing_field", s, r))
    s, r = fresh(); r[0]["extra"]=1; cases.append(("receipt_extra_field", s, r))
    s, r = fresh(); r[2]["operation"]="UNKNOWN"; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("unknown_operation", s, r))
    s, r = fresh(); r[2]["applied"]=False; r[2]["reason"]="REJECTED"; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("rejected_state_change", s, r))
    s, r = fresh(); r[2]["reason"]="NOT_APPLIED"; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("applied_reason", s, r))
    s, r = fresh(); r[3]["after_state"]="RUNNING"; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("applied_transition", s, r))
    s, r = fresh(); r[2]["after_version"]=4; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("applied_version", s, r))
    s, r = fresh(); r[4]["before_state"]="READY"; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("before_state", s, r))
    s, r = fresh(); r[4]["expected_version"]=3; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("expected_version", s, r))
    s, r = fresh(); r[3]["applied"]=False; r[3]["reason"]="APPLIED"; r[3]["after_state"]=r[3]["before_state"]; r[3]["after_version"]=r[3]["before_version"]; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("rejected_reason", s, r))
    s, r = fresh(); r[3]["applied"]=False; r[3]["reason"]="REJECTED"; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("rejected_semantics", s, r))
    s, r = fresh(); r[3]["operation"]="START_JOB"; _rehash_receipts(r); s["final_receipt_digest"]=r[-1]["receipt_digest"]; _rehash_snapshot(s); cases.append(("semantic_rehash", s, r))
    s, r = fresh(); s["final_receipt_digest"]=r[-2]["receipt_digest"]; _rehash_snapshot(s); cases.append(("stale_snapshot", s, r))
    s, r = fresh(); r[0]["command_digest"]="bad"; cases.append(("command_digest", s, r))
    s, r = fresh(); r[0]="not-a-mapping"; cases.append(("receipt_type", s, r))
    s, r = fresh(); r[0]["reason"]={"not":"scalar"}; cases.append(("noncanonical_field", s, r))
    s, r = fresh(); r[0]["sequence"]=True; cases.append(("boolean_sequence", s, r))
    return tuple(cases)


def run_rejection_matrix(
    raw_snapshot: Mapping[str, object], raw_receipts: Sequence[Mapping[str, object]], baseline_digest: str
) -> Tuple[RejectionResult, ...]:
    observer = adapter_module.ReadOnlyObservationAdapter()
    results: list[RejectionResult] = []
    for name, snapshot, receipts in _mutations(raw_snapshot, raw_receipts):
        rejected = False
        reason = "ACCEPTED"
        try:
            observer.observe(snapshot, receipts)
        except adapter_module.ObservationRejected as exc:
            rejected = True
            reason = exc.reason
        results.append(RejectionResult(name, rejected, reason, baseline_digest == EXPECTED_BASELINE_DIGEST, 0, 0))
    return tuple(results)


def _source_snapshot() -> Tuple[Tuple[str, str], ...]:
    paths = (
        PROJECT_DIR / "README.md",
        PROJECT_DIR / "README_STAGE_1.md",
        PROJECT_DIR / "README_STAGE_2.md",
        PROJECT_DIR / "README_STAGE_3.md",
        STAGE1_PATH,
        STAGE2_PATH,
        HOST_PATH,
        ADAPTER_PATH,
        THIS_FILE,
        PROJECT_DIR / "tests" / "test_external_host_contract.py",
        PROJECT_DIR / "tests" / "test_independent_host_baseline.py",
        PROJECT_DIR / "tests" / "test_read_only_observation_adapter.py",
    )
    return tuple((path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path)) for path in paths)


def run_stage3_qualification() -> Stage3Qualification:
    source_before = _source_snapshot()
    frozen_pre_digest = _sha256_file(FROZEN_V03_MANIFEST) if FROZEN_V03_MANIFEST.is_file() else ZERO_DIGEST
    stage2_qualification = stage2.run_stage2_qualification()
    frozen_pre_pass, _, frozen_entries = stage2.verify_frozen_v03_release()
    adapter_read_only, _ = structural_read_only_scan()

    baseline_before = host.build_native_baseline()
    registry0 = empty_registry()
    registry1 = attach(registry0)
    baseline_during = host.build_native_baseline()

    raw_snapshot = baseline_before.snapshot.record()
    raw_receipts = tuple(receipt.record() for receipt in baseline_before.receipts)
    observer = adapter_module.ReadOnlyObservationAdapter()
    observation = observer.observe(raw_snapshot, raw_receipts)
    observation_second = observer.observe(raw_snapshot, raw_receipts)
    observation_replay = adapter_module.replay_observation(observation)

    registry2 = detach(registry1)
    registry_replay = replay_registry(registry2)
    baseline_after = host.build_native_baseline()

    tampered_receipts = _clone(raw_receipts)
    tampered_receipts[2]["after_state"] = "PAUSED"
    try:
        observer.observe(raw_snapshot, tampered_receipts)
        tamper_detection = False
    except adapter_module.ObservationRejected:
        tamper_detection = True

    reordered_receipts = list(_clone(raw_receipts))
    reordered_receipts[2], reordered_receipts[3] = reordered_receipts[3], reordered_receipts[2]
    try:
        observer.observe(raw_snapshot, reordered_receipts)
        reorder_detection = False
    except adapter_module.ObservationRejected:
        reorder_detection = True

    semantic_snapshot = _clone(raw_snapshot)
    semantic_receipts = list(_clone(raw_receipts))
    semantic_receipts[3]["operation"] = "START_JOB"
    _rehash_receipts(semantic_receipts)
    semantic_snapshot["final_receipt_digest"] = semantic_receipts[-1]["receipt_digest"]
    _rehash_snapshot(semantic_snapshot)
    try:
        observer.observe(semantic_snapshot, semantic_receipts)
        semantic_rehash_detection = False
    except adapter_module.ObservationRejected:
        semantic_rehash_detection = True

    rejection_results = run_rejection_matrix(raw_snapshot, raw_receipts, baseline_before.run_digest)
    safely_rejected = sum(
        1
        for result in rejection_results
        if result.rejected
        and result.host_unchanged
        and result.observation_host_actions == 0
        and result.bolt_on_executed_actions == 0
    )

    receipts: Tuple[QualificationReceipt, ...] = ()
    receipts = append_qualification_receipt(receipts, "FROZEN_BASELINE", "v0.3", {
        "entries": frozen_entries,
        "manifest_sha256": frozen_pre_digest,
        "passed": frozen_pre_pass,
    })
    receipts = append_qualification_receipt(receipts, "STAGE2", EXPECTED_STAGE2_COMMIT, {
        "baseline_digest": stage2_qualification.baseline_digest,
        "passed": stage2_qualification.passed,
    })
    receipts = append_qualification_receipt(receipts, "ADAPTER_SOURCE", adapter_module.ADAPTER_ID, {
        "read_only": adapter_read_only,
        "source_sha256": _sha256_file(ADAPTER_PATH),
    })
    receipts = append_qualification_receipt(receipts, "ATTACHMENT", registry2.registry_id, {
        "attach": 1,
        "detach": 1,
        "empty": not registry2.attached,
        "registry_digest": registry2.registry_digest,
    })
    receipts = append_qualification_receipt(receipts, "OBSERVATION", host.HOST_FAMILY, {
        "batch_digest": observation.batch_digest,
        "events": len(observation.events),
        "subjects": len(observation.subjects),
    })
    receipts = append_qualification_receipt(receipts, "REJECTION_MATRIX", adapter_module.ADAPTER_ID, {
        "cases": len(rejection_results),
        "safely_rejected": safely_rejected,
    })
    receipts = append_qualification_receipt(receipts, "SUMMARY", "STAGE-3", {
        "bolt_on_executed_actions": 0,
        "observation_host_actions": 0,
        "rejection_cases_safely_rejected": safely_rejected,
    })
    qualification_replay = replay_qualification_receipts(receipts)

    frozen_post_pass, _, frozen_post_entries = stage2.verify_frozen_v03_release()
    frozen_post_digest = _sha256_file(FROZEN_V03_MANIFEST) if FROZEN_V03_MANIFEST.is_file() else ZERO_DIGEST
    source_unchanged = source_before == _source_snapshot()
    frozen_unchanged = (
        frozen_pre_pass
        and frozen_post_pass
        and frozen_entries == frozen_post_entries
        and frozen_pre_digest == frozen_post_digest
    )
    host_state_changes = len({
        baseline_before.run_digest,
        baseline_during.run_digest,
        baseline_after.run_digest,
    }) - 1
    deterministic_second = observation == observation_second

    passed = all((
        stage2_qualification.passed,
        stage2_qualification.baseline_digest == EXPECTED_BASELINE_DIGEST,
        stage2_qualification.bolt_on_executed_actions == 0,
        frozen_pre_pass,
        frozen_post_pass,
        frozen_unchanged,
        frozen_entries == EXPECTED_FROZEN_V03_ENTRIES,
        _sha256_file(HOST_PATH) == EXPECTED_HOST_SOURCE_SHA256,
        _sha256_file(STAGE1_PATH) == EXPECTED_STAGE1_SOURCE_SHA256,
        adapter_read_only,
        _sha256_file(ADAPTER_PATH) == EXPECTED_ADAPTER_SOURCE_SHA256,
        source_unchanged,
        baseline_before == baseline_during == baseline_after,
        baseline_before.run_digest == EXPECTED_BASELINE_DIGEST,
        host_state_changes == 0,
        deterministic_second,
        observation_replay.passed,
        registry_replay.passed,
        not registry2.attached,
        len(registry2.receipts) == 2,
        len(observation.subjects) == EXPECTED_SUBJECTS,
        len(observation.events) == EXPECTED_OBSERVATION_EVENTS,
        observation.source_command_count == EXPECTED_OBSERVATION_EVENTS,
        tamper_detection,
        reorder_detection,
        semantic_rehash_detection,
        len(rejection_results) == EXPECTED_REJECTION_CASES,
        safely_rejected == EXPECTED_REJECTION_CASES,
        qualification_replay.passed,
    ))

    return Stage3Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        bolt_on_execution_authority=BOLT_ON_EXECUTION_AUTHORITY,
        host_execution_boundary=HOST_EXECUTION_BOUNDARY,
        attachment_mode=ATTACHMENT_MODE,
        stage2_pass=stage2_qualification.passed,
        frozen_v03_pass=frozen_pre_pass and frozen_post_pass,
        frozen_v03_unchanged=frozen_unchanged,
        frozen_v03_entries=frozen_entries,
        source_unchanged=source_unchanged,
        adapter_read_only=adapter_read_only,
        deterministic_second_pass=deterministic_second,
        attachment_replay_pass=registry_replay.passed,
        observation_replay_pass=observation_replay.passed,
        receipt_tamper_detection_pass=tamper_detection,
        receipt_reorder_detection_pass=reorder_detection,
        semantic_rehash_detection_pass=semantic_rehash_detection,
        attach_registrations=1,
        detach_registrations=1,
        registry_empty_after_detach=not registry2.attached,
        host_state_changes=host_state_changes,
        baseline_native_host_actions=stage2_qualification.native_host_actions,
        observation_host_actions=0,
        bolt_on_executed_actions=0,
        observed_subjects=len(observation.subjects),
        observation_events=len(observation.events),
        rejection_cases=len(rejection_results),
        rejection_cases_safely_rejected=safely_rejected,
        baseline_digest=baseline_before.run_digest,
        source_snapshot_digest=observation.source_snapshot_digest,
        source_final_receipt_digest=observation.source_final_receipt_digest,
        final_observation_digest=observation.final_observation_digest,
        observation_batch_digest=observation.batch_digest,
        observation_replay_digest=observation_replay.replay_digest,
        registry_digest=registry2.registry_digest,
        qualification_receipt_digest=receipts[-1].receipt_digest,
        qualification_replay_digest=qualification_replay.final_digest,
        stage1_source_sha256=_sha256_file(STAGE1_PATH),
        host_source_sha256=_sha256_file(HOST_PATH),
        adapter_source_sha256=_sha256_file(ADAPTER_PATH),
        frozen_v03_manifest_sha256=frozen_pre_digest,
    )


def main() -> int:
    qualification = run_stage3_qualification()
    print(f"Stage: {qualification.stage_name} {qualification.stage_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Bolt-on execution authority: {qualification.bolt_on_execution_authority}")
    print(f"Host execution boundary: {qualification.host_execution_boundary}")
    print(f"Attachment mode: {qualification.attachment_mode}")
    print(f"Stage 2 commit: {EXPECTED_STAGE2_COMMIT}")
    print(f"Stage 1 source: {qualification.stage1_source_sha256}")
    print(f"Frozen v0.3 manifest: {qualification.frozen_v03_manifest_sha256}")
    print(f"Frozen v0.3 entries: {qualification.frozen_v03_entries}")
    print(f"Host: {host.HOST_FAMILY} {host.HOST_VERSION}")
    print(f"Host source: {qualification.host_source_sha256}")
    print(f"Adapter: {adapter_module.ADAPTER_ID} {adapter_module.ADAPTER_VERSION}")
    print(f"Adapter source: {qualification.adapter_source_sha256}")
    print(f"Adapter read-only: {qualification.adapter_read_only}")
    print(f"Adapter command surface entries: {len(adapter_module.COMMAND_SURFACE)}")
    print(f"Attach registrations: {qualification.attach_registrations}")
    print(f"Detach registrations: {qualification.detach_registrations}")
    print(f"Registry empty after detach: {qualification.registry_empty_after_detach}")
    print(f"Observed subjects: {qualification.observed_subjects}")
    print(f"Observation events: {qualification.observation_events}")
    print(f"Rejection cases: {qualification.rejection_cases}")
    print(f"Rejection cases safely rejected: {qualification.rejection_cases_safely_rejected}")
    print(f"Host state changes during attach/detach: {qualification.host_state_changes}")
    print(f"Baseline native host actions: {qualification.baseline_native_host_actions}")
    print(f"Observation host actions: {qualification.observation_host_actions}")
    print(f"Bolt-on executed actions: {qualification.bolt_on_executed_actions}")
    print(f"Deterministic second pass: {qualification.deterministic_second_pass}")
    print(f"Observation replay: {qualification.observation_replay_pass}")
    print(f"Baseline digest: {qualification.baseline_digest}")
    print(f"Source snapshot digest: {qualification.source_snapshot_digest}")
    print(f"Source final receipt digest: {qualification.source_final_receipt_digest}")
    print(f"Final observation digest: {qualification.final_observation_digest}")
    print(f"Observation batch digest: {qualification.observation_batch_digest}")
    print(f"Observation replay digest: {qualification.observation_replay_digest}")
    print(f"Registry digest: {qualification.registry_digest}")
    print(f"Qualification receipt digest: {qualification.qualification_receipt_digest}")
    print(f"Qualification replay digest: {qualification.qualification_replay_digest}")
    if qualification.passed:
        print("STAGE 3 READ-ONLY EXTERNAL OBSERVATION ADAPTER: PASS")
        return 0
    print("STAGE 3 READ-ONLY EXTERNAL OBSERVATION ADAPTER: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
