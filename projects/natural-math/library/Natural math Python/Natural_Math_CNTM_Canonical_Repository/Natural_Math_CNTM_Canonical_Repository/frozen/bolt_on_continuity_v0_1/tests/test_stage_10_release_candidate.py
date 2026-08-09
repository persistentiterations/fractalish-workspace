from __future__ import annotations
import importlib.util,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
P=BASE/"release"/"release_candidate_verifier.py"
s=importlib.util.spec_from_file_location("_rc10t",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class T(unittest.TestCase):
 def verifier(self):return m.ReleaseCandidateVerifier(BASE)
 def result(self):return self.verifier().qualify()
 def test_01_qualifies(self):self.assertTrue(self.result()["qualified"])
 def test_02_version(self):self.assertEqual(self.result()["product_version"],"0.1-rc1")
 def test_03_foundation(self):self.assertEqual(self.result()["foundation_commit"],"dc0f9e8")
 def test_04_stage(self):self.assertEqual(self.result()["release_stage"],10)
 def test_05_allowlist(self):self.assertEqual(self.result()["controlled_native_operations"],["inspect","pause","unpause"])
 def test_06_not_production(self):self.assertFalse(self.result()["production_use_qualified"])
 def test_07_tree_digest(self):self.assertEqual(len(self.result()["product_tree_digest"]),71)
 def test_08_qualification_digest(self):self.assertEqual(len(self.result()["release_candidate_qualification_digest"]),71)
 def test_09_files(self):self.assertGreaterEqual(self.result()["product_file_count"],30)
 def test_10_bytes(self):self.assertGreater(self.result()["product_byte_count"],0)
 def test_11_deterministic(self):self.assertEqual(self.result(),self.result())
 def test_12_float_rejected(self):
  with self.assertRaises(TypeError):m.digest({"x":1.0})
 def test_13_manifest_history(self):self.assertEqual([x["stage"] for x in self.verifier()._read_manifest()["qualification_history"]],list(range(11)))
 def test_14_required_gate(self):self.assertGreaterEqual(self.result()["required_file_gate_count"],20)
 def test_15_manifest_product(self):self.assertEqual(self.result()["product"],"Bolt-On Continuity for Docker")
 def test_16_manifest_shell(self):self.assertFalse(self.verifier()._read_manifest()["authority"]["shell"])
 def test_17_manifest_disposable(self):self.assertTrue(self.verifier()._read_manifest()["authority"]["disposable_container_live_qualification"])
 def test_18_manifest_terminal(self):self.assertEqual(self.verifier()._read_manifest()["required_terminal_state"],{"running":True,"paused":False})
 def test_19_tree_sorted(self):
  rows=self.verifier()._tree();self.assertEqual([x["path"] for x in rows],sorted(x["path"] for x in rows))
 def test_20_no_pyc(self):self.assertFalse(any(x["path"].endswith(".pyc") for x in self.verifier()._tree()))
 def test_21_no_cache(self):self.assertFalse(any("__pycache__" in x["path"] for x in self.verifier()._tree()))
 def test_22_hash_length(self):self.assertTrue(all(len(x["sha256"])==64 for x in self.verifier()._tree()))
 def test_23_path_relative(self):self.assertTrue(all(not x["path"].startswith("/") for x in self.verifier()._tree()))
 def test_24_authority_scan(self):self.assertEqual(self.verifier()._authority_scan(),["inspect","pause","unpause"])
 def test_25_stage0_real_files(self):
  self.assertIn("README.md",m.REQUIRED_STAGE_FILES[0]);self.assertIn("PRODUCT_CONTRACT.md",m.REQUIRED_STAGE_FILES[0])
if __name__=="__main__":unittest.main()
