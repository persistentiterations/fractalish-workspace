from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "portability"
    / "cross_host_replay.py"
)
SPEC = importlib.util.spec_from_file_location("cross_host_replay", MODULE_PATH)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


def make_frozen_fixture(root: Path) -> tuple[Path, str]:
    release = root / "frozen" / "bolt_on" / "v0.2"
    (release / "authority").mkdir(parents=True)
    (release / "README.md").write_text("frozen\n", encoding="utf-8", newline="\n")
    (release / "authority" / "contract.py").write_text(
        "HOLD='HOLD'\nRELEASE='RELEASE'\n", encoding="utf-8", newline="\n"
    )
    files = [release / "README.md", release / "authority" / "contract.py"]
    rows = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(release).as_posix()}"
        for path in files
    ]
    manifest = release / "RELEASE_MANIFEST_SHA256.txt"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return release, hashlib.sha256(manifest.read_bytes()).hexdigest()


class CrossHostReplayTests(unittest.TestCase):
    def setUp(self):
        self.queue_raw = M.contract._fixture_inputs()[0]
        self.workflow_run = M.workflow_host.run_workflow(M.workflow_host.baseline_commands())
        self.queue = M.project_host(
            M.QueueCrossHostAdapter(),
            self.queue_raw,
            M._queue_host_digest(self.queue_raw),
        )
        self.workflow = M.project_host(
            M.WorkflowCrossHostAdapter(),
            self.workflow_run.events,
            self.workflow_run.run_digest,
        )

    def test_stage_identity(self):
        self.assertEqual(M.STAGE_NAME, "EQUIVALENT-EVENT CROSS-HOST REPLAY")
        self.assertEqual(M.STAGE_VERSION, "0.3.3")

    def test_execution_authority_none(self):
        self.assertEqual(M.EXECUTION_AUTHORITY, "NONE")
        for name in ("execute", "apply", "dispatch", "mutate_host"):
            self.assertFalse(hasattr(M.CrossHostSemanticAdapter, name))

    def test_portable_event_builder_deterministic(self):
        first = M.build_portable_event(
            sequence=1,
            semantic_id="P1",
            event_type=M.ACTIVATED,
            subject_id="S",
            state_before=M.READY,
            state_after=M.ACTIVE,
            action=M.contract.HOLD,
        )
        second = M.build_portable_event(
            sequence=1,
            semantic_id="P1",
            event_type=M.ACTIVATED,
            subject_id="S",
            state_before=M.READY,
            state_after=M.ACTIVE,
            action=M.contract.HOLD,
        )
        self.assertEqual(first, second)

    def test_portable_event_boolean_sequence_rejected(self):
        with self.assertRaises(TypeError):
            M.build_portable_event(
                sequence=True,
                semantic_id="P1",
                event_type=M.ACTIVATED,
                subject_id="S",
                state_before=M.READY,
                state_after=M.ACTIVE,
                action=M.contract.HOLD,
            )

    def test_portable_event_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            M.build_portable_event(
                sequence=1,
                semantic_id="P1",
                event_type="DELETE",
                subject_id="S",
                state_before=M.READY,
                state_after=M.ACTIVE,
                action=M.contract.HOLD,
            )

    def test_portable_event_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            M.build_portable_event(
                sequence=1,
                semantic_id="P1",
                event_type=M.ACTIVATED,
                subject_id="S",
                state_before="UNKNOWN",
                state_after=M.ACTIVE,
                action=M.contract.HOLD,
            )

    def test_portable_event_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            M.build_portable_event(
                sequence=1,
                semantic_id="P1",
                event_type=M.ACTIVATED,
                subject_id="S",
                state_before=M.READY,
                state_after=M.ACTIVE,
                action="DELETE",
            )

    def test_portable_event_digest_tamper_rejected(self):
        event = self.queue.portable_events[0]
        valid, reason = M.validate_portable_event(replace(event, subject_id="OTHER"))
        self.assertFalse(valid)
        self.assertEqual(reason, "PORTABLE_EVENT_DIGEST_MISMATCH")

    def test_evidence_binding_deterministic(self):
        event = self.queue.portable_events[0]
        first = M.build_evidence_binding(
            host_id="H",
            host_family="F",
            host_run_digest="a" * 64,
            raw_event_digest="b" * 64,
            portable_event=event,
            source_sequence=1,
        )
        second = M.build_evidence_binding(
            host_id="H",
            host_family="F",
            host_run_digest="a" * 64,
            raw_event_digest="b" * 64,
            portable_event=event,
            source_sequence=1,
        )
        self.assertEqual(first, second)

    def test_evidence_binding_invalid_digest_rejected(self):
        with self.assertRaises(ValueError):
            M.build_evidence_binding(
                host_id="H",
                host_family="F",
                host_run_digest="bad",
                raw_event_digest="b" * 64,
                portable_event=self.queue.portable_events[0],
                source_sequence=1,
            )

    def test_evidence_binding_digest_tamper_rejected(self):
        binding = self.queue.evidence_bindings[0]
        valid, reason = M.validate_evidence_binding(replace(binding, host_id="OTHER"))
        self.assertFalse(valid)
        self.assertEqual(reason, "EVIDENCE_BINDING_DIGEST_MISMATCH")

    def test_queue_projection_passes(self):
        self.assertTrue(self.queue.passed)
        self.assertEqual(self.queue.executed_actions, 0)

    def test_workflow_projection_passes(self):
        self.assertTrue(self.workflow.passed)
        self.assertEqual(self.workflow.executed_actions, 0)

    def test_missing_adapter_fails_closed(self):
        report = M.project_host(None, (), "a" * 64)
        self.assertFalse(report.passed)
        self.assertEqual(report.first_error, "NO_CROSS_HOST_ADAPTER")

    def test_queue_requires_two_events(self):
        report = M.project_host(
            M.QueueCrossHostAdapter(),
            self.queue_raw[:1],
            M._queue_host_digest(self.queue_raw[:1]),
        )
        self.assertFalse(report.passed)
        self.assertEqual(report.first_error, "CROSS_HOST_PROJECTION_EXCEPTION")

    def test_queue_wrong_order_rejected(self):
        raw = (self.queue_raw[1], self.queue_raw[0])
        report = M.project_host(
            M.QueueCrossHostAdapter(), raw, M._queue_host_digest(raw)
        )
        self.assertFalse(report.passed)

    def test_workflow_missing_checkpoint_rejected(self):
        events = tuple(
            event
            for event in self.workflow_run.events
            if event.operation != M.workflow_host.CHECKPOINT
        )
        report = M.project_host(
            M.WorkflowCrossHostAdapter(), events, self.workflow_run.run_digest
        )
        self.assertFalse(report.passed)

    def test_workflow_rejected_events_ignored(self):
        bad_commands = M.workflow_host.baseline_commands() + (
            M.workflow_host.WorkflowCommand(
                "CMD-X", "TASK-7", M.workflow_host.START, 4
            ),
        )
        run = M.workflow_host.run_workflow(bad_commands)
        report = M.project_host(M.WorkflowCrossHostAdapter(), run.events, run.run_digest)
        self.assertTrue(report.passed)

    def test_semantic_events_identical(self):
        self.assertEqual(self.queue.portable_events, self.workflow.portable_events)

    def test_semantic_stream_digest_identical(self):
        self.assertEqual(
            self.queue.semantic_stream_digest, self.workflow.semantic_stream_digest
        )

    def test_portable_receipts_identical(self):
        self.assertEqual(self.queue.portable_receipts, self.workflow.portable_receipts)

    def test_portable_ledger_digest_identical(self):
        self.assertEqual(
            self.queue.portable_ledger_digest, self.workflow.portable_ledger_digest
        )

    def test_evidence_bindings_distinct(self):
        self.assertNotEqual(self.queue.evidence_bindings, self.workflow.evidence_bindings)

    def test_evidence_ledgers_distinct(self):
        self.assertNotEqual(
            self.queue.evidence_ledger_digest, self.workflow.evidence_ledger_digest
        )

    def test_host_run_digests_distinct(self):
        self.assertNotEqual(self.queue.host_run_digest, self.workflow.host_run_digest)

    def test_portable_replay_passes(self):
        replay = M.replay_portable_receipts(self.queue.portable_receipts)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.final_state, M.AT_CONTROL_POINT)
        self.assertEqual(replay.actions, (M.contract.HOLD, M.contract.RELEASE))

    def test_cross_host_replay_results_identical(self):
        self.assertEqual(self.queue.portable_replay, self.workflow.portable_replay)

    def test_evidence_replay_passes(self):
        self.assertTrue(M.replay_evidence_receipts(self.queue.evidence_receipts).passed)
        self.assertTrue(M.replay_evidence_receipts(self.workflow.evidence_receipts).passed)

    def test_portable_payload_tamper_detected(self):
        receipts = list(self.queue.portable_receipts)
        receipts[1] = replace(receipts[1], payload="tampered")
        self.assertFalse(M.replay_portable_receipts(tuple(receipts)).passed)

    def test_evidence_payload_tamper_detected(self):
        receipts = list(self.queue.evidence_receipts)
        receipts[1] = replace(receipts[1], payload="tampered")
        self.assertFalse(M.replay_evidence_receipts(tuple(receipts)).passed)

    def test_portable_reorder_detected(self):
        receipts = list(self.queue.portable_receipts)
        receipts[1], receipts[2] = receipts[2], receipts[1]
        self.assertFalse(M.replay_portable_receipts(tuple(receipts)).passed)

    def test_evidence_reorder_detected(self):
        receipts = list(self.queue.evidence_receipts)
        receipts[1], receipts[2] = receipts[2], receipts[1]
        self.assertFalse(M.replay_evidence_receipts(tuple(receipts)).passed)

    def test_empty_portable_stream_rejected(self):
        self.assertFalse(M.replay_portable_receipts(()).passed)

    def test_empty_evidence_stream_rejected(self):
        self.assertFalse(M.replay_evidence_receipts(()).passed)

    def test_portable_summary_execution_claim_rejected_even_rehashed(self):
        receipts = list(self.queue.portable_receipts)
        summary = json.loads(receipts[-1].payload)
        summary["executed_actions"] = 1
        receipts[-1] = replace(receipts[-1], payload=M._canonical_json(summary))
        replay = M.replay_portable_receipts(M._rehash_receipts(receipts))
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "PORTABLE_SUMMARY_MISMATCH")

    def test_evidence_summary_execution_claim_rejected_even_rehashed(self):
        receipts = list(self.queue.evidence_receipts)
        summary = json.loads(receipts[-1].payload)
        summary["executed_actions"] = 1
        receipts[-1] = replace(receipts[-1], payload=M._canonical_json(summary))
        replay = M.replay_evidence_receipts(M._rehash_receipts(receipts))
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "EVIDENCE_SUMMARY_MISMATCH")

    def test_illegal_transition_rejected_even_rehashed(self):
        receipts = list(self.queue.portable_receipts)
        payload = json.loads(receipts[2].payload)
        payload["state_before"] = M.READY
        unsigned = {key: value for key, value in payload.items() if key != "semantic_digest"}
        payload["semantic_digest"] = M._digest_json(unsigned)
        receipts[2] = replace(receipts[2], payload=M._canonical_json(payload))
        replay = M.replay_portable_receipts(M._rehash_receipts(receipts))
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "ILLEGAL_PORTABLE_TRANSITION")

    def test_subject_change_rejected_even_rehashed(self):
        receipts = list(self.queue.portable_receipts)
        payload = json.loads(receipts[2].payload)
        payload["subject_id"] = "OTHER"
        unsigned = {key: value for key, value in payload.items() if key != "semantic_digest"}
        payload["semantic_digest"] = M._digest_json(unsigned)
        receipts[2] = replace(receipts[2], payload=M._canonical_json(payload))
        replay = M.replay_portable_receipts(M._rehash_receipts(receipts))
        self.assertFalse(replay.passed)
        self.assertEqual(replay.first_error, "PORTABLE_SUBJECT_MISMATCH")

    def test_duplicate_portable_id_rejected(self):
        class Duplicate(M.QueueCrossHostAdapter):
            def project(self, raw_events, host_run_digest):
                events, bindings = super().project(raw_events, host_run_digest)
                second = replace(events[1], semantic_id=events[0].semantic_id)
                return (events[0], second), bindings

        report = M.project_host(
            Duplicate(), self.queue_raw, M._queue_host_digest(self.queue_raw)
        )
        self.assertFalse(report.passed)
        self.assertEqual(report.first_error, "DUPLICATE_PORTABLE_SEMANTIC_ID")

    def test_evidence_semantic_mismatch_rejected(self):
        class Mismatch(M.QueueCrossHostAdapter):
            def project(self, raw_events, host_run_digest):
                events, bindings = super().project(raw_events, host_run_digest)
                return events, (replace(bindings[0], portable_semantic_digest="f" * 64), bindings[1])

        report = M.project_host(
            Mismatch(), self.queue_raw, M._queue_host_digest(self.queue_raw)
        )
        self.assertFalse(report.passed)

    def test_portable_receipt_boundary_rejected(self):
        receipts = list(self.queue.portable_receipts)
        receipts[0] = replace(receipts[0], kind="OTHER")
        self.assertFalse(M.replay_portable_receipts(M._rehash_receipts(receipts)).passed)

    def test_evidence_receipt_boundary_rejected(self):
        receipts = list(self.queue.evidence_receipts)
        receipts[0] = replace(receipts[0], kind="OTHER")
        self.assertFalse(M.replay_evidence_receipts(M._rehash_receipts(receipts)).passed)

    def test_source_hash_bindings_match_stage1_and_stage2(self):
        source_map = dict(M._source_snapshot())
        self.assertEqual(
            source_map[M.CONTRACT_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()],
            M.EXPECTED_STAGE1_SOURCE_SHA256,
        )
        self.assertEqual(
            source_map[M.STAGE2_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()],
            M.EXPECTED_STAGE2_SOURCE_SHA256,
        )
        self.assertEqual(
            source_map[M.WORKFLOW_HOST_PATH.relative_to(M.REPOSITORY_ROOT).as_posix()],
            M.EXPECTED_WORKFLOW_HOST_SOURCE_SHA256,
        )

    def test_stage3_qualification_passes_with_frozen_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            result = M.run_stage3_qualification(
                frozen_root=release, expected_manifest_sha256=manifest_sha
            )
            self.assertTrue(result.passed)
            self.assertEqual(result.executed_actions, 0)
            self.assertTrue(result.portable_ledgers_identical)
            self.assertTrue(result.host_evidence_distinct)


if __name__ == "__main__":
    unittest.main()
