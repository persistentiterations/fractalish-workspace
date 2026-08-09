from __future__ import annotations
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from control_room.observation import build_record, canonicalize
from control_room.observer import DockerCliObserver, FixtureObserver, ObservationError
from control_room.receipt import generate_receipt
from control_room.webapp import render_observation

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "docker_inspect_one.json"

class StageOneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = FixtureObserver(FIXTURE).inspect_one("bolt-on-control-room-demo")

    def test_canonicalizes_only_required_fields(self) -> None:
        result = canonicalize(self.raw).as_dict()
        self.assertEqual(set(result), {"container_id", "container_name", "configured_image", "resolved_image", "state", "running", "created_at", "started_at"})
        self.assertNotIn("Pid", json.dumps(result))
        self.assertNotIn("IPAddress", json.dumps(result))

    def test_missing_values_are_unavailable_not_invented(self) -> None:
        result = canonicalize({"Id": "abc", "Config": {}, "State": {}})
        self.assertIsNone(result.container_name)
        self.assertIsNone(result.running)
        self.assertIsNone(result.started_at)

    def test_receipt_is_deterministic_across_observation_times(self) -> None:
        first = build_record("demo", self.raw, "Docker CLI inspect (read-only)", "docker inspect --type container demo", "2026-08-02T12:01:00Z")
        second = build_record("demo", self.raw, "Docker CLI inspect (read-only)", "docker inspect --type container demo", "2026-08-02T12:02:00Z")
        self.assertEqual(generate_receipt(first).receipt_id, generate_receipt(second).receipt_id)

    def test_receipt_changes_when_observed_fact_changes(self) -> None:
        first = build_record("demo", self.raw, "Docker CLI inspect (read-only)", "source")
        changed = json.loads(json.dumps(self.raw)); changed["State"]["Running"] = False
        second = build_record("demo", changed, "Docker CLI inspect (read-only)", "source")
        self.assertNotEqual(generate_receipt(first).receipt_id, generate_receipt(second).receipt_id)

    def test_docker_adapter_uses_only_exact_inspect_arguments(self) -> None:
        completed = subprocess.CompletedProcess([], 0, json.dumps([self.raw]), "")
        with patch("control_room.observer.subprocess.run", return_value=completed) as run:
            result = DockerCliObserver("docker-test").inspect_one("demo; stop anything")
        self.assertEqual(result["Id"], self.raw["Id"])
        self.assertEqual(run.call_args.args[0], ["docker-test", "inspect", "--type", "container", "demo; stop anything"])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_docker_adapter_rejects_zero_or_multiple_results(self) -> None:
        for payload in ([], [self.raw, self.raw]):
            completed = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
            with self.subTest(count=len(payload)), patch("control_room.observer.subprocess.run", return_value=completed):
                with self.assertRaises(ObservationError): DockerCliObserver("docker-test").inspect_one("demo")

    def test_page_labels_provenance_and_receipt(self) -> None:
        page = render_observation(FixtureObserver(FIXTURE), "bolt-on-control-room-demo")
        for marker in ("observed", "derived", "retained", "unavailable", "sha256:", "nginx:alpine", "1234567890abcdef"):
            self.assertIn(marker, page)

    def test_page_reports_observer_failure_honestly(self) -> None:
        with patch.object(DockerCliObserver, "inspect_one", side_effect=ObservationError("not connected")):
            page = render_observation(DockerCliObserver("missing"), "demo")
        self.assertIn("Observer unavailable", page)
        self.assertIn("no observation receipt was created", page)

if __name__ == "__main__": unittest.main()
