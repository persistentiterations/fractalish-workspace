from __future__ import annotations
import os
import shutil
import unittest
from control_room.observation import build_record
from control_room.observer import DockerCliObserver
from control_room.receipt import generate_receipt

class LiveDockerIntegrationTest(unittest.TestCase):
    def test_real_read_only_docker_observation(self) -> None:
        subject = os.environ.get("CONTROL_ROOM_DOCKER_CONTAINER")
        if not subject or not shutil.which("docker"):
            self.skipTest("set CONTROL_ROOM_DOCKER_CONTAINER and provide Docker to run the live test")
        observer = DockerCliObserver()
        raw = observer.inspect_one(subject)
        record = build_record(subject, raw, observer.source_interface, observer.source_command(subject))
        receipt = generate_receipt(record)
        self.assertEqual(record.canonical_fields.container_id, raw["Id"])
        self.assertTrue(receipt.receipt_id.startswith("sha256:"))
        self.assertEqual(observer.source_command(subject), f"docker inspect --type container {subject}")

if __name__ == "__main__": unittest.main()
