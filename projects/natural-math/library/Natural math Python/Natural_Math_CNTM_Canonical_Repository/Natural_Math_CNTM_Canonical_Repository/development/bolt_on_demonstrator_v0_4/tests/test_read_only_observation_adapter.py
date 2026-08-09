from __future__ import annotations

import importlib.util
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


host = load("test_v04_stage3_host", PROJECT / "hosts" / "ordinary_job_service.py")
adapter = load("test_v04_stage3_adapter", PROJECT / "adapters" / "read_only_job_observer.py")
stage3 = load("test_v04_stage3_harness", PROJECT / "integration" / "read_only_observation_adapter.py")


class Stage3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline_run = host.build_native_baseline()
        cls.snapshot = cls.baseline_run.snapshot.record()
        cls.receipts = tuple(item.record() for item in cls.baseline_run.receipts)
        cls.observer = adapter.ReadOnlyObservationAdapter()
        cls.batch = cls.observer.observe(cls.snapshot, cls.receipts)

    def test_001_stage_name(self): self.assertEqual(stage3.STAGE_VERSION, "0.4.3")
    def test_002_mode(self): self.assertEqual(adapter.MODE, "READ_ONLY_EXTERNAL_OBSERVATION")
    def test_003_authority_none(self): self.assertEqual(adapter.EXECUTION_AUTHORITY, "NONE")
    def test_004_command_surface_empty(self): self.assertEqual(adapter.COMMAND_SURFACE, ())
    def test_005_identity_id(self): self.assertEqual(self.observer.identity().adapter_id, adapter.ADAPTER_ID)
    def test_006_identity_digest(self): self.assertEqual(len(self.observer.identity().identity_digest), 64)
    def test_007_public_methods(self):
        names={n for n,v in adapter.ReadOnlyObservationAdapter.__dict__.items() if callable(v) and not n.startswith("_")}
        self.assertEqual(names,{"identity","normalise_record","observe"})
    def test_008_normalise_subject(self): self.assertEqual(self.observer.normalise_record(self.snapshot["records"][0]).subject_id,"JOB-001")
    def test_009_normalise_state(self): self.assertEqual(self.observer.normalise_record(self.snapshot["records"][0]).observed_state,"DONE")
    def test_010_subject_count(self): self.assertEqual(len(self.batch.subjects),1)
    def test_011_event_count(self): self.assertEqual(len(self.batch.events),6)
    def test_012_first_operation(self): self.assertEqual(self.batch.events[0].native_operation,"REGISTER_JOB")
    def test_013_last_operation(self): self.assertEqual(self.batch.events[-1].native_operation,"COMPLETE_JOB")
    def test_014_first_before_mapping(self): self.assertEqual(self.batch.events[0].observed_before_state,"ABSENT")
    def test_015_ready_mapping(self): self.assertEqual(self.batch.events[0].observed_after_state,"READY")
    def test_016_running_mapping(self): self.assertEqual(self.batch.events[1].observed_after_state,"ACTIVE")
    def test_017_held_mapping(self): self.assertEqual(self.batch.events[3].observed_after_state,"HELD")
    def test_018_done_mapping(self): self.assertEqual(self.batch.events[-1].observed_after_state,"DONE")
    def test_019_event_chain_start(self): self.assertEqual(self.batch.events[0].previous_observation_digest,adapter.ZERO_DIGEST)
    def test_020_event_chain_link(self): self.assertEqual(self.batch.events[1].previous_observation_digest,self.batch.events[0].observation_digest)
    def test_021_source_receipt_binding(self): self.assertEqual(self.batch.events[2].source_receipt_digest,self.receipts[2]["receipt_digest"])
    def test_022_source_command_binding(self): self.assertEqual(self.batch.events[2].source_command_digest,self.receipts[2]["command_digest"])
    def test_023_source_snapshot_binding(self): self.assertEqual(self.batch.source_snapshot_digest,self.snapshot["snapshot_digest"])
    def test_024_source_final_binding(self): self.assertEqual(self.batch.source_final_receipt_digest,self.snapshot["final_receipt_digest"])
    def test_025_source_counts(self): self.assertEqual((self.batch.source_command_count,self.batch.source_applied_count,self.batch.source_rejected_count),(6,6,0))
    def test_026_batch_digest(self): self.assertEqual(len(self.batch.batch_digest),64)
    def test_027_final_observation_digest(self): self.assertEqual(self.batch.final_observation_digest,self.batch.events[-1].observation_digest)
    def test_028_replay_pass(self): self.assertTrue(adapter.replay_observation(self.batch).passed)
    def test_029_replay_digest(self): self.assertEqual(adapter.replay_observation(self.batch).replay_digest,self.batch.batch_digest)
    def test_030_deterministic_observation(self): self.assertEqual(self.batch,self.observer.observe(self.snapshot,self.receipts))
    def test_031_batch_json_serializable(self): json.dumps(self.batch.record(),sort_keys=True)
    def test_032_registry_empty(self): self.assertFalse(stage3.empty_registry().attached)
    def test_033_registry_attach(self): self.assertEqual(stage3.attach(stage3.empty_registry()).attached,(adapter.ADAPTER_ID,))
    def test_034_registry_detach(self): self.assertFalse(stage3.detach(stage3.attach(stage3.empty_registry())).attached)
    def test_035_registry_replay(self): self.assertTrue(stage3.replay_registry(stage3.detach(stage3.attach(stage3.empty_registry()))).passed)
    def test_036_double_attach_rejected(self):
        with self.assertRaises(ValueError): stage3.attach(stage3.attach(stage3.empty_registry()))
    def test_037_detach_absent_rejected(self):
        with self.assertRaises(ValueError): stage3.detach(stage3.empty_registry())
    def test_038_registry_tamper(self):
        reg=stage3.detach(stage3.attach(stage3.empty_registry())); bad=replace(reg.receipts[0],event="DETACH"); badreg=replace(reg,receipts=(bad,reg.receipts[1])); self.assertFalse(stage3.replay_registry(badreg).passed)
    def test_039_structural_scan(self): self.assertTrue(stage3.structural_read_only_scan()[0])
    def test_040_host_baseline_digest(self): self.assertEqual(self.baseline_run.run_digest,stage3.EXPECTED_BASELINE_DIGEST)
    def test_041_stage2_pass(self): self.assertTrue(stage3.stage2.run_stage2_qualification().passed)
    def test_042_rejection_matrix_count(self): self.assertEqual(len(stage3.run_rejection_matrix(self.snapshot,self.receipts,self.baseline_run.run_digest)),40)
    def test_043_rejection_matrix_safe(self): self.assertTrue(all(x.rejected and x.host_unchanged for x in stage3.run_rejection_matrix(self.snapshot,self.receipts,self.baseline_run.run_digest)))
    def test_044_qualification_pass(self): self.assertTrue(stage3.run_stage3_qualification().passed)
    def test_045_cli_pass(self):
        cp=subprocess.run([sys.executable,str(PROJECT/"integration"/"read_only_observation_adapter.py")],capture_output=True,text=True)
        self.assertEqual(cp.returncode,0);self.assertIn("STAGE 3 READ-ONLY EXTERNAL OBSERVATION ADAPTER: PASS",cp.stdout)


def _make_rejection_test(index: int, case_name: str):
    def test(self):
        results={item.name:item for item in stage3.run_rejection_matrix(self.snapshot,self.receipts,self.baseline_run.run_digest)}
        self.assertIn(case_name,results)
        self.assertTrue(results[case_name].rejected)
        self.assertTrue(results[case_name].host_unchanged)
        self.assertEqual(results[case_name].observation_host_actions,0)
        self.assertEqual(results[case_name].bolt_on_executed_actions,0)
    test.__name__=f"test_{45+index:03d}_reject_{case_name}"
    return test


_case_names=[name for name,_,_ in stage3._mutations(Stage3Tests.snapshot if hasattr(Stage3Tests,'snapshot') else host.build_native_baseline().snapshot.record(), tuple(x.record() for x in host.build_native_baseline().receipts))]
for _index,_name in enumerate(_case_names,1):
    setattr(Stage3Tests,f"test_{45+_index:03d}_reject_{_name}",_make_rejection_test(_index,_name))


if __name__ == "__main__": unittest.main()
