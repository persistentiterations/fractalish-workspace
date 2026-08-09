from pathlib import Path
import importlib.util, tempfile, unittest
P=Path(__file__).resolve().parents[1]/"final_stage"/"freeze_v0_2.py"
S=importlib.util.spec_from_file_location("f",P); M=importlib.util.module_from_spec(S); S.loader.exec_module(M)
class T(unittest.TestCase):
 def test_count(self): self.assertEqual(M.COUNT,150)
 def test_target(self): self.assertEqual(M.TARGET.as_posix(),"frozen/bolt_on/v0.2")
 def test_rc(self): self.assertEqual(M.RC.name,"RC1_QUALIFICATION.json")
 def test_stage_order(self): self.assertEqual([x[0] for x in M.STAGES],["stage_2","stage_3","stage_4","stage_5"])
 def test_sha(self): self.assertEqual(len(M.sha(b"x")),64)
 def test_canon(self): self.assertEqual(M.canon({"b":2,"a":1}),M.canon({"a":1,"b":2}))
 def test_verifier(self): self.assertIn("BOLT-ON v0.2 FROZEN VERIFICATION PASSED",M.verifier())
 def test_ignore_pyc(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/"a.pyc").write_bytes(b"x"); (p/"a.py").write_text("x")
   self.assertEqual([x.name for x in M.files(p)],["a.py"])
 def test_exclude_rc(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/"a").write_text("a"); (p/"RC1_QUALIFICATION.json").write_text("{}")
   x=M.tree(p,True); (p/"RC1_QUALIFICATION.json").write_text('{"x":1}')
   self.assertEqual(x,M.tree(p,True))
 def test_tree_changes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); f=p/"a"; f.write_text("a"); x=M.tree(p); f.write_text("b")
   self.assertNotEqual(x,M.tree(p))
if __name__=="__main__": unittest.main()
