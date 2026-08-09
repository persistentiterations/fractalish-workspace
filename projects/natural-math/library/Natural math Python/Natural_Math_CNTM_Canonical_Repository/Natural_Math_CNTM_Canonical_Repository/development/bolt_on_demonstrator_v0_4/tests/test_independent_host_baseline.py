from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
HOST_PATH = PROJECT / "hosts" / "ordinary_job_service.py"
QUAL_PATH = PROJECT / "integration" / "independent_host_baseline.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


host = load("test_v04_stage2_host", HOST_PATH)
qual = load("test_v04_stage2_qualification", QUAL_PATH)


class ConstantTests(unittest.TestCase):
    pass


CONSTANT_CASES = (
    ("host_family", lambda: host.HOST_FAMILY, "ORDINARY VERSIONED JOB SERVICE"),
    ("host_version", lambda: host.HOST_VERSION, "1.0"),
    ("integration_api", lambda: host.INTEGRATION_API, "JOB-SERVICE-READ-COMMAND-1"),
    ("authority", lambda: host.AUTHORITY_TOKEN, "LOCAL_JOB_SERVICE_AUTHORITY"),
    ("operation_count", lambda: len(host.NATIVE_OPERATIONS), 7),
    ("first_operation", lambda: host.NATIVE_OPERATIONS[0], host.REGISTER_JOB),
    ("last_operation", lambda: host.NATIVE_OPERATIONS[-1], host.CANCEL_JOB),
    ("terminal_states", lambda: host.TERMINAL_STATES, (host.DONE, host.CANCELLED)),
    ("stage_version", lambda: qual.STAGE_VERSION, "0.4.2"),
    ("execution_authority", lambda: qual.BOLT_ON_EXECUTION_AUTHORITY, "NONE"),
)


def _constant_test(getter, expected):
    def test(self):
        self.assertEqual(getter(), expected)
    return test


for name, getter, expected in CONSTANT_CASES:
    setattr(ConstantTests, f"test_{name}", _constant_test(getter, expected))


class CommandTests(unittest.TestCase):
    pass


def command_case(name, builder, expected_valid, expected_reason):
    def test(self):
        command = builder()
        valid, reason = host.validate_command(command)
        self.assertEqual(valid, expected_valid)
        self.assertEqual(reason, expected_reason)
    setattr(CommandTests, f"test_{name}", test)


valid = lambda: host.make_command(host.REGISTER_JOB, "J", 0, "K")
command_case("valid", valid, True, "VALID")
command_case("unknown", lambda: host.make_command("UNKNOWN", "J", 0, "K"), False, "UNKNOWN_OPERATION")
command_case("bad_id", lambda: replace(valid(), command_id="CMD-BAD"), False, "COMMAND_ID_MISMATCH")
command_case("bad_digest", lambda: replace(valid(), command_digest="0" * 64), False, "COMMAND_DIGEST_MISMATCH")
command_case("nondigest", lambda: replace(valid(), command_digest="x"), False, "COMMAND_DIGEST_INVALID")
command_case("bool_version", lambda: replace(valid(), expected_version=True), False, "COMMAND_FIELDS_INVALID")
command_case("negative_version", lambda: replace(valid(), expected_version=-1), False, "COMMAND_FIELDS_INVALID")
command_case("empty_job", lambda: replace(valid(), job_id=""), False, "COMMAND_FIELDS_INVALID")
command_case("empty_key", lambda: replace(valid(), idempotency_key=""), False, "COMMAND_FIELDS_INVALID")
command_case("empty_token", lambda: replace(valid(), authority_token=""), False, "COMMAND_FIELDS_INVALID")
command_case("duplicate_payload", lambda: replace(valid(), payload=(("a", "1"), ("a", "2"))), False, "COMMAND_FIELDS_INVALID")
command_case("wrong_type", lambda: object(), False, "COMMAND_TYPE_INVALID")


class TransitionTests(unittest.TestCase):
    pass


def run_ops(ops):
    service = host.NativeJobService()
    receipts = []
    for operation, version, key, payload in ops:
        receipts.append(service.submit(host.make_command(operation, "J", version, key, payload=payload)))
    return service, receipts


