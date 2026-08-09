import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN = ROOT / "guardian.py"
CLASSIFICATION = json.loads(
    (ROOT / "STAGE_02C_CLASSIFICATION.json").read_text(encoding="utf-8")
)


class Stage02CClassificationRegressionTests(unittest.TestCase):
    def test_all_stage02c_actual_outcomes_are_preserved(self):
        records = (
            CLASSIFICATION["confirmed_bypasses_or_false_positives"]
            + CLASSIFICATION["disproven_reviewer_hypotheses"]
        )
        failures = []

        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "ledger.jsonl"

            for record in records:
                source = ROOT / record["file"]
                process = subprocess.run(
                    [
                        sys.executable,
                        "-S",
                        str(GUARDIAN),
                        "--unsigned-dev",
                        "--ledger",
                        str(ledger),
                        "scan",
                        str(source),
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                try:
                    slip = json.loads(process.stdout)
                except json.JSONDecodeError:
                    failures.append(
                        f"{source.name}: invalid JSON; stdout={process.stdout!r}; "
                        f"stderr={process.stderr!r}"
                    )
                    continue

                actual = slip["intake_outcome"]
                frozen_actual = record["actual"]
                if actual != frozen_actual:
                    failures.append(
                        f"{source.name}: Stage 02C actual={frozen_actual}, "
                        f"Stage 03 actual={actual}"
                    )

        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":
    unittest.main(verbosity=2)
