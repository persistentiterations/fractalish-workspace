from __future__ import annotations
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from control_room.observer import ContainerObserver
from control_room.transition import TransitionError, capture_running, capture_stopped, classify, confirm_manual_stop, load, receipt
from control_room.webapp import render_transition

ROOT = Path(__file__).resolve().parents[1]
RAW = json.loads((ROOT / "tests/fixtures/docker_inspect_one.json").read_text())[0]
class SequenceObserver(ContainerObserver):
    def __init__(self, values): self.values = iter(values)
    def inspect_one(self, subject): return next(self.values)

class StageThreeTests(unittest.TestCase):
    def stopped_raw(self):
        value = json.loads(json.dumps(RAW)); value["State"]["Status"]="exited"; value["State"]["Running"]=False; return value
    def evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"transition.json"; observer=SequenceObserver([RAW, self.stopped_raw()]); first=capture_running(observer,"bolt-on-demo",path); confirmed=confirm_manual_stop(first,path); return capture_stopped(observer,confirmed,path), path.exists()
    def test_running_to_stopped_same_id_classifies(self):
        evidence,_=self.evidence(); result=classify(evidence); self.assertEqual((result.classification,result.reason),("SAME_SUBJECT_STOPPED",None))
    def test_confirmation_is_required_before_later_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"transition.json"; first=capture_running(SequenceObserver([RAW]),"bolt-on-demo",path)
            with self.assertRaises(TransitionError): capture_stopped(SequenceObserver([self.stopped_raw()]),first,path)
    def test_first_observation_must_be_running(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(TransitionError): capture_running(SequenceObserver([self.stopped_raw()]),"bolt-on-demo",Path(temporary)/"e.json")
    def test_conflicting_missing_and_unsupported_evidence_fail_closed(self):
        evidence,_=self.evidence(); later=replace(evidence.later, canonical_fields={**evidence.later.canonical_fields,"container_id":"b"*64}); self.assertEqual(classify(replace(evidence,later=later)).reason,"unverified_observation_receipt")
        missing=replace(evidence,later=None); self.assertEqual(classify(missing).reason,"insufficient_observations")
        wrong=replace(evidence,later=replace(evidence.later,canonical_fields={**evidence.later.canonical_fields,"state":"running","running":True})); self.assertEqual(classify(wrong).reason,"unverified_observation_receipt")
    def test_receipt_is_deterministic_and_time_independent(self):
        evidence,_=self.evidence(); altered=replace(evidence,earlier=replace(evidence.earlier,retained=replace(evidence.earlier.retained,observed_at="other")),later=replace(evidence.later,retained=replace(evidence.later.retained,observed_at="other2")))
        self.assertEqual(receipt(evidence).receipt_id,receipt(altered).receipt_id)
    def test_page_labels_transition_evidence(self):
        evidence,_=self.evidence(); page=render_transition(evidence,classify(evidence))
        for marker in ("observed","retained","derived","classification","operator-entered","SAME_SUBJECT_STOPPED","sha256:"): self.assertIn(marker,page)

if __name__ == "__main__": unittest.main()