TRANSITION_CASES = (
    ("register", [(host.REGISTER_JOB, 0, "1", None)], True, host.READY, 1),
    ("start", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None)], True, host.RUNNING, 2),
    ("checkpoint", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None), (host.CHECKPOINT_JOB, 2, "3", {"checkpoint": "C"})], True, host.RUNNING, 3),
    ("pause", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None), (host.PAUSE_JOB, 2, "3", None)], True, host.PAUSED, 3),
    ("resume", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None), (host.PAUSE_JOB, 2, "3", None), (host.RESUME_JOB, 3, "4", None)], True, host.RUNNING, 4),
    ("complete", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None), (host.COMPLETE_JOB, 2, "3", None)], True, host.DONE, 3),
    ("cancel_ready", [(host.REGISTER_JOB, 0, "1", None), (host.CANCEL_JOB, 1, "2", None)], True, host.CANCELLED, 2),
    ("start_running_rejected", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None), (host.START_JOB, 2, "3", None)], False, host.RUNNING, 2),
    ("resume_running_rejected", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None), (host.RESUME_JOB, 2, "3", None)], False, host.RUNNING, 2),
    ("pause_ready_rejected", [(host.REGISTER_JOB, 0, "1", None), (host.PAUSE_JOB, 1, "2", None)], False, host.READY, 1),
    ("checkpoint_missing_rejected", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 1, "2", None), (host.CHECKPOINT_JOB, 2, "3", None)], False, host.RUNNING, 2),
    ("stale_rejected", [(host.REGISTER_JOB, 0, "1", None), (host.START_JOB, 0, "2", None)], False, host.READY, 1),
    ("terminal_rejected", [(host.REGISTER_JOB, 0, "1", None), (host.CANCEL_JOB, 1, "2", None), (host.START_JOB, 2, "3", None)], False, host.CANCELLED, 2),
    ("missing_rejected", [(host.START_JOB, 0, "1", None)], False, None, 0),
)


def _transition_test(ops, expected_applied, expected_state, expected_version):
    def test(self):
        service, receipts = run_ops(ops)
        self.assertEqual(receipts[-1].applied, expected_applied)
        snapshot = service.snapshot()
        if expected_state is None:
            self.assertEqual(snapshot.records, ())
        else:
            self.assertEqual(snapshot.records[0].state, expected_state)
            self.assertEqual(snapshot.records[0].version, expected_version)
    return test


for name, ops, applied, state, version in TRANSITION_CASES:
    setattr(TransitionTests, f"test_{name}", _transition_test(ops, applied, state, version))


class ReplayTests(unittest.TestCase):
    def test_baseline_replay(self):
        run = host.build_native_baseline()
        self.assertTrue(host.replay_run(run).passed)

    def test_baseline_deterministic(self):
        self.assertEqual(host.build_native_baseline(), host.build_native_baseline())

    def test_rejection_replay(self):
        self.assertTrue(host.replay_run(host.build_rejection_campaign()).passed)

    def test_rejection_deterministic(self):
        self.assertEqual(host.build_rejection_campaign(), host.build_rejection_campaign())

    def test_receipt_tamper(self):
        run = host.build_native_baseline()
        rows = list(run.receipts)
        rows[0] = replace(rows[0], after_state=host.PAUSED)
        self.assertFalse(host.replay_run(replace(run, receipts=tuple(rows))).passed)

    def test_receipt_reorder(self):
        run = host.build_native_baseline()
        rows = list(run.receipts)
        rows[1], rows[2] = rows[2], rows[1]
        self.assertFalse(host.replay_run(replace(run, receipts=tuple(rows))).passed)

    def test_command_tamper(self):
        run = host.build_native_baseline()
        rows = list(run.commands)
        rows[0] = replace(rows[0], job_id="OTHER")
        self.assertFalse(host.replay_run(replace(run, commands=tuple(rows))).passed)

    def test_run_digest_tamper(self):
        run = host.build_native_baseline()
        self.assertFalse(host.replay_run(replace(run, run_digest="0" * 64)).passed)

    def test_snapshot_tamper(self):
        run = host.build_native_baseline()
        snap = replace(run.snapshot, applied_count=5)
        self.assertFalse(host.replay_run(replace(run, snapshot=snap)).passed)

    def test_count_mismatch(self):
        run = host.build_native_baseline()
        self.assertFalse(host.replay_run(replace(run, receipts=run.receipts[:-1])).passed)

    def test_wrong_run_type(self):
        self.assertFalse(host.replay_run(object()).passed)

    def test_semantic_rehash(self):
        run = host.build_native_baseline()
        rows = list(run.receipts)
        forged = replace(rows[-1], applied=False, reason="REJECTED")
        forged = replace(forged, receipt_digest=host._digest_json(forged.unsigned_record()))
        rows[-1] = forged
        self.assertFalse(host.replay_run(replace(run, receipts=tuple(rows))).passed)


class RejectionTests(unittest.TestCase):
    pass

