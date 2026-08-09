#!/usr/bin/env python3
"""Qualification harness for v0.4 Stage 2.

The host fixture remains an ordinary standalone job service.  This harness binds
that native baseline to the already-qualified Stage 1 external-host contract,
checks the frozen v0.3 release, and proves deterministic native replay without
installing an adapter or issuing any bolt-on action.
"""

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
from typing import Iterable, Sequence, Tuple

sys.dont_write_bytecode = True

STAGE_NAME = "INDEPENDENT ORDINARY HOST FIXTURE AND NATIVE BASELINE"
STAGE_VERSION = "0.4.2"
MODE = "NATIVE_HOST_BASELINE_QUALIFICATION"
BOLT_ON_EXECUTION_AUTHORITY = "NONE"
HOST_EXECUTION_BOUNDARY = "NATIVE_HOST_ONLY"
ZERO_DIGEST = "0" * 64

EXPECTED_STAGE1_COMMIT = "9a75f070265c6b0929ed72a6917f08f2cc41f209"
EXPECTED_STAGE1_SOURCE_SHA256 = "8035b10d0e68ec0365f48340366ec3bdd903a4dcc2e7b9b2574b2269c04b4806"
EXPECTED_HOST_SOURCE_SHA256 = "14a3b86d4cabee409d84904f3db4feb416be905c3c54edb3ca5ef4d50e41a797"
EXPECTED_FROZEN_V03_MANIFEST_SHA256 = "57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa"
EXPECTED_FROZEN_V03_ENTRIES = 20
EXPECTED_BASELINE_COMMANDS = 6
EXPECTED_BASELINE_APPLIED = 6
EXPECTED_BASELINE_REJECTED = 0
EXPECTED_REJECTION_COMMANDS = 19
EXPECTED_REJECTION_APPLIED = 4
EXPECTED_REJECTION_REJECTED = 15

THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPOSITORY_ROOT = THIS_FILE.parents[3]
HOST_PATH = PROJECT_DIR / "hosts" / "ordinary_job_service.py"
STAGE1_PATH = PROJECT_DIR / "integration" / "external_host_contract.py"
FROZEN_V03_ROOT = REPOSITORY_ROOT / "frozen" / "bolt_on" / "v0.3"
FROZEN_V03_MANIFEST = FROZEN_V03_ROOT / "RELEASE_MANIFEST_SHA256.txt"


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


host = _load_module("v04_stage2_ordinary_job_service", HOST_PATH)


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


