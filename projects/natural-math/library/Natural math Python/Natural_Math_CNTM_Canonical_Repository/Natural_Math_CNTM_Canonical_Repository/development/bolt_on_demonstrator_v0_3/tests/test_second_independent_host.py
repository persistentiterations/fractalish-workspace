from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import os
import tempfile
import unittest
import sys

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "portability"
    / "second_independent_host.py"
)
SPEC = importlib.util.spec_from_file_location("second_independent_host", MODULE_PATH)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
assert SPEC.loader is not None
SPEC.loader.exec_module(M)
H = M.workflow_host
C = M.contract


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


class SecondIndependentHostTests(unittest.TestCase):
    def test_01_host_identity_constants(self):
        self.assertEqual(H.HOST_NAME, "DETERMINISTIC VERSIONED WORKFLOW HOST")
        self.assertEqual(H.HOST_VERSION, "1.0")

    def test_02_supported_operations_exact(self):
        self.assertEqual(
            H.SUPPORTED_OPERATIONS,
            (H.REGISTER, H.START, H.CHECKPOINT, H.PAUSE, H.RESUME, H.COMPLETE, H.CANCEL),
        )

    def test_03_baseline_commands_are_ordered(self):
        commands = H.baseline_commands()
        self.assertEqual(tuple(item.operation for item in commands), (H.REGISTER, H.START, H.CHECKPOINT, H.COMPLETE))
        self.assertEqual(tuple(item.expected_revision for item in commands), (0, 1, 2, 3))

    def test_04_baseline_run_applies_all(self):
        run = H.run_workflow(H.baseline_commands())
        self.assertEqual(run.applied_command_ids, ("CMD-001", "CMD-002", "CMD-003", "CMD-004"))
        self.assertEqual(run.rejected_command_ids, ())

    def test_05_baseline_final_record(self):
        run = H.run_workflow(H.baseline_commands())
        self.assertEqual(run.final_records, (H.WorkflowRecord("TASK-7", H.DONE, 4),))

    def test_06_run_is_deterministic(self):
        self.assertEqual(H.run_workflow(H.baseline_commands()), H.run_workflow(H.baseline_commands()))

    def test_07_input_is_unchanged(self):
        commands = H.baseline_commands()
        before = repr(commands)
        H.run_workflow(commands)
        self.assertEqual(before, repr(commands))

    def test_08_command_is_frozen(self):
        command = H.baseline_commands()[0]
        with self.assertRaises(FrozenInstanceError):
            command.operation = H.START

    def test_09_duplicate_command_ids_rejected(self):
        commands = (
            H.WorkflowCommand("DUP", "A", H.REGISTER, 0),
            H.WorkflowCommand("DUP", "B", H.REGISTER, 0),
        )
        run = H.run_workflow(commands)
        self.assertEqual(tuple(item.reason for item in run.events), ("DUPLICATE_COMMAND_ID", "DUPLICATE_COMMAND_ID"))

    def test_10_empty_command_id_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("", "A", H.REGISTER, 0),))
        self.assertEqual(run.events[0].reason, "EMPTY_COMMAND_ID")

    def test_11_empty_task_id_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("C", "", H.REGISTER, 0),))
        self.assertEqual(run.events[0].reason, "EMPTY_TASK_ID")

    def test_12_unsupported_operation_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("C", "A", "DELETE", 0),))
        self.assertEqual(run.events[0].reason, "UNSUPPORTED_OPERATION")

    def test_13_boolean_revision_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("C", "A", H.REGISTER, True),))
        self.assertEqual(run.events[0].reason, "REVISION_NOT_INTEGER")

    def test_14_negative_revision_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("C", "A", H.REGISTER, -1),))
        self.assertEqual(run.events[0].reason, "NEGATIVE_REVISION")

    def test_15_register_transition(self):
        run = H.run_workflow((H.WorkflowCommand("C1", "A", H.REGISTER, 0),))
        event = run.events[0]
        self.assertEqual((event.state_before, event.state_after, event.revision_after), (H.ABSENT, H.READY, 1))

    def test_16_start_transition(self):
        run = H.run_workflow((H.WorkflowCommand("C1", "A", H.REGISTER, 0), H.WorkflowCommand("C2", "A", H.START, 1)))
        self.assertEqual(run.events[1].state_after, H.RUNNING)

    def test_17_checkpoint_preserves_state_and_advances_revision(self):
        run = H.run_workflow(H.baseline_commands()[:3])
        event = run.events[2]
        self.assertEqual((event.state_before, event.state_after), (H.RUNNING, H.RUNNING))
        self.assertEqual((event.revision_before, event.revision_after), (2, 3))

    def test_18_pause_resume_transitions(self):
        commands = (
            H.WorkflowCommand("1", "A", H.REGISTER, 0),
            H.WorkflowCommand("2", "A", H.START, 1),
            H.WorkflowCommand("3", "A", H.PAUSE, 2),
            H.WorkflowCommand("4", "A", H.RESUME, 3),
        )
        run = H.run_workflow(commands)
        self.assertEqual(tuple(item.state_after for item in run.events), (H.READY, H.RUNNING, H.PAUSED, H.RUNNING))

    def test_19_complete_transition(self):
        run = H.run_workflow(H.baseline_commands())
        self.assertEqual(run.events[-1].state_after, H.DONE)

    def test_20_cancel_from_ready(self):
        run = H.run_workflow((H.WorkflowCommand("1", "A", H.REGISTER, 0), H.WorkflowCommand("2", "A", H.CANCEL, 1)))
        self.assertEqual(run.final_records[0].state, H.CANCELLED)

    def test_21_cancel_from_running(self):
        commands = (H.WorkflowCommand("1", "A", H.REGISTER, 0), H.WorkflowCommand("2", "A", H.START, 1), H.WorkflowCommand("3", "A", H.CANCEL, 2))
        self.assertEqual(H.run_workflow(commands).final_records[0].state, H.CANCELLED)

    def test_22_cancel_from_paused(self):
        commands = (H.WorkflowCommand("1", "A", H.REGISTER, 0), H.WorkflowCommand("2", "A", H.START, 1), H.WorkflowCommand("3", "A", H.PAUSE, 2), H.WorkflowCommand("4", "A", H.CANCEL, 3))
        self.assertEqual(H.run_workflow(commands).final_records[0].state, H.CANCELLED)

    def test_23_missing_record_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("1", "A", H.START, 0),))
        self.assertEqual(run.events[0].reason, "RECORD_NOT_FOUND")

    def test_24_register_existing_record_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("1", "A", H.REGISTER, 0), H.WorkflowCommand("2", "A", H.REGISTER, 1)))
        self.assertEqual(run.events[1].reason, "RECORD_ALREADY_EXISTS")

    def test_25_revision_mismatch_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("1", "A", H.REGISTER, 0), H.WorkflowCommand("2", "A", H.START, 9)))
        self.assertEqual(run.events[1].reason, "REVISION_MISMATCH")

    def test_26_illegal_transition_rejected(self):
        run = H.run_workflow((H.WorkflowCommand("1", "A", H.REGISTER, 0), H.WorkflowCommand("2", "A", H.COMPLETE, 1)))
        self.assertEqual(run.events[1].reason, "ILLEGAL_TRANSITION")

    def test_27_final_records_are_sorted(self):
        run = H.run_workflow((H.WorkflowCommand("1", "B", H.REGISTER, 0), H.WorkflowCommand("2", "A", H.REGISTER, 0)))
        self.assertEqual(tuple(item.task_id for item in run.final_records), ("A", "B"))

    def test_28_digest_matches_canonical_text(self):
        run = H.run_workflow(H.baseline_commands())
        self.assertEqual(hashlib.sha256(run.canonical_text().encode("utf-8")).hexdigest(), run.run_digest)

    def test_29_host_writes_no_files(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                H.run_workflow(H.baseline_commands())
                self.assertEqual(list(Path(directory).iterdir()), [])
            finally:
                os.chdir(previous)

    def test_30_host_is_independent(self):
        self.assertTrue(M._host_independent())

    def test_31_host_is_materially_different(self):
        self.assertTrue(M._materially_different())

    def test_32_adapter_identity_is_valid(self):
        adapter = M.WorkflowStateAdapter()
        valid, reason = C.validate_adapter_identity(adapter.identity())
        self.assertTrue(valid, reason)
        self.assertEqual(adapter.identity().host_family, "VERSIONED_FINITE_STATE_WORKFLOW")

    def test_33_adapter_normalizes_workflow_event(self):
        adapter = M.WorkflowStateAdapter()
        event = adapter.normalize_event(H.run_workflow(H.baseline_commands()).events[0])
        self.assertEqual(event.subject_id, "TASK-7")
        self.assertEqual(event.event_type, H.APPLIED)

    def test_34_adapter_rejects_wrong_raw_type(self):
        with self.assertRaises(TypeError):
            M.WorkflowStateAdapter().normalize_event({"sequence": 1})

    def test_35_hold_projects_to_pause_without_execution(self):
        adapter = M.WorkflowStateAdapter()
        run = H.run_workflow(H.baseline_commands())
        requests = M._requests_for(adapter, run)
        events = tuple(adapter.normalize_event(item) for item in run.events)
        projection = adapter.project_action(requests[0], events[1])
        self.assertEqual(projection.host_operation, H.PAUSE)
        self.assertFalse(projection.executed)

    def test_36_release_projects_to_resume_without_execution(self):
        adapter = M.WorkflowStateAdapter()
        run = H.run_workflow(H.baseline_commands())
        requests = M._requests_for(adapter, run)
        events = tuple(adapter.normalize_event(item) for item in run.events)
        projection = adapter.project_action(requests[1], events[2])
        self.assertEqual(projection.host_operation, H.RESUME)
        self.assertFalse(projection.executed)

    def test_37_rejected_source_event_abstains(self):
        adapter = M.WorkflowStateAdapter()
        raw = H.run_workflow((H.WorkflowCommand("1", "A", H.START, 0),)).events[0]
        event = adapter.normalize_event(raw)
        request = C.build_action_request(
            request_id=1,
            action=C.HOLD,
            subject_id=event.subject_id,
            source_event_digest=event.event_digest,
            governance_session_digest="a" * 64,
            authority_digest="b" * 64,
            expected_state_digest=event.state_after_digest,
            current_epoch=1,
        )
        projection = adapter.project_action(request, event)
        self.assertFalse(projection.would_dispatch)
        self.assertEqual(projection.reason_code, "SOURCE_EVENT_NOT_APPLIED")

    def test_38_attachment_report_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            report = M.attach_second_host(frozen_root=release, expected_manifest_sha256=manifest_sha)
            self.assertTrue(report.adapter_report.passed)
            self.assertTrue(report.replay.passed)
            self.assertEqual(report.executed_actions, 0)

    def test_39_attachment_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            first = M.attach_second_host(frozen_root=release, expected_manifest_sha256=manifest_sha)
            second = M.attach_second_host(frozen_root=release, expected_manifest_sha256=manifest_sha)
            self.assertEqual(first, second)

    def test_40_attachment_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            report = M.attach_second_host(frozen_root=release, expected_manifest_sha256=manifest_sha)
            receipts = list(report.receipts)
            receipts[1] = replace(receipts[1], payload="tampered")
            self.assertFalse(M.replay_attachment_receipts(tuple(receipts)).passed)

    def test_41_stage2_qualification_passes_with_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            qualification = M.run_stage2_qualification(frozen_root=release, expected_manifest_sha256=manifest_sha)
            self.assertTrue(qualification.passed)

    def test_42_stage2_qualification_invariants(self):
        with tempfile.TemporaryDirectory() as directory:
            release, manifest_sha = make_frozen_fixture(Path(directory))
            q = M.run_stage2_qualification(frozen_root=release, expected_manifest_sha256=manifest_sha)
            self.assertTrue(q.stage1_source_bound)
            self.assertTrue(q.host_independent_pass)
            self.assertTrue(q.material_difference_pass)
            self.assertTrue(q.host_output_unchanged)
            self.assertTrue(q.sources_unchanged)
            self.assertTrue(q.frozen_v02_unchanged)
            self.assertTrue(q.no_hidden_execution_authority)
            self.assertEqual(q.executed_actions, 0)


if __name__ == "__main__":
    unittest.main()
