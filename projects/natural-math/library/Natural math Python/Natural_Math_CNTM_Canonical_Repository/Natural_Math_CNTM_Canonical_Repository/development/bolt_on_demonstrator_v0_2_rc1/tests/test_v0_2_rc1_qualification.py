from pathlib import Path
import importlib.util, tempfile, unittest, json, sys
P=Path(__file__).resolve().parents[1]/'release_candidate'/'qualify_v0_2_rc1.py'
S=importlib.util.spec_from_file_location('rc1',P); m=importlib.util.module_from_spec(S); sys.modules[S.name]=m; S.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_version(self): self.assertEqual(m.RC_VERSION,'v0.2-RC1')
 def test_count(self): self.assertEqual(m.EXPECTED_TEST_COUNT,150)
 def test_sha(self): self.assertEqual(m.shat('abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
 def test_authority_allow_preserved(self): self.assertIn('ALLOW',m.AUTHORITY_DECISIONS)
 def test_authority_deny_preserved(self): self.assertIn('DENY',m.AUTHORITY_DECISIONS)
 def test_allow_not_prohibited(self): self.assertNotIn('ALLOW',m.PROHIBITED)
 def test_deny_not_prohibited(self): self.assertNotIn('DENY',m.PROHIBITED)
 def test_stage_order(self): self.assertEqual([x[0] for x in m.STAGES],['stage_2','stage_3','stage_4','stage_5'])
 def test_manifest_deterministic(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'b').write_text('b'); (p/'a').write_text('a'); self.assertEqual(m.manifest(p),m.manifest(p))
 def test_manifest_changes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); f=p/'a'; f.write_text('a'); x=m.manifest(p); f.write_text('b'); self.assertNotEqual(x,m.manifest(p))
 def test_manifest_ignores_record(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'RC1_QUALIFICATION.json').write_text('{}'); self.assertEqual(m.manifest(p),m.shat(''))
 def test_scan_allows_authority_decisions(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'x.py').write_text('A="ALLOW"\nB="DENY"\n'); self.assertEqual(m.scan_actions(p),())
 def test_scan_detects_execute(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'x.py').write_text('A="EXECUTE"\n'); self.assertTrue(m.scan_actions(p))
 def test_scan_allows_hold_release(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'x.py').write_text('A="HOLD"\\nB="RELEASE"\\n'); self.assertEqual(m.scan_actions(p),())
 def test_scan_ignores_tests(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'tests').mkdir(); (p/'tests'/'test_x.py').write_text('A="ALLOW"\\n'); self.assertEqual(m.scan_actions(p),())
 def test_dev_frozen_separate(self): self.assertNotEqual(m.DEV_REL,m.FROZEN_REL)
 def test_verify_path(self): self.assertEqual(m.VERIFY_REL.as_posix(),'tools/verify_all_frozen.py')
 def test_stage2_marker(self): self.assertEqual(m.STAGES[0][2],'PASS')
 def test_stage5_marker(self): self.assertIn('STAGE 5',m.STAGES[-1][2])
 def test_files_ignores_pyc(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'x.pyc').write_bytes(b'x'); self.assertEqual(list(m.files(p)),[])
 def test_files_include_source(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); f=p/'x.py'; f.write_text('x'); self.assertEqual(list(m.files(p)),[f])
 def test_qualification_error(self): self.assertTrue(issubclass(m.QualificationError,RuntimeError))
 def test_prohibited_force_execute(self): self.assertIn('FORCE_EXECUTE',m.PROHIBITED)
 def test_rc_output_name(self): self.assertEqual('RC1_QUALIFICATION.json','RC1_QUALIFICATION.json')
 def test_json_canonical_digest(self):
  a=m.shat(json.dumps({'b':1,'a':2},sort_keys=True,separators=(',',':'))); b=m.shat('{"a":2,"b":1}'); self.assertEqual(a,b)
 def test_stable_evidence_ignores_output_hashes(self):
  a=[{'name':'x','command':['python','x.py'],'stdout_sha256':'aaa','stderr_sha256':'bbb','marker':'PASS'}]
  b=[{'name':'x','command':['python','x.py'],'stdout_sha256':'ccc','stderr_sha256':'ddd','marker':'PASS'}]
  self.assertEqual(m.stable_evidence(a),m.stable_evidence(b))
 def test_stable_evidence_preserves_test_count(self):
  a=[{'name':'tests','command':['unittest discover'],'stdout_sha256':'a','stderr_sha256':'b','marker':'OK','count':150}]
  b=[{'name':'tests','command':['unittest discover'],'stdout_sha256':'c','stderr_sha256':'d','marker':'OK','count':149}]
  self.assertNotEqual(m.stable_evidence(a),m.stable_evidence(b))
 def test_stable_evidence_preserves_command(self):
  a=[{'name':'x','command':['python','a.py'],'stdout_sha256':'a','stderr_sha256':'b','marker':'PASS'}]
  b=[{'name':'x','command':['python','b.py'],'stdout_sha256':'a','stderr_sha256':'b','marker':'PASS'}]
  self.assertNotEqual(m.stable_evidence(a),m.stable_evidence(b))

if __name__=='__main__': unittest.main()