def _manifest_entries(path: Path) -> Tuple[Tuple[str, str], ...]:
    rows: list[Tuple[str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or not _is_digest(parts[0]):
            raise ValueError(f"invalid manifest line {number}")
        rows.append((parts[1], parts[0]))
    if len({relative for relative, _ in rows}) != len(rows):
        raise ValueError("duplicate manifest path")
    return tuple(rows)


def verify_frozen_v03_release() -> Tuple[bool, str, int]:
    if not FROZEN_V03_ROOT.is_dir() or not FROZEN_V03_MANIFEST.is_file():
        return False, "FROZEN_V03_MISSING", 0
    if _sha256_file(FROZEN_V03_MANIFEST) != EXPECTED_FROZEN_V03_MANIFEST_SHA256:
        return False, "FROZEN_V03_MANIFEST_DIGEST_MISMATCH", 0
    try:
        entries = _manifest_entries(FROZEN_V03_MANIFEST)
    except (OSError, UnicodeError, ValueError):
        return False, "FROZEN_V03_MANIFEST_INVALID", 0
    if len(entries) != EXPECTED_FROZEN_V03_ENTRIES:
        return False, "FROZEN_V03_ENTRY_COUNT_MISMATCH", len(entries)
    expected = {relative: digest for relative, digest in entries}
    actual = {
        path.relative_to(FROZEN_V03_ROOT).as_posix()
        for path in FROZEN_V03_ROOT.rglob("*")
        if path.is_file() and path != FROZEN_V03_MANIFEST
    }
    if set(expected) != actual:
        return False, "FROZEN_V03_FILE_SET_MISMATCH", len(entries)
    for relative, digest in entries:
        if _sha256_file(FROZEN_V03_ROOT / relative) != digest:
            return False, f"FROZEN_V03_CHANGED:{relative}", len(entries)
    return True, "VALID", len(entries)


def validate_stage1_baseline() -> Tuple[bool, str]:
    if not STAGE1_PATH.is_file():
        return False, "STAGE1_MISSING"
    if _sha256_file(STAGE1_PATH) != EXPECTED_STAGE1_SOURCE_SHA256:
        return False, "STAGE1_SOURCE_DIGEST_MISMATCH"
    completed = subprocess.run(
        [sys.executable, str(STAGE1_PATH)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    output = completed.stdout + "\n" + completed.stderr
    required = (
        "Contract requirements: 37",
        "Rejection cases safely rejected: 28",
        "Host actions: 0",
        "Bolt-on executed actions: 0",
        "STAGE 1 EXTERNAL HOST INTEGRATION CONTRACT: PASS",
    )
    if completed.returncode or any(marker not in output for marker in required):
        return False, "STAGE1_QUALIFICATION_FAILED"
    return True, "PASS"


def structural_independence_scan() -> Tuple[bool, Tuple[str, ...]]:
    hits: list[str] = []
    source = HOST_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(HOST_PATH))
    allowed_roots = {"__future__", "hashlib", "json", "dataclasses", "typing"}
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
    lowered = source.lower()
    forbidden_text = (
        "natural_math",
        "cntm",
        "portable_adapter_contract",
        "external_host_contract",
        "bolt_on_demonstrator",
        "frozen/bolt_on",
    )
    for token in forbidden_text:
        if token in lowered:
            hits.append(f"FORBIDDEN_COUPLING:{token}")
    required_operations = {
        "REGISTER_JOB",
        "START_JOB",
        "CHECKPOINT_JOB",
        "PAUSE_JOB",
        "RESUME_JOB",
        "COMPLETE_JOB",
        "CANCEL_JOB",
    }
    if set(host.NATIVE_OPERATIONS) != required_operations:
        hits.append("NATIVE_OPERATION_SET_CHANGED")
    if host.HOST_FAMILY != "ORDINARY VERSIONED JOB SERVICE":
        hits.append("HOST_FAMILY_CHANGED")
    if host.HOST_VERSION != "1.0":
        hits.append("HOST_VERSION_CHANGED")
    return not hits, tuple(hits)


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
class ReceiptReplay:
    passed: bool
    reason: str
    count: int
    final_digest: str


@dataclass(frozen=True)
class Stage2Qualification:
    passed: bool
    stage_name: str
    stage_version: str
    mode: str
    bolt_on_execution_authority: str
    host_execution_boundary: str
    stage1_pass: bool
    frozen_v03_pass: bool
    frozen_v03_unchanged: bool
    frozen_v03_entries: int
    source_unchanged: bool
    independent_source: bool
    baseline_commands: int
    baseline_applied: int
    baseline_rejected: int
    baseline_final_state: str
    baseline_final_version: int
    baseline_checkpoints: int
    rejection_commands: int
    rejection_applied: int
    rejection_rejected: int
    rejection_cases_safely_rejected: int
    deterministic_second_pass: bool
    restart_replay_pass: bool
    rejection_replay_pass: bool
    receipt_tamper_detection_pass: bool
    receipt_reorder_detection_pass: bool
    semantic_rehash_detection_pass: bool
    native_host_actions: int
    bolt_on_executed_actions: int
    baseline_digest: str
    baseline_replay_digest: str
    rejection_digest: str
    qualification_receipt_digest: str
    qualification_replay_digest: str
    frozen_v03_manifest_sha256: str
    stage1_source_sha256: str
    host_source_sha256: str


def append_qualification_receipt(
    receipts: Sequence[QualificationReceipt],
    kind: str,
    subject: str,
    payload: object,
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


def replay_qualification_receipts(receipts: Iterable[QualificationReceipt]) -> ReceiptReplay:
    previous = ZERO_DIGEST
    count = 0
    for expected_sequence, receipt in enumerate(tuple(receipts), 1):
        if not isinstance(receipt, QualificationReceipt):
            return ReceiptReplay(False, "RECEIPT_TYPE_INVALID", count, previous)
        if receipt.sequence != expected_sequence:
            return ReceiptReplay(False, "RECEIPT_SEQUENCE_MISMATCH", count, previous)
        if receipt.previous_digest != previous:
            return ReceiptReplay(False, "RECEIPT_CHAIN_MISMATCH", count, previous)
        if not _is_digest(receipt.receipt_digest):
            return ReceiptReplay(False, "RECEIPT_DIGEST_INVALID", count, previous)
        if _digest_json(receipt.unsigned_record()) != receipt.receipt_digest:
            return ReceiptReplay(False, "RECEIPT_DIGEST_MISMATCH", count, previous)
        try:
            payload = json.loads(receipt.payload)
        except (TypeError, json.JSONDecodeError):
            return ReceiptReplay(False, "RECEIPT_PAYLOAD_INVALID", count, previous)
        if receipt.kind == "SUMMARY":
            required = {
                "bolt_on_executed_actions": 0,
                "native_host_actions": EXPECTED_BASELINE_APPLIED,
                "rejection_cases_safely_rejected": EXPECTED_REJECTION_REJECTED,
            }
            if any(payload.get(key) != value for key, value in required.items()):
                return ReceiptReplay(False, "SUMMARY_SEMANTICS_INVALID", count, previous)
        previous = receipt.receipt_digest
        count += 1
    return ReceiptReplay(True, "PASS", count, previous)


def _source_snapshot() -> Tuple[Tuple[str, str], ...]:
    paths = (
        PROJECT_DIR / "README.md",
        PROJECT_DIR / "README_STAGE_1.md",
        PROJECT_DIR / "README_STAGE_2.md",
        STAGE1_PATH,
        HOST_PATH,
        THIS_FILE,
        PROJECT_DIR / "tests" / "test_external_host_contract.py",
        PROJECT_DIR / "tests" / "test_independent_host_baseline.py",
    )
    return tuple(
        (path.relative_to(REPOSITORY_ROOT).as_posix(), _sha256_file(path))
        for path in paths
    )


def run_stage2_qualification() -> Stage2Qualification:
    source_before = _source_snapshot()
    frozen_pre_digest = _sha256_file(FROZEN_V03_MANIFEST) if FROZEN_V03_MANIFEST.is_file() else ZERO_DIGEST
    frozen_pre_pass, _, frozen_entries = verify_frozen_v03_release()
    stage1_pass, _ = validate_stage1_baseline()
    independent_source, _ = structural_independence_scan()

    baseline = host.build_native_baseline()
    baseline_second = host.build_native_baseline()
    baseline_replay = host.replay_run(baseline)

    rejection = host.build_rejection_campaign()
    rejection_second = host.build_rejection_campaign()
    rejection_replay = host.replay_run(rejection)

    record = baseline.snapshot.records[0]
    safely_rejected = sum(
        1
        for receipt in rejection.receipts
        if not receipt.applied
        and receipt.before_state == receipt.after_state
        and receipt.before_version == receipt.after_version
    )

    tampered_receipts = list(baseline.receipts)
    tampered_receipts[2] = replace(tampered_receipts[2], after_state=host.PAUSED)
    tampered_run = replace(baseline, receipts=tuple(tampered_receipts))
    tamper_detection = not host.replay_run(tampered_run).passed

    reordered_receipts = list(baseline.receipts)
    reordered_receipts[2], reordered_receipts[3] = reordered_receipts[3], reordered_receipts[2]
    reordered_run = replace(baseline, receipts=tuple(reordered_receipts))
    reorder_detection = not host.replay_run(reordered_run).passed

    forged_receipts = list(baseline.receipts)
    forged = replace(forged_receipts[-1], applied=False, reason="REJECTED")
    forged = replace(forged, receipt_digest=_digest_json(forged.unsigned_record()))
    forged_receipts[-1] = forged
    forged_run = replace(baseline, receipts=tuple(forged_receipts))
    semantic_rehash_detection = not host.replay_run(forged_run).passed

    receipts: Tuple[QualificationReceipt, ...] = ()
    receipts = append_qualification_receipt(receipts, "FROZEN_BASELINE", "v0.3", {
        "entries": EXPECTED_FROZEN_V03_ENTRIES,
        "manifest_sha256": EXPECTED_FROZEN_V03_MANIFEST_SHA256,
        "passed": frozen_pre_pass,
    })
    receipts = append_qualification_receipt(receipts, "STAGE1", EXPECTED_STAGE1_COMMIT, {
        "passed": stage1_pass,
        "source_sha256": EXPECTED_STAGE1_SOURCE_SHA256,
    })
    receipts = append_qualification_receipt(receipts, "HOST_SOURCE", host.HOST_FAMILY, {
        "independent": independent_source,
        "integration_api": host.INTEGRATION_API,
        "source_sha256": EXPECTED_HOST_SOURCE_SHA256,
        "version": host.HOST_VERSION,
    })
    receipts = append_qualification_receipt(receipts, "NATIVE_BASELINE", record.job_id, {
        "applied": baseline.snapshot.applied_count,
        "commands": len(baseline.commands),
        "final_state": record.state,
        "final_version": record.version,
        "rejected": baseline.snapshot.rejected_count,
        "run_digest": baseline.run_digest,
    })
    receipts = append_qualification_receipt(receipts, "REJECTION_CAMPAIGN", "JOB-ATTACK", {
        "applied": rejection.snapshot.applied_count,
        "commands": len(rejection.commands),
        "rejected": rejection.snapshot.rejected_count,
        "run_digest": rejection.run_digest,
        "safely_rejected": safely_rejected,
    })
    receipts = append_qualification_receipt(receipts, "REPLAY", "NATIVE", {
        "baseline": baseline_replay.passed,
        "rejection": rejection_replay.passed,
        "second_pass": baseline == baseline_second and rejection == rejection_second,
    })
    receipts = append_qualification_receipt(receipts, "SUMMARY", "STAGE-2", {
        "bolt_on_executed_actions": 0,
        "native_host_actions": baseline.snapshot.applied_count,
        "rejection_cases_safely_rejected": safely_rejected,
    })
    receipt_replay = replay_qualification_receipts(receipts)

    frozen_post_pass, _, frozen_post_entries = verify_frozen_v03_release()
    frozen_post_digest = _sha256_file(FROZEN_V03_MANIFEST) if FROZEN_V03_MANIFEST.is_file() else ZERO_DIGEST
    source_unchanged = source_before == _source_snapshot()
    frozen_unchanged = (
        frozen_pre_pass
        and frozen_post_pass
        and frozen_entries == frozen_post_entries
        and frozen_pre_digest == frozen_post_digest
    )
    deterministic_second = baseline == baseline_second and rejection == rejection_second

    passed = all((
        stage1_pass,
        frozen_pre_pass,
        frozen_post_pass,
        frozen_unchanged,
        frozen_entries == EXPECTED_FROZEN_V03_ENTRIES,
        independent_source,
        _sha256_file(HOST_PATH) == EXPECTED_HOST_SOURCE_SHA256,
        source_unchanged,
        len(baseline.commands) == EXPECTED_BASELINE_COMMANDS,
        baseline.snapshot.applied_count == EXPECTED_BASELINE_APPLIED,
        baseline.snapshot.rejected_count == EXPECTED_BASELINE_REJECTED,
        record.state == host.DONE,
        record.version == 6,
        record.checkpoint_count == 1,
        len(rejection.commands) == EXPECTED_REJECTION_COMMANDS,
        rejection.snapshot.applied_count == EXPECTED_REJECTION_APPLIED,
        rejection.snapshot.rejected_count == EXPECTED_REJECTION_REJECTED,
        safely_rejected == EXPECTED_REJECTION_REJECTED,
        deterministic_second,
        baseline_replay.passed,
        rejection_replay.passed,
        tamper_detection,
        reorder_detection,
        semantic_rehash_detection,
        receipt_replay.passed,
    ))

    return Stage2Qualification(
        passed=passed,
        stage_name=STAGE_NAME,
        stage_version=STAGE_VERSION,
        mode=MODE,
        bolt_on_execution_authority=BOLT_ON_EXECUTION_AUTHORITY,
        host_execution_boundary=HOST_EXECUTION_BOUNDARY,
        stage1_pass=stage1_pass,
        frozen_v03_pass=frozen_pre_pass and frozen_post_pass,
        frozen_v03_unchanged=frozen_unchanged,
        frozen_v03_entries=frozen_entries,
        source_unchanged=source_unchanged,
        independent_source=independent_source,
        baseline_commands=len(baseline.commands),
        baseline_applied=baseline.snapshot.applied_count,
        baseline_rejected=baseline.snapshot.rejected_count,
        baseline_final_state=record.state,
        baseline_final_version=record.version,
        baseline_checkpoints=record.checkpoint_count,
        rejection_commands=len(rejection.commands),
        rejection_applied=rejection.snapshot.applied_count,
        rejection_rejected=rejection.snapshot.rejected_count,
        rejection_cases_safely_rejected=safely_rejected,
        deterministic_second_pass=deterministic_second,
        restart_replay_pass=baseline_replay.passed,
        rejection_replay_pass=rejection_replay.passed,
        receipt_tamper_detection_pass=tamper_detection,
        receipt_reorder_detection_pass=reorder_detection,
        semantic_rehash_detection_pass=semantic_rehash_detection,
        native_host_actions=baseline.snapshot.applied_count,
        bolt_on_executed_actions=0,
        baseline_digest=baseline.run_digest,
        baseline_replay_digest=baseline_replay.replay_digest,
        rejection_digest=rejection.run_digest,
        qualification_receipt_digest=receipts[-1].receipt_digest,
        qualification_replay_digest=receipt_replay.final_digest,
        frozen_v03_manifest_sha256=frozen_pre_digest,
        stage1_source_sha256=_sha256_file(STAGE1_PATH),
        host_source_sha256=_sha256_file(HOST_PATH),
    )


def main() -> int:
    qualification = run_stage2_qualification()
    print(f"Stage: {qualification.stage_name} {qualification.stage_version}")
    print(f"Mode: {qualification.mode}")
    print(f"Bolt-on execution authority: {qualification.bolt_on_execution_authority}")
    print(f"Host execution boundary: {qualification.host_execution_boundary}")
    print(f"Stage 1 source: {qualification.stage1_source_sha256}")
    print(f"Frozen v0.3 manifest: {qualification.frozen_v03_manifest_sha256}")
    print(f"Frozen v0.3 entries: {qualification.frozen_v03_entries}")
    print(f"Host: {host.HOST_FAMILY} {host.HOST_VERSION}")
    print(f"Host source: {qualification.host_source_sha256}")
    print(f"Integration API: {host.INTEGRATION_API}")
    print(f"Native operations: {', '.join(host.NATIVE_OPERATIONS)}")
    print(f"Baseline commands: {qualification.baseline_commands}")
    print(f"Baseline applied: {qualification.baseline_applied}")
    print(f"Baseline rejected: {qualification.baseline_rejected}")
    print(f"Final state: {qualification.baseline_final_state}")
    print(f"Final version: {qualification.baseline_final_version}")
    print(f"Checkpoint count: {qualification.baseline_checkpoints}")
    print(f"Rejection commands: {qualification.rejection_commands}")
    print(f"Rejection applied: {qualification.rejection_applied}")
    print(f"Rejection rejected: {qualification.rejection_rejected}")
    print(f"Rejection cases safely rejected: {qualification.rejection_cases_safely_rejected}")
    print(f"Deterministic second pass: {qualification.deterministic_second_pass}")
    print(f"Restart replay: {qualification.restart_replay_pass}")
    print(f"Independent host source: {qualification.independent_source}")
    print(f"Native host actions: {qualification.native_host_actions}")
    print(f"Bolt-on executed actions: {qualification.bolt_on_executed_actions}")
    print(f"Baseline digest: {qualification.baseline_digest}")
    print(f"Baseline replay digest: {qualification.baseline_replay_digest}")
    print(f"Rejection digest: {qualification.rejection_digest}")
    print(f"Qualification receipt digest: {qualification.qualification_receipt_digest}")
    print(f"Qualification replay digest: {qualification.qualification_replay_digest}")
    if qualification.passed:
        print("STAGE 2 INDEPENDENT ORDINARY HOST BASELINE: PASS")
        return 0
    print("STAGE 2 INDEPENDENT ORDINARY HOST BASELINE: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
