from __future__ import annotations
import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
FP=HERE/"tools"/"freeze_bolt_on_continuity_v0_1.py"
s=importlib.util.spec_from_file_location("_s11f",FP);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
VP=HERE/"tools"/"verify_frozen_bolt_on_continuity_v0_1.py"
v=importlib.util.spec_from_file_location("_s11v",VP);vm=importlib.util.module_from_spec(v);v.loader.exec_module(vm)
class T(unittest.TestCase):
 def repo(self):
  td=Path(tempfile.mkdtemp());p=td/"products"/"bolt_on_continuity_v0_1";(p/"release").mkdir(parents=True)
  (p/"a.txt").write_text("a",encoding="utf-8");(p/"sub").mkdir();(p/"sub"/"b.txt").write_text("b",encoding="utf-8")
  (p/"release"/"release_candidate_verifier.py").write_text(
   """class ReleaseCandidateVerifier:
    def __init__(self, p):
        self.p = p
    def qualify(self):
        return {
            "qualified": True,
            "release_candidate_qualification_digest": "sha256:" + "1" * 64,
        }
""", encoding="utf-8")
  return td
 def test_01_digest(self):self.assertEqual(len(m.digest({"a":1})),71)
 def test_02_float(self):
  with self.assertRaises(TypeError):m.digest({"a":1.0})
 def test_03_include(self):self.assertTrue(m.included(Path("a.txt")))
 def test_04_exclude_pyc(self):self.assertFalse(m.included(Path("a.pyc")))
 def test_05_exclude_cache(self):self.assertFalse(m.included(Path("__pycache__/a.py")))
 def test_06_freeze(self):
  r=self.repo();x=m.ProductFreezer(r).freeze("tester",7317);self.assertTrue(x["qualified"]);shutil.rmtree(r)
 def test_07_target(self):
  r=self.repo();m.ProductFreezer(r).freeze("tester",7317);self.assertTrue((r/"frozen"/"bolt_on_continuity_v0_1").is_dir());shutil.rmtree(r)
 def test_08_manifest(self):
  r=self.repo();m.ProductFreezer(r).freeze("tester",7317);self.assertTrue((r/"frozen"/"bolt_on_continuity_v0_1"/"FROZEN_MANIFEST.json").is_file());shutil.rmtree(r)
 def test_09_approval(self):
  r=self.repo();m.ProductFreezer(r).freeze("tester",7317);self.assertTrue((r/"frozen"/"bolt_on_continuity_v0_1"/"FREEZE_APPROVAL_RECORD.json").is_file());shutil.rmtree(r)
 def test_10_refuse_existing(self):
  r=self.repo();f=m.ProductFreezer(r);f.freeze("tester",7317)
  with self.assertRaises(m.FreezeRejected):f.freeze("tester",7317)
  shutil.rmtree(r)
 def test_11_approver(self):
  r=self.repo()
  with self.assertRaises(m.FreezeRejected):m.ProductFreezer(r).freeze("",7317)
  shutil.rmtree(r)
 def test_12_epoch(self):
  r=self.repo()
  with self.assertRaises(m.FreezeRejected):m.ProductFreezer(r).freeze("x",-1)
  shutil.rmtree(r)
 def test_13_verify(self):
  r=self.repo();m.ProductFreezer(r).freeze("tester",7317);self.assertTrue(vm.verify(r)["qualified"]);shutil.rmtree(r)
 def test_14_equivalence(self):
  r=self.repo();m.ProductFreezer(r).freeze("tester",7317);self.assertTrue(vm.verify(r)["source_equivalence"]);shutil.rmtree(r)
 def test_15_tamper(self):
  r=self.repo();m.ProductFreezer(r).freeze("tester",7317);(r/"frozen"/"bolt_on_continuity_v0_1"/"a.txt").write_text("x")
  with self.assertRaises(vm.FrozenVerificationRejected):vm.verify(r)
  shutil.rmtree(r)
if __name__=="__main__":unittest.main()