REJECTION_REASONS = (
    "UNKNOWN_OPERATION",
    "JOB_NOT_FOUND",
    "EXPECTED_VERSION_MISMATCH",
    "AUTHORITY_TOKEN_REJECTED",
    "INVALID_STATE_TRANSITION",
    "CHECKPOINT_REQUIRED",
    "JOB_ALREADY_EXISTS",
    "DUPLICATE_IDEMPOTENCY_KEY",
    "IDEMPOTENCY_KEY_CONFLICT",
    "TERMINAL_STATE",
)


def _rejection_reason_test(reason):
    def test(self):
        run = host.build_rejection_campaign()
        self.assertIn(reason, {receipt.reason for receipt in run.receipts if not receipt.applied})
    return test


for reason in REJECTION_REASONS:
    setattr(RejectionTests, f"test_reason_{reason.lower()}", _rejection_reason_test(reason))


class QualificationReceiptTests(unittest.TestCase):
    def build(self):
        rows = ()
        rows = qual.append_qualification_receipt(rows, "A", "1", {"x": 1})
        rows = qual.append_qualification_receipt(rows, "SUMMARY", "STAGE-2", {
            "bolt_on_executed_actions": 0,
            "native_host_actions": 6,
            "rejection_cases_safely_rejected": 15,
        })
        return rows

    def test_replay(self):
        self.assertTrue(qual.replay_qualification_receipts(self.build()).passed)

    def test_final_digest(self):
        rows = self.build()
        self.assertEqual(qual.replay_qualification_receipts(rows).final_digest, rows[-1].receipt_digest)

    def test_type_rejected(self):
        self.assertFalse(qual.replay_qualification_receipts((object(),)).passed)

    def test_sequence_rejected(self):
        rows = list(self.build())
        rows[0] = replace(rows[0], sequence=2)
        self.assertFalse(qual.replay_qualification_receipts(rows).passed)

    def test_chain_rejected(self):
        rows = list(self.build())
        rows[1] = replace(rows[1], previous_digest="0" * 64)
        self.assertFalse(qual.replay_qualification_receipts(rows).passed)

    def test_payload_rejected(self):
        rows = list(self.build())
        rows[0] = replace(rows[0], payload="{")
        rows[0] = replace(rows[0], receipt_digest=qual._digest_json(rows[0].unsigned_record()))
        self.assertFalse(qual.replay_qualification_receipts(rows).passed)

    def test_summary_semantics_rejected(self):
        rows = list(self.build())
        forged = replace(rows[-1], payload=qual._canonical_json({
            "bolt_on_executed_actions": 1,
            "native_host_actions": 6,
            "rejection_cases_safely_rejected": 15,
        }))
        forged = replace(forged, receipt_digest=qual._digest_json(forged.unsigned_record()))
        rows[-1] = forged
        self.assertFalse(qual.replay_qualification_receipts(rows).passed)

    def test_deterministic(self):
        self.assertEqual(self.build(), self.build())


class HarnessTests(unittest.TestCase):
    def test_independence_scan(self):
        passed, hits = qual.structural_independence_scan()
        self.assertTrue(passed, hits)
        self.assertEqual(qual._sha256_file(qual.HOST_PATH), qual.EXPECTED_HOST_SOURCE_SHA256)

    def test_stage1_source_hash(self):
        self.assertEqual(qual._sha256_file(qual.STAGE1_PATH), qual.EXPECTED_STAGE1_SOURCE_SHA256)

    def test_host_baseline_counts(self):
        run = host.build_native_baseline()
        self.assertEqual((len(run.commands), run.snapshot.applied_count, run.snapshot.rejected_count), (6, 6, 0))

    def test_rejection_counts(self):
        run = host.build_rejection_campaign()
        self.assertEqual((len(run.commands), run.snapshot.applied_count, run.snapshot.rejected_count), (19, 4, 15))

    def test_full_qualification_with_environment_gates(self):
        with patch.object(qual, "verify_frozen_v03_release", return_value=(True, "VALID", 20)), \
             patch.object(qual, "validate_stage1_baseline", return_value=(True, "PASS")):
            result = qual.run_stage2_qualification()
        self.assertTrue(result.passed)
        self.assertEqual(result.qualification_receipt_digest, result.qualification_replay_digest)

    def test_full_qualification_fails_stage1(self):
        with patch.object(qual, "verify_frozen_v03_release", return_value=(True, "VALID", 20)), \
             patch.object(qual, "validate_stage1_baseline", return_value=(False, "FAIL")):
            result = qual.run_stage2_qualification()
        self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main()
