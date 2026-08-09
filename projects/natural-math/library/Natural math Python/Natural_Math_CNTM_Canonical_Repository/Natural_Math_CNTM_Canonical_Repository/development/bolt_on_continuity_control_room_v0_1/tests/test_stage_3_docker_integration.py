from __future__ import annotations
import os
from pathlib import Path
import shutil
import unittest
from control_room.observer import DockerCliObserver
from control_room.transition import classify, load, receipt

class LiveStageThreeIntegrationTest(unittest.TestCase):
    def test_operator_confirmed_real_running_to_stopped_evidence(self):
        subject=os.environ.get("CONTROL_ROOM_DOCKER_CONTAINER"); source=os.environ.get("CONTROL_ROOM_STAGE3_EVIDENCE")
        if not subject or not source or not shutil.which("docker"): self.skipTest("Stage 3 evidence, subject, and Docker are required")
        evidence=load(Path(source)); result=classify(evidence); observed=DockerCliObserver().inspect_one(subject)
        self.assertTrue(evidence.operator_stop_confirmed)
        self.assertEqual((result.classification,result.reason),("SAME_SUBJECT_STOPPED",None))
        self.assertEqual(evidence.earlier.canonical_fields["container_id"],evidence.later.canonical_fields["container_id"])
        self.assertEqual(evidence.later.canonical_fields["container_id"],observed["Id"])
        self.assertEqual((observed["State"]["Status"],observed["State"]["Running"]),("exited",False))
        self.assertTrue(receipt(evidence,result).receipt_id.startswith("sha256:"))

if __name__ == "__main__": unittest.main()
