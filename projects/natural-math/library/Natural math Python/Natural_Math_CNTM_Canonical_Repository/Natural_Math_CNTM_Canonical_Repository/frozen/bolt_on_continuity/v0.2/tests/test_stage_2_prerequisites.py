from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from bolt_on_continuity_v0_2.prerequisite_checker import (  # noqa: E402
    INFO_ARGS,
    VERSION_ARGS,
    ProbeResult,
    canonical_report_bytes,
    evaluate_prerequisites,
)


VERSION_OK = json.dumps({"Client": {"Version": "28.0.0"}, "Server": {"Version": "28.0.0"}})
INFO_LINUX = json.dumps({"OSType": "linux"})


class FakeRunner:
    def __init__(self, version: ProbeResult | None = None, info: ProbeResult | None = None):
        self.version = version or ProbeResult(0, VERSION_OK)
        self.info = info or ProbeResult(0, INFO_LINUX)
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def __call__(self, executable: str, args, timeout: int) -> ProbeResult:
        key = tuple(args)
        self.calls.append((executable, key, timeout))
        if key == VERSION_ARGS:
            return self.version
        if key == INFO_ARGS:
            return self.info
        raise AssertionError(f"unexpected probe: {key}")


def evaluate(**overrides):
    runner = overrides.pop("runner", FakeRunner())
    values = {
        "system_name": "Windows",
        "machine": "AMD64",
        "python_implementation": "CPython",
        "python_version": (3, 13, 1),
        "docker_executable": "docker",
        "runner": runner,
        "environment": {},
    }
    values.update(overrides)
    return evaluate_prerequisites(**values), runner


class Stage2PrerequisiteTests(unittest.TestCase):
    def test_supported_windows_linux_engine_passes(self):
        report, runner = evaluate()
        self.assertTrue(report["eligible"])
        self.assertEqual(report["reason_codes"], ["ELIGIBLE"])
        self.assertEqual([call[1] for call in runner.calls], [VERSION_ARGS, INFO_ARGS])

    def test_supported_native_linux_passes(self):
        report, _ = evaluate(system_name="Linux", machine="x86_64")
        self.assertTrue(report["eligible"])
        self.assertEqual(report["host_family"], "linux")

    def test_missing_docker_fails_without_probe(self):
        report, runner = evaluate(docker_executable=None)
        self.assertFalse(report["eligible"])
        self.assertIn("DOCKER_CLI_MISSING", report["reason_codes"])
        self.assertEqual(runner.calls, [])

    def test_daemon_failure_fails_closed(self):
        runner = FakeRunner(version=ProbeResult(1, "", "daemon unavailable"))
        report, _ = evaluate(runner=runner)
        self.assertFalse(report["eligible"])
        self.assertIn("DOCKER_VERSION_FAILED", report["reason_codes"])

    def test_malformed_output_fails_closed(self):
        runner = FakeRunner(info=ProbeResult(0, "not-json"))
        report, _ = evaluate(runner=runner)
        self.assertFalse(report["eligible"])
        self.assertIn("DOCKER_INFO_MALFORMED", report["reason_codes"])

    def test_windows_container_mode_rejected(self):
        runner = FakeRunner(info=ProbeResult(0, json.dumps({"OSType": "windows"})))
        report, _ = evaluate(runner=runner)
        self.assertFalse(report["eligible"])
        self.assertIn("LINUX_CONTAINER_ENGINE_REQUIRED", report["reason_codes"])

    def test_unsupported_python_rejected(self):
        report, _ = evaluate(python_version=(3, 10, 9))
        self.assertFalse(report["eligible"])
        self.assertIn("UNSUPPORTED_PYTHON", report["reason_codes"])

    def test_unsupported_platform_rejected(self):
        report, _ = evaluate(system_name="Darwin")
        self.assertFalse(report["eligible"])
        self.assertIn("UNSUPPORTED_HOST", report["reason_codes"])

    def test_remote_endpoint_rejected_without_probe(self):
        report, runner = evaluate(environment={"DOCKER_HOST": "tcp://example.invalid:2375"})
        self.assertFalse(report["eligible"])
        self.assertIn("REMOTE_ENDPOINT_REJECTED", report["reason_codes"])
        self.assertEqual(runner.calls, [])

    def test_safe_defaults_are_fixed(self):
        report, _ = evaluate()
        self.assertIs(report["observation_only"], True)
        self.assertIs(report["gateway_enabled"], False)

    def test_canonical_output_is_stable(self):
        report_a, _ = evaluate()
        report_b, _ = evaluate()
        self.assertEqual(canonical_report_bytes(report_a), canonical_report_bytes(report_b))

    def test_only_exact_allowlisted_probes_are_used(self):
        report, runner = evaluate()
        self.assertTrue(report["eligible"])
        self.assertEqual({call[1] for call in runner.calls}, {VERSION_ARGS, INFO_ARGS})


if __name__ == "__main__":
    unittest.main()
