import os
from pathlib import Path
import unittest
from control_room.observer import DockerCliObserver
from control_room.transition import classify, load, receipt
from control_room.webapp import render_stage_four
class StageFourLiveTest(unittest.TestCase):
 def test_live_retained_presentation(self):
  e=load(Path(os.environ['CONTROL_ROOM_STAGE4_EVIDENCE'])); r=classify(e); current=DockerCliObserver().inspect_one(e.subject_selector); page=render_stage_four(e,r)
  self.assertEqual(r.classification,'SAME_SUBJECT_STOPPED'); self.assertEqual(current['Id'],e.later.canonical_fields['container_id']); self.assertFalse(current['State']['Running']); self.assertIn(receipt(e,r).receipt_id,page)
