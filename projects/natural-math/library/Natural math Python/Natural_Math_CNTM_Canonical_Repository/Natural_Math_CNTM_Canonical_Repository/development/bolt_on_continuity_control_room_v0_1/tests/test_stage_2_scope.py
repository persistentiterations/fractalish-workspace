from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "STAGE_2_SCOPE.md"

class StageTwoScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CONTRACT.read_text(encoding="utf-8")

    def test_foundation_is_exactly_bound(self) -> None:
        self.assertIn("51dffe72c43a2c5f98c20cc9d9ea4ae1b336f225", self.text)
        self.assertIn("bolt-on-continuity-control-room-observation/v1", self.text)
        self.assertIn("bolt-on-continuity-control-room-receipt/v1", self.text)

    def test_retained_record_and_order_are_exact(self) -> None:
        for marker in ("retained-observations/v1", "observation_index", "positive integer", "duplicate or non-contiguous indices", "timestamps do not override"):
            self.assertIn(marker, self.text)

    def test_only_full_container_id_controls_identity(self) -> None:
        self.assertIn("full Docker `Id`", self.text)
        self.assertIn("only authorized", self.text)
        self.assertIn("identity comparison field", self.text)
        self.assertIn("must not influence identity classification", self.text)

    def test_classification_is_bounded_and_fail_closed(self) -> None:
        for marker in ("`SAME_SUBJECT`", "`INDETERMINATE`", "identity_mismatch_out_of_scope", "does not authorize or imply `REPLACED`"):
            self.assertIn(marker, self.text)

    def test_comparison_receipt_is_deterministic(self) -> None:
        for marker in ("comparison-receipt/v1", "sorted keys", "fixed compact separators", "no timestamp", "replay-identical"):
            self.assertIn(marker, self.text)

    def test_provenance_categories_are_separate(self) -> None:
        for marker in ("**observed**", "**retained**", "**derived**", "**classification**", "**operator-entered**", "**unavailable**"):
            self.assertIn(marker, self.text)

    def test_live_path_requires_multiple_real_read_only_observations(self) -> None:
        for marker in ("at least two foreground read-only", "Docker's real full ID", "no mutation"):
            self.assertIn(marker, self.text)

    def test_exclusions_deny_stage_three_capabilities(self) -> None:
        for marker in ("replacement or duplicate detection", "incident, failure, recovery", "operator approve, deny, hold, release", "automatic polling", "any modification under `frozen/`"):
            self.assertIn(marker, self.text)

if __name__ == "__main__":
    unittest.main()
