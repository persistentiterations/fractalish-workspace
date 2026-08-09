#!/usr/bin/env python3
"""Qualification harness for v0.4 Stage 4 host-owned command crossing."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
import subprocess
import sys
from typing import Iterable, Mapping, Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "HOST-OWNED BOUNDED COMMAND GATEWAY"
STAGE_VERSION = "0.4.4"
MODE = "LIVE_HOST_OWNED_COMMAND_CROSSING"
BOLT_ON_EXECUTION_AUTHORITY = "NONE"
GATEWAY_EXECUTION_OWNER = "HOST"
HOST_EXECUTION_BOUNDARY = "NATIVE_HOST_ONLY"
ZERO_DIGEST = "0" * 64

EXPECTED_STAGE3_COMMIT = "d4c7dd0f84b4aeed32dcd6fabc15e82ae4f37c10"
EXPECTED_STAGE1_SOURCE_SHA256 = "8035b10d0e68ec0365f48340366ec3bdd903a4dcc2e7b9b2574b2269c04b4806"
EXPECTED_STAGE2_SOURCE_SHA256 = "b973a626061dd2853ce6aca5b38c0d66bcc31e2234802cdb5c1055dd55d72a34"
EXPECTED_STAGE3_SOURCE_SHA256 = "29a801c12324ce94dd08b0c88184e56f5d86501d4a5094fae8cbc9d36f7448d2"
EXPECTED_HOST_SOURCE_SHA256 = "14a3b86d4cabee409d84904f3db4feb416be905c3c54edb3ca5ef4d50e41a797"
EXPECTED_OBSERVER_SOURCE_SHA256 = "176232fe8f4a9266fc90259ea82f19e36b36863fb14f328786c8ddb7ebcf6f68"
EXPECTED_PROJECTOR_SOURCE_SHA256 = "9031999d62820a971e7e201c3393a710716c20f9973c8c33a2a0b3e8b455f57d"
EXPECTED_GATEWAY_SOURCE_SHA256 = "ab41240248100acff9b4e599ac2109f609d75528c954c101a2fd9bc241667fea"
EXPECTED_FROZEN_V03_MANIFEST_SHA256 = "57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa"
EXPECTED_FROZEN_V03_ENTRIES = 20
EXPECTED_GATEWAY_ACTIONS = 2
EXPECTED_SURROUNDING_NATIVE_ACTIONS = 4
EXPECTED_TOTAL_NATIVE_ACTIONS = 6
EXPECTED_PROJECTED_REQUESTS = 2

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
HOST_PATH = PROJECT_DIR / "hosts" / "ordinary_job_service.py"
STAGE1_PATH = PROJECT_DIR / "integration" / "external_host_contract.py"
STAGE2_PATH = PROJECT_DIR / "integration" / "independent_host_baseline.py"
STAGE3_PATH = PROJECT_DIR / "integration" / "read_only_observation_adapter.py"
OBSERVER_PATH = PROJECT_DIR / "adapters" / "read_only_job_observer.py"
PROJECTOR_PATH = PROJECT_DIR / "adapters" / "bounded_action_projector.py"
GATEWAY_PATH = PROJECT_DIR / "gateways" / "host_owned_command_gateway.py"
VERIFY_ALL_PATH = REPOSITORY_ROOT / "tools" / "verify_all_frozen.py"

GOVERNANCE_SESSION_DIGEST = hashlib.sha256(b"V04-STAGE4-GOVERNANCE-SESSION").hexdigest()
AUTHORITY_DIGEST = hashlib.sha256(b"V04-STAGE4-BOUNDED-AUTHORITY").hexdigest()


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


observer_module = _load_module("v04_stage4_read_only_observer", OBSERVER_PATH)
projector_module = _load_module("v04_stage4_bounded_projector", PROJECTOR_PATH)
gateway_module = _load_module("v04_stage4_host_gateway", GATEWAY_PATH)
host = gateway_module.host


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


def _clone(value: object) -> object:
    return json.loads(_canonical_json(value))


def validate_frozen_releases() -> Tuple[bool, str]:
    if not VERIFY_ALL_PATH.is_file():
        return False, "AGGREGATE_VERIFIER_MISSING"
    completed = subprocess.run(
        [sys.executable, str(VERIFY_ALL_PATH)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    output = completed.stdout + "\n" + completed.stderr
    required = (
        "BOLT-ON v0.1 FROZEN VERIFICATION PASSED: 21 files",
        "BOLT-ON v0.2 FROZEN VERIFICATION PASSED: 25 files",
        "BOLT-ON v0.3 FROZEN VERIFICATION PASSED: 20 files",
        "ALL FROZEN RELEASE VERIFICATIONS PASSED",
    )
    if completed.returncode or any(marker not in output for marker in required):
        return False, "AGGREGATE_FROZEN_VERIFICATION_FAILED"
    return True, "PASS"


def validate_source_bindings() -> Tuple[bool, Tuple[str, ...]]:
    expected = {
        STAGE1_PATH: EXPECTED_STAGE1_SOURCE_SHA256,
        STAGE2_PATH: EXPECTED_STAGE2_SOURCE_SHA256,
        STAGE3_PATH: EXPECTED_STAGE3_SOURCE_SHA256,
        HOST_PATH: EXPECTED_HOST_SOURCE_SHA256,
        OBSERVER_PATH: EXPECTED_OBSERVER_SOURCE_SHA256,
        PROJECTOR_PATH: EXPECTED_PROJECTOR_SOURCE_SHA256,
        GATEWAY_PATH: EXPECTED_GATEWAY_SOURCE_SHA256,
    }
    failures = tuple(
        f"SOURCE_MISMATCH:{path.relative_to(REPOSITORY_ROOT).as_posix()}"
        for path, digest in expected.items()
        if not path.is_file() or _sha256_file(path) != digest
    )
    return not failures, failures


def structural_authority_scan() -> Tuple[bool, Tuple[str, ...]]:
    hits: list[str] = []
    projector_source = PROJECTOR_PATH.read_text(encoding="utf-8")
    projector_tree = ast.parse(projector_source, filename=str(PROJECTOR_PATH))
    allowed_projector_imports = {
        "__future__", "hashlib", "importlib", "json", "dataclasses", "pathlib", "sys", "typing"
    }
    for node in ast.walk(projector_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] not in allowed_projector_imports:
                    hits.append(f"PROJECTOR_IMPORT:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root not in allowed_projector_imports:
                hits.append(f"PROJECTOR_IMPORT:{node.module}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {
            "apply", "dispatch", "execute", "send_command", "submit", "mutate_host"
        }:
            hits.append(f"PROJECTOR_EXECUTION_METHOD:{node.name}")
    lowered = projector_source.lower()
    for token in ("ordinary_job_service", "host_owned_command_gateway", "authority_token"):
        if token in lowered:
            hits.append(f"PROJECTOR_FORBIDDEN_COUPLING:{token}")

    gateway_source = GATEWAY_PATH.read_text(encoding="utf-8")
    if "read_only_job_observer" in gateway_source or "bounded_action_projector" in gateway_source:
        hits.append("GATEWAY_IMPORTS_ADAPTER")
    if gateway_module.EXECUTION_OWNER != "HOST":
        hits.append("GATEWAY_OWNER_INVALID")
    if gateway_module.BOLT_ON_EXECUTION_AUTHORITY != "NONE":
        hits.append("BOLT_ON_AUTHORITY_INVALID")
    return not hits, tuple(hits)


def _source_snapshot() -> Tuple[Tuple[str, str], ...]:
    paths = (
        PROJECT_DIR / "README.md",
        PROJECT_DIR / "README_STAGE_1.md",
        PROJECT_DIR / "README_STAGE_2.md",
        PROJECT_DIR / "README_STAGE_3.md",
        PROJECT_DIR / "README_STAGE_4.md",
        STAGE1_PATH,
        STAGE2_PATH,
        STAGE3_PATH,
        HOST_PATH,
        OBSERVER_PATH,
        PROJECTOR_PATH,
        GATEWAY_PATH,
        THIS_FILE,
        PROJECT_DIR / "tests" / "test_external_host_contract.py",
        PROJECT_DIR / "tests" / "test_independent_host_baseline.py",
        PROJECT_DIR / "tests" / "test_read_only_observation_adapter.py",
        PROJECT_DIR / "tests" / "test_host_owned_bounded_command_gateway.py",
    )
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in paths
        if path.is_file()
    )


def _submit_required(service: object, command: object) -> object:
    receipt = service.submit(command)
    if not receipt.applied:
        raise RuntimeError(f"required native command rejected: {receipt.reason}")
    return receipt


def _build_setup_service() -> object:
    service = host.NativeJobService()
    commands = (
        host.make_command(host.REGISTER_JOB, "JOB-GATEWAY", 0, "STAGE4-001"),
        host.make_command(host.START_JOB, "JOB-GATEWAY", 1, "STAGE4-002"),
        host.make_command(
            host.CHECKPOINT_JOB,
            "JOB-GATEWAY",
            2,
            "STAGE4-003",
            payload={"checkpoint": "STAGE4-CHECKPOINT-1"},
        ),
    )
    for command in commands:
        _submit_required(service, command)
    return service


def _observe(service: object):
    run = service.export_run()
    observer = observer_module.ReadOnlyObservationAdapter()
    batch = observer.observe(
        run.snapshot.record(),
        tuple(receipt.record() for receipt in run.receipts),
    )
    replay = observer_module.replay_observation(batch)
    if not replay.passed:
        raise RuntimeError(f"observation replay failed: {replay.reason}")
    return run, batch, replay


def _project(action: str, request_id: int, batch: object):
    subject = batch.subjects[0]
    event = batch.events[-1]
    request = projector_module.build_portable_request(
        request_id=request_id,
        action=action,
        subject_id=subject.subject_id,
        source_observation_digest=event.observation_digest,
        governance_session_digest=GOVERNANCE_SESSION_DIGEST,
        authority_digest=AUTHORITY_DIGEST,
        observed_state=subject.observed_state,
        current_epoch=subject.native_version,
    )
    projector = projector_module.BoundedActionProjector()
    envelope = projector.project(request, event.record(), subject.record())
    valid, reason = projector_module.validate_envelope_record(envelope.record())
    if not valid:
        raise RuntimeError(f"projected envelope invalid: {reason}")
    permit = gateway_module.issue_permit(
        action=envelope.action,
        subject_id=envelope.subject_id,
        expected_native_state=envelope.expected_native_state,
        expected_native_version=envelope.expected_native_version,
        source_observation_digest=envelope.source_observation_digest,
        source_receipt_digest=envelope.source_receipt_digest,
        governance_session_digest=envelope.governance_session_digest,
        authority_digest=envelope.authority_digest,
        projector_identity_digest=envelope.projector_identity_digest,
    )
    return request, envelope, permit


@dataclass(frozen=True)
class CampaignResult:
    host_run: object
    direct_run: object
    hold_request: object
    release_request: object
    hold_envelope: object
    release_envelope: object
    hold_permit: object
    release_permit: object
    decisions: Tuple[object, ...]
    decision_replay: object
    native_replay: object
    final_observation: object


def run_live_campaign() -> CampaignResult:
    service = _build_setup_service()
    _, observed_before_hold, _ = _observe(service)
    hold_request, hold_envelope, hold_permit = _project(projector_module.HOLD, 401, observed_before_hold)

    gateway = gateway_module.HostOwnedCommandGateway()
    hold_decision = gateway.process(hold_envelope.record(), hold_permit, service)
    if not hold_decision.accepted:
        raise RuntimeError(f"HOLD rejected: {hold_decision.reason}")

    _, observed_before_release, _ = _observe(service)
    release_request, release_envelope, release_permit = _project(
        projector_module.RELEASE, 402, observed_before_release
    )
    release_decision = gateway.process(release_envelope.record(), release_permit, service)
    if not release_decision.accepted:
        raise RuntimeError(f"RELEASE rejected: {release_decision.reason}")

    _submit_required(
        service,
        host.make_command(host.COMPLETE_JOB, "JOB-GATEWAY", 5, "STAGE4-006"),
    )
    host_run = service.export_run()
    final_observation = observer_module.ReadOnlyObservationAdapter().observe(
        host_run.snapshot.record(), tuple(receipt.record() for receipt in host_run.receipts)
    )

    direct = host.NativeJobService()
    direct_commands = (
        host.make_command(host.REGISTER_JOB, "JOB-GATEWAY", 0, "STAGE4-001"),
        host.make_command(host.START_JOB, "JOB-GATEWAY", 1, "STAGE4-002"),
        host.make_command(
            host.CHECKPOINT_JOB,
            "JOB-GATEWAY",
            2,
            "STAGE4-003",
            payload={"checkpoint": "STAGE4-CHECKPOINT-1"},
        ),
        host.make_command(host.PAUSE_JOB, "JOB-GATEWAY", 3, hold_envelope.idempotency_key),
        host.make_command(host.RESUME_JOB, "JOB-GATEWAY", 4, release_envelope.idempotency_key),
        host.make_command(host.COMPLETE_JOB, "JOB-GATEWAY", 5, "STAGE4-006"),
    )
    for command in direct_commands:
        _submit_required(direct, command)
    direct_run = direct.export_run()

    return CampaignResult(
        host_run=host_run,
        direct_run=direct_run,
        hold_request=hold_request,
        release_request=release_request,
        hold_envelope=hold_envelope,
        release_envelope=release_envelope,
        hold_permit=hold_permit,
        release_permit=release_permit,
        decisions=gateway.decisions,
        decision_replay=gateway_module.replay_decisions(gateway.decisions),
        native_replay=host.replay_run(host_run),
        final_observation=final_observation,
    )


def _rehash_envelope(envelope: Mapping[str, object]) -> dict[str, object]:
    row = dict(envelope)
    row["envelope_digest"] = _digest_json(
        {key: row[key] for key in projector_module.ENVELOPE_KEYS if key != "envelope_digest"}
    )
    return row


def build_attack_fixture():
    service = _build_setup_service()
    _, batch, _ = _observe(service)
    _, envelope, permit = _project(projector_module.HOLD, 499, batch)
    return service, envelope.record(), permit


def build_adversarial_cases() -> Tuple[Tuple[str, object, object], ...]:
    _, valid, permit = build_attack_fixture()
    cases: list[Tuple[str, object, object]] = [("ENVELOPE_NOT_MAPPING", [], permit)]
    for key in sorted(projector_module.ENVELOPE_KEYS):
        row = dict(valid)
        row.pop(key)
        cases.append((f"MISSING_{key.upper()}", row, permit))
    row = dict(valid); row["extra"] = "x"; cases.append(("EXTRA_FIELD", row, permit))
    row = dict(valid); row["envelope_digest"] = ZERO_DIGEST; cases.append(("DIGEST_ZERO", row, permit))

    mutations = (
        ("SCHEMA_VERSION", "schema_version", "WRONG-SCHEMA"),
        ("ENVELOPE_ID", "envelope_id", "ENV-WRONG"),
        ("REQUEST_BOOL", "request_id", True),
        ("REQUEST_ZERO", "request_id", 0),
        ("ACTION_UNKNOWN", "action", "CANCEL"),
        ("SUBJECT_WRONG", "subject_id", "OTHER-JOB"),
        ("OPERATION_WRONG", "native_operation", host.COMPLETE_JOB),
        ("STATE_WRONG", "expected_native_state", host.PAUSED),
        ("VERSION_STALE", "expected_native_version", 2),
        ("VERSION_FUTURE", "expected_native_version", 99),
        ("OBSERVATION_WRONG", "source_observation_digest", hashlib.sha256(b"wrong-observation").hexdigest()),
        ("RECEIPT_WRONG", "source_receipt_digest", hashlib.sha256(b"wrong-receipt").hexdigest()),
        ("REQUEST_DIGEST_WRONG", "source_request_digest", hashlib.sha256(b"wrong-request").hexdigest()),
        ("GOVERNANCE_WRONG", "governance_session_digest", hashlib.sha256(b"wrong-governance").hexdigest()),
        ("AUTHORITY_WRONG", "authority_digest", hashlib.sha256(b"wrong-authority").hexdigest()),
        ("PROJECTOR_WRONG", "projector_identity_digest", hashlib.sha256(b"wrong-projector").hexdigest()),
        ("WOULD_DISPATCH_FALSE", "would_dispatch", False),
        ("EXECUTED_TRUE", "executed", True),
        ("IDEMPOTENCY_EMPTY", "idempotency_key", ""),
        ("IDEMPOTENCY_WRONG", "idempotency_key", "WRONG-IDEMPOTENCY"),
    )
    for name, key, value in mutations:
        row = dict(valid); row[key] = value; cases.append((name, _rehash_envelope(row), permit))

    permit_cases = (
        ("PERMIT_NOT_OBJECT", "not-a-permit"),
        ("PERMIT_DIGEST_ZERO", replace(permit, permit_digest=ZERO_DIGEST)),
        ("PERMIT_ACTION", gateway_module.rehash_permit(replace(permit, action=gateway_module.RELEASE, native_operation=gateway_module.RESUME_JOB, expected_native_state=gateway_module.PAUSED))),
        ("PERMIT_SUBJECT", gateway_module.rehash_permit(replace(permit, subject_id="OTHER-JOB"))),
        ("PERMIT_OPERATION", gateway_module.rehash_permit(replace(permit, native_operation=gateway_module.RESUME_JOB))),
        ("PERMIT_STATE", gateway_module.rehash_permit(replace(permit, expected_native_state=gateway_module.PAUSED))),
        ("PERMIT_VERSION", gateway_module.rehash_permit(replace(permit, expected_native_version=4))),
        ("PERMIT_OBSERVATION", gateway_module.rehash_permit(replace(permit, source_observation_digest=hashlib.sha256(b"permit-observation").hexdigest()))),
        ("PERMIT_RECEIPT", gateway_module.rehash_permit(replace(permit, source_receipt_digest=hashlib.sha256(b"permit-receipt").hexdigest()))),
        ("PERMIT_GOVERNANCE", gateway_module.rehash_permit(replace(permit, governance_session_digest=hashlib.sha256(b"permit-governance").hexdigest()))),
        ("PERMIT_AUTHORITY", gateway_module.rehash_permit(replace(permit, authority_digest=hashlib.sha256(b"permit-authority").hexdigest()))),
        ("PERMIT_PROJECTOR", gateway_module.rehash_permit(replace(permit, projector_identity_digest=hashlib.sha256(b"permit-projector").hexdigest()))),
    )
    for name, bad_permit in permit_cases:
        cases.append((name, valid, bad_permit))

    row = dict(valid)
    row["source_receipt_digest"] = hashlib.sha256(b"host-binding").hexdigest()
    row = _rehash_envelope(row)
    matching_permit = gateway_module.issue_permit(
        action=row["action"], subject_id=row["subject_id"],
        expected_native_state=row["expected_native_state"],
        expected_native_version=row["expected_native_version"],
        source_observation_digest=row["source_observation_digest"],
        source_receipt_digest=row["source_receipt_digest"],
        governance_session_digest=row["governance_session_digest"],
        authority_digest=row["authority_digest"],
        projector_identity_digest=row["projector_identity_digest"],
    )
    cases.append(("HOST_RECEIPT_BINDING", row, matching_permit))
    return tuple(cases)


def run_adversarial_campaign() -> Tuple[int, int, str]:
    cases = build_adversarial_cases()
    safely_rejected = 0
    results: list[dict[str, object]] = []
    for name, envelope, permit in cases:
        service, _, _ = build_attack_fixture()
        before = service.export_run()
        gateway = gateway_module.HostOwnedCommandGateway()
        decision = gateway.process(envelope, permit, service)
        after = service.export_run()
        safe = (
            not decision.accepted
            and not decision.host_action_executed
            and before == after
            and len(before.commands) == len(after.commands)
        )
        safely_rejected += int(safe)
        results.append({
            "name": name,
            "reason": decision.reason,
            "safe": safe,
            "decision_digest": decision.decision_digest,
        })
    return len(cases), safely_rejected, _digest_json(results)


def run_duplicate_checks() -> Tuple[bool, bool, str]:
    service, envelope, permit = build_attack_fixture()
    gateway = gateway_module.HostOwnedCommandGateway()
    first = gateway.process(envelope, permit, service)
    command_count = len(service.export_run().commands)
    duplicate = gateway.process(envelope, permit, service)
    duplicate_pass = (
        first.accepted
        and not duplicate.accepted
        and duplicate.reason == "DUPLICATE_GATEWAY_REQUEST"
        and len(service.export_run().commands) == command_count
    )

    conflict_row = dict(envelope)
    conflict_row["governance_session_digest"] = hashlib.sha256(b"conflict-governance").hexdigest()
    conflict_row = _rehash_envelope(conflict_row)
    conflict_permit = gateway_module.issue_permit(
        action=conflict_row["action"], subject_id=conflict_row["subject_id"],
        expected_native_state=conflict_row["expected_native_state"],
        expected_native_version=conflict_row["expected_native_version"],
        source_observation_digest=conflict_row["source_observation_digest"],
        source_receipt_digest=conflict_row["source_receipt_digest"],
        governance_session_digest=conflict_row["governance_session_digest"],
        authority_digest=conflict_row["authority_digest"],
        projector_identity_digest=conflict_row["projector_identity_digest"],
    )
    conflict = gateway.process(conflict_row, conflict_permit, service)
    conflict_pass = (
        not conflict.accepted
        and conflict.reason == "GATEWAY_IDEMPOTENCY_CONFLICT"
        and len(service.export_run().commands) == command_count
    )
    return duplicate_pass, conflict_pass, gateway.decisions[-1].decision_digest


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
    return rows + (
        QualificationReceipt(
            sequence=unsigned["sequence"], kind=kind, subject=subject,
            payload=unsigned["payload"], previous_digest=unsigned["previous_digest"],
            receipt_digest=_digest_json(unsigned),
        ),
    )


def replay_qualification_receipts(receipts: Iterable[QualificationReceipt]) -> QualificationReplay:
    previous = ZERO_DIGEST
    count = 0
    for expected_sequence, receipt in enumerate(tuple(receipts), 1):
        if not isinstance(receipt, QualificationReceipt):
            return QualificationReplay(False, "RECEIPT_TYPE_INVALID", count, previous)
        if receipt.sequence != expected_sequence or receipt.previous_digest != previous:
            return QualificationReplay(False, "RECEIPT_CHAIN_INVALID", count, previous)
        if _digest_json(receipt.unsigned_record()) != receipt.receipt_digest:
            return QualificationReplay(False, "RECEIPT_DIGEST_INVALID", count, previous)
        try:
            payload = json.loads(receipt.payload)
        except (TypeError, json.JSONDecodeError):
            return QualificationReplay(False, "RECEIPT_PAYLOAD_INVALID", count, previous)
        if receipt.kind == "SUMMARY":
            required = {
                "bolt_on_executed_actions": 0,
                "gateway_host_actions": EXPECTED_GATEWAY_ACTIONS,
                "total_native_host_actions": EXPECTED_TOTAL_NATIVE_ACTIONS,
            }
            if any(payload.get(key) != value for key, value in required.items()):
                return QualificationReplay(False, "SUMMARY_SEMANTICS_INVALID", count, previous)
        previous = receipt.receipt_digest
        count += 1
    return QualificationReplay(True, "PASS", count, previous)


@dataclass(frozen=True)
class Stage4Qualification:
    passed: bool
    stage_name: str
    stage_version: str
    mode: str
    bolt_on_execution_authority: str
    gateway_execution_owner: str
    host_execution_boundary: str
    frozen_verification_pass: bool
    source_bindings_pass: bool
    source_unchanged: bool
    no_hidden_authority: bool
    projected_requests: int
    gateway_permits: int
    gateway_accepted: int
    gateway_rejected: int
    gateway_host_actions: int
    surrounding_native_actions: int
    total_native_actions: int
    bolt_on_executed_actions: int
    direct_native_equivalence: bool
    deterministic_second_pass: bool
    native_replay_pass: bool
    observation_replay_pass: bool
    decision_replay_pass: bool
    duplicate_rejection_pass: bool
    idempotency_conflict_pass: bool
    adversarial_cases: int
    adversarial_cases_safely_rejected: int
    final_state: str
    final_version: int
    native_run_digest: str
    native_replay_digest: str
    direct_run_digest: str
    final_observation_digest: str
    gateway_decision_digest: str
    adversarial_digest: str
    qualification_receipt_digest: str
    qualification_replay_digest: str
    projector_source_sha256: str
    gateway_source_sha256: str


def run_stage4_qualification() -> Stage4Qualification:
    source_before = _source_snapshot()
    frozen_pass, _ = validate_frozen_releases()
    source_pass, _ = validate_source_bindings()
    authority_pass, _ = structural_authority_scan()

    campaign = run_live_campaign()
    campaign_second = run_live_campaign()
    adversarial_cases, adversarial_rejected, adversarial_digest = run_adversarial_campaign()
    duplicate_pass, conflict_pass, duplicate_digest = run_duplicate_checks()

    final_record = campaign.host_run.snapshot.records[0]
    gateway_accepted = sum(1 for decision in campaign.decisions if decision.accepted)
    gateway_rejected = len(campaign.decisions) - gateway_accepted
    gateway_actions = sum(1 for decision in campaign.decisions if decision.host_action_executed)
    direct_equivalence = campaign.host_run == campaign.direct_run
    deterministic = campaign == campaign_second
    observation_replay = observer_module.replay_observation(campaign.final_observation)

    receipts: Tuple[QualificationReceipt, ...] = ()
    receipts = append_qualification_receipt(receipts, "FROZEN", "v0.3", {
        "manifest_sha256": EXPECTED_FROZEN_V03_MANIFEST_SHA256,
        "entries": EXPECTED_FROZEN_V03_ENTRIES,
        "verified": frozen_pass,
    })
    receipts = append_qualification_receipt(receipts, "SOURCES", EXPECTED_STAGE3_COMMIT, {
        "bound": source_pass,
        "projector_sha256": EXPECTED_PROJECTOR_SOURCE_SHA256,
        "gateway_sha256": EXPECTED_GATEWAY_SOURCE_SHA256,
    })
    receipts = append_qualification_receipt(receipts, "HOLD", campaign.hold_envelope.subject_id, {
        "accepted": campaign.decisions[0].accepted,
        "action": campaign.hold_envelope.action,
        "native_operation": campaign.hold_envelope.native_operation,
        "decision_digest": campaign.decisions[0].decision_digest,
    })
    receipts = append_qualification_receipt(receipts, "RELEASE", campaign.release_envelope.subject_id, {
        "accepted": campaign.decisions[1].accepted,
        "action": campaign.release_envelope.action,
        "native_operation": campaign.release_envelope.native_operation,
        "decision_digest": campaign.decisions[1].decision_digest,
    })
    receipts = append_qualification_receipt(receipts, "EQUIVALENCE", final_record.job_id, {
        "direct_native": direct_equivalence,
        "native_run_digest": campaign.host_run.run_digest,
        "direct_run_digest": campaign.direct_run.run_digest,
    })
    receipts = append_qualification_receipt(receipts, "ADVERSARIAL", "GATEWAY", {
        "cases": adversarial_cases,
        "safely_rejected": adversarial_rejected,
        "digest": adversarial_digest,
        "duplicate": duplicate_pass,
        "conflict": conflict_pass,
        "duplicate_digest": duplicate_digest,
    })
    receipts = append_qualification_receipt(receipts, "SUMMARY", "STAGE-4", {
        "bolt_on_executed_actions": 0,
        "gateway_host_actions": gateway_actions,
        "total_native_host_actions": campaign.host_run.snapshot.applied_count,
    })
    qualification_replay = replay_qualification_receipts(receipts)
    source_unchanged = source_before == _source_snapshot()

    passed = all((
        frozen_pass,
        source_pass,
        source_unchanged,
        authority_pass,
        len(campaign.decisions) == EXPECTED_PROJECTED_REQUESTS,
        gateway_accepted == EXPECTED_GATEWAY_ACTIONS,
        gateway_rejected == 0,
        gateway_actions == EXPECTED_GATEWAY_ACTIONS,
        campaign.host_run.snapshot.applied_count == EXPECTED_TOTAL_NATIVE_ACTIONS,
        direct_equivalence,
        deterministic,
        campaign.native_replay.passed,
        observation_replay.passed,
        campaign.decision_replay.passed,
        duplicate_pass,
        conflict_pass,
        adversarial_cases == adversarial_rejected,
        final_record.state == host.DONE,
        final_record.version == 6,
        qualification_replay.passed,
    ))

    return Stage4Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        bolt_on_execution_authority=BOLT_ON_EXECUTION_AUTHORITY,
        gateway_execution_owner=GATEWAY_EXECUTION_OWNER,
        host_execution_boundary=HOST_EXECUTION_BOUNDARY,
        frozen_verification_pass=frozen_pass,
        source_bindings_pass=source_pass,
        source_unchanged=source_unchanged,
        no_hidden_authority=authority_pass,
        projected_requests=EXPECTED_PROJECTED_REQUESTS,
        gateway_permits=2,
        gateway_accepted=gateway_accepted,
        gateway_rejected=gateway_rejected,
        gateway_host_actions=gateway_actions,
        surrounding_native_actions=EXPECTED_SURROUNDING_NATIVE_ACTIONS,
        total_native_actions=campaign.host_run.snapshot.applied_count,
        bolt_on_executed_actions=0,
        direct_native_equivalence=direct_equivalence,
        deterministic_second_pass=deterministic,
        native_replay_pass=campaign.native_replay.passed,
        observation_replay_pass=observation_replay.passed,
        decision_replay_pass=campaign.decision_replay.passed,
        duplicate_rejection_pass=duplicate_pass,
        idempotency_conflict_pass=conflict_pass,
        adversarial_cases=adversarial_cases,
        adversarial_cases_safely_rejected=adversarial_rejected,
        final_state=final_record.state,
        final_version=final_record.version,
        native_run_digest=campaign.host_run.run_digest,
        native_replay_digest=campaign.native_replay.replay_digest,
        direct_run_digest=campaign.direct_run.run_digest,
        final_observation_digest=campaign.final_observation.batch_digest,
        gateway_decision_digest=campaign.decisions[-1].decision_digest,
        adversarial_digest=adversarial_digest,
        qualification_receipt_digest=receipts[-1].receipt_digest,
        qualification_replay_digest=qualification_replay.final_digest,
        projector_source_sha256=_sha256_file(PROJECTOR_PATH),
        gateway_source_sha256=_sha256_file(GATEWAY_PATH),
    )


def main() -> int:
    q = run_stage4_qualification()
    print(f"Stage: {q.stage_name} {q.stage_version}")
    print(f"Mode: {q.mode}")
    print(f"Bolt-on execution authority: {q.bolt_on_execution_authority}")
    print(f"Gateway execution owner: {q.gateway_execution_owner}")
    print(f"Host execution boundary: {q.host_execution_boundary}")
    print(f"Stage 3 commit: {EXPECTED_STAGE3_COMMIT}")
    print(f"Frozen v0.3 manifest: {EXPECTED_FROZEN_V03_MANIFEST_SHA256}")
    print(f"Frozen v0.3 entries: {EXPECTED_FROZEN_V03_ENTRIES}")
    print(f"Host: {host.HOST_FAMILY} {host.HOST_VERSION}")
    print(f"Host source: {EXPECTED_HOST_SOURCE_SHA256}")
    print(f"Observer source: {EXPECTED_OBSERVER_SOURCE_SHA256}")
    print(f"Projector source: {q.projector_source_sha256}")
    print(f"Gateway source: {q.gateway_source_sha256}")
    print(f"Portable actions: {projector_module.HOLD}, {projector_module.RELEASE}")
    print(f"Native operations: {host.PAUSE_JOB}, {host.RESUME_JOB}")
    print(f"Projected requests: {q.projected_requests}")
    print(f"Gateway permits: {q.gateway_permits}")
    print(f"Gateway accepted: {q.gateway_accepted}")
    print(f"Gateway rejected: {q.gateway_rejected}")
    print(f"Gateway host actions: {q.gateway_host_actions}")
    print(f"Surrounding native host actions: {q.surrounding_native_actions}")
    print(f"Total native host actions: {q.total_native_actions}")
    print(f"Bolt-on executed actions: {q.bolt_on_executed_actions}")
    print(f"Direct-native equivalence: {q.direct_native_equivalence}")
    print(f"Deterministic second pass: {q.deterministic_second_pass}")
    print(f"Native replay: {q.native_replay_pass}")
    print(f"Observation replay: {q.observation_replay_pass}")
    print(f"Gateway decision replay: {q.decision_replay_pass}")
    print(f"Duplicate request rejection: {q.duplicate_rejection_pass}")
    print(f"Idempotency conflict rejection: {q.idempotency_conflict_pass}")
    print(f"Adversarial cases: {q.adversarial_cases}")
    print(f"Adversarial cases safely rejected: {q.adversarial_cases_safely_rejected}")
    print(f"Final state: {q.final_state}")
    print(f"Final version: {q.final_version}")
    print(f"Native run digest: {q.native_run_digest}")
    print(f"Native replay digest: {q.native_replay_digest}")
    print(f"Direct run digest: {q.direct_run_digest}")
    print(f"Final observation digest: {q.final_observation_digest}")
    print(f"Gateway decision digest: {q.gateway_decision_digest}")
    print(f"Adversarial digest: {q.adversarial_digest}")
    print(f"Qualification receipt digest: {q.qualification_receipt_digest}")
    print(f"Qualification replay digest: {q.qualification_replay_digest}")
    print("STAGE 4 HOST-OWNED BOUNDED COMMAND GATEWAY: PASS" if q.passed else "STAGE 4 HOST-OWNED BOUNDED COMMAND GATEWAY: FAIL")
    return 0 if q.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
