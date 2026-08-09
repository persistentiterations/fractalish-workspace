from __future__ import annotations
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from control_room.comparison import compare_identity, generate_comparison_receipt
from control_room.observer import DockerCliObserver
from control_room.retention import capture_and_retain, load_retained

class LiveDockerStageTwoIntegrationTest(unittest.TestCase):
    def test_two_real_read_only_observations_retain_and_classify_same_subject(self) -> None:
        subject = os.environ.get("CONTROL_ROOM_DOCKER_CONTAINER")
        if not subject or not shutil.which("docker"):
            self.skipTest("set CONTROL_ROOM_DOCKER_CONTAINER and provide Docker to run the live test")
        observer = DockerCliObserver()
        before = observer.inspect_one(subject)
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "stage-2-evidence.json"
            retained = capture_and_retain(observer, subject, evidence, 2)
            loaded = load_retained(evidence)
        result = compare_identity(loaded)
        first_receipt = generate_comparison_receipt(loaded, result)
        replay_receipt = generate_comparison_receipt(loaded, compare_identity(loaded))
        after = observer.inspect_one(subject)
        self.assertEqual([item.observation_index for item in retained.observations], [1, 2])
        self.assertEqual(result.classification, "SAME_SUBJECT")
        self.assertIsNone(result.reason)
        self.assertEqual({item.container_id for item in loaded.observations}, {before["Id"]})
        self.assertEqual(first_receipt.receipt_id, replay_receipt.receipt_id)
        self.assertEqual(before["Id"], after["Id"])
        self.assertEqual(before["State"]["StartedAt"], after["State"]["StartedAt"])
        self.assertEqual(before["State"]["Running"], after["State"]["Running"])
        self.assertEqual(before["RestartCount"], after["RestartCount"])

if __name__ == "__main__": unittest.main()
