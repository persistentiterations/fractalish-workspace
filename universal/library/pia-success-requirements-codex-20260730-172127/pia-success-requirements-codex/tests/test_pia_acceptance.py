"""
PIA pilot acceptance runner tests.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.cognitive_basin.pia.acceptance import run_acceptance_suite


def test_pia_acceptance_runner_writes_retained_artifacts(tmp_path):
    summary = run_acceptance_suite(tmp_path)

    assert summary["passed"] is True
    assert summary["scenario_count"] == 11
    assert summary["pilot_claim_status"] == "DETERMINISTIC_HARNESS_VERIFIED"
    assert summary["host_substitution_level"] == "deterministic-pilot-model-host-substitution"

    for key, path in summary["artifacts"].items():
        assert path, key
        assert Path(path).exists(), key

    receipt = json.loads(Path(summary["artifacts"]["guarded_run_receipt"]).read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "fractalish.pia.guarded-run-receipt.v0.1"
    assert receipt["source_host_id"] != receipt["destination_host_id"]
    assert summary["artifacts"]["fixture_steward_record"].endswith("private\\fixture-steward-record-private.json") or summary["artifacts"]["fixture_steward_record"].endswith("private/fixture-steward-record-private.json")
    steward_verification = json.loads(Path(summary["artifacts"]["fixture_steward_verification"]).read_text(encoding="utf-8"))
    assert steward_verification["schema_version"] == "fractalish.pia.fixture-steward-verification.v0.1"
    assert steward_verification["verified"] is True


def test_pia_acceptance_module_entrypoint(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "python.cognitive_basin.pia.acceptance", "--all", "--artifact-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "pia-pilot-acceptance-summary.json").read_text(encoding="utf-8"))
    assert summary["passed"] is True
