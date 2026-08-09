import importlib.util,json,sys,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];P=BASE/"src"/"bolt_on_continuity"/"execution"/"controlled_native_executor.py"
s=importlib.util.spec_from_file_location("ex",P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
CID="a"*64
class Fake:
 def __init__(self,paused=False,fail=None):self.paused=paused;self.fail=fail;self.calls=[]
 def invoke(self,args):
  self.calls.append(args);op=args[1]
  if self.fail==op:return {"args":args,"returncode":1,"stdout":"","stderr":"failed"}
  if op=="pause":self.paused=True;return {"args":args,"returncode":0,"stdout":CID+"\n","stderr":""}
  if op=="unpause":self.paused=False;return {"args":args,"returncode":0,"stdout":CID+"\n","stderr":""}
  return {"args":args,"returncode":0,"stdout":json.dumps([{"Id":CID,"State":{"Running":True,"Paused":self.paused}}]),"stderr":""}
class T(unittest.TestCase):
 def test_01_id(self):m.ControlledNativeExecutor(CID,Fake())
 def test_02_short_id(self):
  with self.assertRaises(ValueError):m.ControlledNativeExecutor("a"*12,Fake())
 def test_03_bad_id(self):
  with self.assertRaises(ValueError):m.ControlledNativeExecutor("z"*64,Fake())
 def test_04_inspect(self):self.assertFalse(m.ControlledNativeExecutor(CID,Fake()).inspect_state()["paused"])
 def test_05_hold(self):self.assertTrue(m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",0,1)["after"]["paused"])
 def test_06_release(self):self.assertFalse(m.ControlledNativeExecutor(CID,Fake(True)).execute("RELEASE",0,1)["after"]["paused"])
 def test_07_hold_args(self):self.assertEqual(m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",0,1)["argument_vector"],["docker","pause",CID])
 def test_08_release_args(self):self.assertEqual(m.ControlledNativeExecutor(CID,Fake(True)).execute("RELEASE",0,1)["argument_vector"],["docker","unpause",CID])
 def test_09_chain(self):
  e=m.ControlledNativeExecutor(CID,Fake());a=e.execute("HOLD",0,1);b=e.execute("RELEASE",1,2);self.assertEqual(b["previous_receipt_digest"],a["execution_receipt_digest"])
 def test_10_qualification(self):self.assertTrue(m.ControlledNativeExecutor(CID,Fake()).qualify_hold_release(1)["qualified"])
 def test_11_final_unpaused(self):self.assertFalse(m.ControlledNativeExecutor(CID,Fake()).qualify_hold_release(1)["final"]["paused"])
 def test_12_unsupported(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake()).execute("STOP",0,1)
 def test_13_bad_sequence(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",-1,1)
 def test_14_bad_time(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",0,-1)
 def test_15_hold_precondition(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake(True)).execute("HOLD",0,1)
 def test_16_release_precondition(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake()).execute("RELEASE",0,1)
 def test_17_pause_failure(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake(fail="pause")).execute("HOLD",0,1)
 def test_18_unpause_failure(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake(True,fail="unpause")).execute("RELEASE",0,1)
 def test_19_inspect_failure(self):
  with self.assertRaises(m.ExecutionRejected):m.ControlledNativeExecutor(CID,Fake(fail="inspect")).inspect_state()
 def test_20_exact_calls(self):
  f=Fake();m.ControlledNativeExecutor(CID,f).qualify_hold_release(1);self.assertEqual({x[1] for x in f.calls},{"inspect","pause","unpause"})
 def test_21_no_generic_run(self):self.assertNotIn("run",dir(m.ControlledNativeExecutor(CID,Fake())))
 def test_22_no_stop(self):self.assertNotIn("stop",dir(m.ControlledNativeExecutor(CID,Fake())))
 def test_23_no_kill(self):self.assertNotIn("kill",dir(m.ControlledNativeExecutor(CID,Fake())))
 def test_24_no_remove(self):self.assertNotIn("remove",dir(m.ControlledNativeExecutor(CID,Fake())))
 def test_25_determinism(self):
  a=m.ControlledNativeExecutor(CID,Fake()).qualify_hold_release(1);b=m.ControlledNativeExecutor(CID,Fake()).qualify_hold_release(1);self.assertEqual(a,b)
 def test_26_digest(self):self.assertEqual(m.digest({"a":1}),m.digest({"a":1}))
 def test_27_float(self):
  with self.assertRaises(TypeError):m.digest({"a":1.2})
 def test_28_transport_pause_allowed(self):
  self.assertIn(("docker","pause"),m.DockerSubprocessTransport.ALLOWED)
 def test_29_transport_unpause_allowed(self):self.assertIn(("docker","unpause"),m.DockerSubprocessTransport.ALLOWED)
 def test_30_transport_inspect_allowed(self):self.assertIn(("docker","inspect"),m.DockerSubprocessTransport.ALLOWED)
 def test_31_transport_only_three(self):self.assertEqual(len(m.DockerSubprocessTransport.ALLOWED),3)
 def test_32_receipt_subject(self):self.assertEqual(m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",0,1)["container_id"],CID)
 def test_33_receipt_operation(self):self.assertEqual(m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",0,1)["native_operation"],"pause")
 def test_34_initial_zero(self):self.assertEqual(m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",0,1)["previous_receipt_digest"],m.ZERO_DIGEST)
 def test_35_no_shell_field(self):self.assertNotIn("shell",m.ControlledNativeExecutor(CID,Fake()).execute("HOLD",0,1))
 def test_36_recovery_flag(self):self.assertFalse(m.ControlledNativeExecutor(CID,Fake()).qualify_hold_release(1)["recovery_attempted"])
if __name__=="__main__":unittest.main()
