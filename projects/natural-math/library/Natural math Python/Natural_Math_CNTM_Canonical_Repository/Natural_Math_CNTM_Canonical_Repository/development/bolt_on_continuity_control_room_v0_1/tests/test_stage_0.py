from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "STAGE_0_SCOPE.md"

class StageZeroScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CONTRACT.read_text(encoding="utf-8")

    def test_foundation_is_exactly_bound(self) -> None:
        self.assertIn("bolt-on-continuity-v0.4", self.text)
        self.assertIn("4cc817441d3447e54303550090eaf8b95c451a83", self.text)

    def test_real_single_container_observation_is_required(self) -> None:
        self.assertIn("one harmless Docker demonstration container", self.text)
        self.assertIn("real read-only inspection interface", self.text)

    def test_display_fields_are_defined(self) -> None:
        for field in ("container name", "container ID", "image identity", "running or stopped status", "observer connection status", "latest observation time", "receipt identifier"):
            self.assertIn(field, self.text)

    def test_receipt_is_deterministic_and_auditable(self) -> None:
        for marker in ("receipt schema/version", "observation subject", "observation source", "canonicalized source fields", "deterministic SHA-256 receipt digest"):
            self.assertIn(marker, self.text)

    def test_fact_classes_are_distinguished(self) -> None:
        for marker in ("observed facts", "classifications", "Retention state", "operator-entered"):
            self.assertIn(marker, self.text)

    def test_mutation_and_simulation_are_denied(self) -> None:
        for marker in ("container stop, restart, pause", "Docker write APIs", "automatic remediation", "fake incidents", "simulated telemetry"):
            self.assertIn(marker, self.text)

if __name__ == "__main__":
    unittest.main()
