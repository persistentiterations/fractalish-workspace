from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"qualification"/"adversarial_recovery.py"
s=importlib.util.spec_from_file_location("_s9t",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
CID="a"*64
class Fake:
 def __init__(self,running=True,paused=False,fail_pause=False,fail_recovery=False):
  self.running=running;self.paused=paused;self.fail_pause=fail_pause;self.fail_recovery=fail_recovery;self.unpauses=0;self.calls=[]
 def invoke(self,args):
  self.calls.append(list(args));op=args[1]
  if op=="inspect":return {"args":args,"returncode":0,"stdout":json.dumps([{"Id":CID,"State":{"Running":self.running,"Paused":self.paused}}]),"stderr":""}
  if op=="pause":
   if self.fail_pause:return {"args":args,"returncode":1,"stdout":"","stderr":"pause failure"}
   self.paused=True;return {"args":args,"returncode":0,"stdout":CID+"\\n","stderr":""}
  if op=="unpause":
   self.unpauses+=1
   if self.fail_recovery:return {"args":args,"returncode":1,"stdout":"","stderr":"recovery failure"}
   self.paused=False;return {"args":args,"returncode":0,"stdout":CID+"\\n","stderr":""}
  return {"args":args,"returncode":1,"stdout":"","stderr":"bad"}
class T(unittest.TestCase):
 def q(self,f=None):return m.BoundedRecoveryQualifier(BASE,CID,f or Fake())
 def r(self):return self.q().qualify(7317)
 def test_01_pass(self):self.assertTrue(self.r()["qualified"])
 def test_02_injection_once(self):self.assertEqual(self.r()["injected_failure_count"],1)
 def test_03_rejected(self):self.assertTrue(self.r()["first_release_rejected"])
 def test_04_final_running(self):self.assertTrue(self.r()["final_state"]["running"])
 def test_05_final_unpaused(self):self.assertFalse(self.r()["final_state"]["paused"])
 def test_06_recovery_sequence(self):self.assertEqual(self.r()["recovery_sequence"],999)
 def test_07_digest(self):self.assertEqual(len(self.r()["stage_9_recovery_qualification_digest"]),71)
 def test_08_hold_digest(self):self.assertEqual(len(self.r()["hold_receipt_digest"]),71)
 def test_09_recovery_digest(self):self.assertEqual(len(self.r()["recovery_receipt_digest"]),71)
 def test_10_subject(self):self.assertEqual(self.r()["container_id"],CID)
 def test_11_bad_short(self):
  with self.assertRaises(ValueError):m.BoundedRecoveryQualifier(BASE,"a"*12,Fake())
 def test_12_bad_hex(self):
  with self.assertRaises(ValueError):m.BoundedRecoveryQualifier(BASE,"z"*64,Fake())
 def test_13_negative_time(self):
  with self.assertRaises(m.Stage9Rejected):self.q().qualify(-1)
 def test_14_float_time(self):
  with self.assertRaises(m.Stage9Rejected):self.q().qualify(1.2)
 def test_15_stopped(self):
  with self.assertRaises(m.Stage9Rejected):self.q(Fake(running=False)).qualify(1)
 def test_16_initial_paused(self):
  with self.assertRaises(m.Stage9Rejected):self.q(Fake(paused=True)).qualify(1)
 def test_17_pause_failure(self):
  with self.assertRaises(Exception):self.q(Fake(fail_pause=True)).qualify(1)
 def test_18_recovery_failure(self):
  with self.assertRaises(Exception):self.q(Fake(fail_recovery=True)).qualify(1)
 def test_19_only_allowlist(self):
  f=Fake();self.q(f).qualify(1);self.assertTrue(all(x[1] in {"inspect","pause","unpause"} for x in f.calls))
 def test_20_full_id_calls(self):
  f=Fake();self.q(f).qualify(1);self.assertTrue(all(x[2]==CID for x in f.calls))
 def test_21_no_stop(self):
  f=Fake();self.q(f).qualify(1);self.assertFalse(any(x[1]=="stop" for x in f.calls))
 def test_22_no_kill(self):
  f=Fake();self.q(f).qualify(1);self.assertFalse(any(x[1]=="kill" for x in f.calls))
 def test_23_no_rm(self):
  f=Fake();self.q(f).qualify(1);self.assertFalse(any(x[1]=="rm" for x in f.calls))
 def test_24_no_exec(self):
  f=Fake();self.q(f).qualify(1);self.assertFalse(any(x[1]=="exec" for x in f.calls))
 def test_25_wrapper_reject_extra(self):
  w=m.FailFirstUnpauseTransport(Fake())
  with self.assertRaises(m.Stage9Rejected):w.invoke(["docker","pause",CID,"extra"])
 def test_26_wrapper_reject_name(self):
  w=m.FailFirstUnpauseTransport(Fake())
  with self.assertRaises(m.Stage9Rejected):w.invoke(["docker","pause","name"])
 def test_27_wrapper_reject_op(self):
  w=m.FailFirstUnpauseTransport(Fake())
  with self.assertRaises(m.Stage9Rejected):w.invoke(["docker","stop",CID])
 def test_28_first_unpause_not_delegated(self):
  f=Fake();w=m.FailFirstUnpauseTransport(f);w.invoke(["docker","unpause",CID]);self.assertEqual(f.unpauses,0)
 def test_29_second_unpause_delegated(self):
  f=Fake();w=m.FailFirstUnpauseTransport(f);w.invoke(["docker","unpause",CID]);w.invoke(["docker","unpause",CID]);self.assertEqual(f.unpauses,1)
 def test_30_counter(self):
  f=Fake();w=m.FailFirstUnpauseTransport(f);w.invoke(["docker","unpause",CID]);self.assertEqual(w.injected_failure_count,1)
 def test_31_digest_float(self):
  with self.assertRaises(TypeError):m.digest({"x":1.0})
 def test_32_deterministic(self):self.assertEqual(self.r(),self.r())
 def test_33_stranded_digest(self):self.assertEqual(len(self.r()["stranded_state_digest"]),71)
 def test_34_initial_digest(self):self.assertEqual(len(self.r()["initial_state_digest"]),71)
 def test_35_failure_reason(self):self.assertTrue(bool(self.r()["first_release_rejection_reason"]))
 def test_36_foundation(self):self.assertIsNotNone(self.q().executor)
if __name__=="__main__":unittest.main()
