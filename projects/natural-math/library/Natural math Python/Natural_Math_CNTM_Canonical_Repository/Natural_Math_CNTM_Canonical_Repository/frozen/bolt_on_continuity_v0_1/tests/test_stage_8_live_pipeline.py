from __future__ import annotations
import copy, importlib.util, json, sys, unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MODULE = BASE / "src" / "bolt_on_continuity" / "integration" / "controlled_live_pipeline.py"
spec = importlib.util.spec_from_file_location("_stage8_tests", MODULE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CID = "a" * 64

class FakeTransport:
    def __init__(self, running=True, paused=False, fail_pause=False, fail_unpause=False):
        self.running=running; self.paused=paused; self.fail_pause=fail_pause; self.fail_unpause=fail_unpause
        self.calls=[]
    def invoke(self,args):
        self.calls.append(list(args)); op=args[1]
        if op=="inspect":
            p=[{"Id":CID,"State":{"Running":self.running,"Paused":self.paused}}]
            return {"args":args,"returncode":0,"stdout":json.dumps(p),"stderr":""}
        if op=="pause":
            if self.fail_pause:return {"args":args,"returncode":1,"stdout":"","stderr":"pause failed"}
            self.paused=True;return {"args":args,"returncode":0,"stdout":CID+"\\n","stderr":""}
        if op=="unpause":
            if self.fail_unpause:return {"args":args,"returncode":1,"stdout":"","stderr":"unpause failed"}
            self.paused=False;return {"args":args,"returncode":0,"stdout":CID+"\\n","stderr":""}
        return {"args":args,"returncode":1,"stdout":"","stderr":"bad"}

class Stage8Tests(unittest.TestCase):
    def pipeline(self,t=None): return m.ControlledLivePipeline(BASE,CID,t or FakeTransport())
    def result(self): return self.pipeline().qualify(7317)
    def test_01_qualifies(self): self.assertTrue(self.result()["qualified"])
    def test_02_verifies(self): self.assertTrue(self.result()["continuity_verification_pass"])
    def test_03_final_running(self): self.assertTrue(self.result()["final_state"]["running"])
    def test_04_final_unpaused(self): self.assertFalse(self.result()["final_state"]["paused"])
    def test_05_no_recovery(self): self.assertFalse(self.result()["recovery_attempted"])
    def test_06_full_id(self): self.assertEqual(self.result()["container_id"],CID)
    def test_07_config_digest(self): self.assertTrue(self.result()["configuration_digest"].startswith("sha256:"))
    def test_08_incident(self): self.assertTrue(self.result()["incident_id"].startswith("incident-"))
    def test_09_hold_digest(self): self.assertEqual(len(self.result()["hold_execution_receipt_digest"]),71)
    def test_10_release_digest(self): self.assertEqual(len(self.result()["release_execution_receipt_digest"]),71)
    def test_11_continuity_digest(self): self.assertEqual(len(self.result()["continuity_qualification_digest"]),71)
    def test_12_stage8_digest(self): self.assertEqual(len(self.result()["stage_8_qualification_digest"]),71)
    def test_13_deterministic_config(self):
        self.assertEqual(self.pipeline().configuration_digest,self.pipeline().configuration_digest)
    def test_14_bad_short_id(self):
        with self.assertRaises(ValueError): m.ControlledLivePipeline(BASE,"a"*12,FakeTransport())
    def test_15_bad_nonhex_id(self):
        with self.assertRaises(ValueError): m.ControlledLivePipeline(BASE,"z"*64,FakeTransport())
    def test_16_negative_time(self):
        with self.assertRaises(m.Stage8Rejected): self.pipeline().qualify(-1)
    def test_17_float_time(self):
        with self.assertRaises(m.Stage8Rejected): self.pipeline().qualify(1.5)
    def test_18_initial_stopped(self):
        with self.assertRaises(m.Stage8Rejected): self.pipeline(FakeTransport(running=False)).qualify(1)
    def test_19_initial_paused(self):
        with self.assertRaises(m.Stage8Rejected): self.pipeline(FakeTransport(paused=True)).qualify(1)
    def test_20_pause_failure(self):
        with self.assertRaises(Exception): self.pipeline(FakeTransport(fail_pause=True)).qualify(1)
    def test_21_only_allowed_ops(self):
        t=FakeTransport();self.pipeline(t).qualify(1)
        self.assertTrue(all(c[1] in {"inspect","pause","unpause"} for c in t.calls))
    def test_22_full_id_every_call(self):
        t=FakeTransport();self.pipeline(t).qualify(1)
        self.assertTrue(all(c[2]==CID for c in t.calls))
    def test_23_shell_never_present(self):
        t=FakeTransport();self.pipeline(t).qualify(1)
        self.assertTrue(all("shell" not in c for c in t.calls))
    def test_24_no_remove(self):
        t=FakeTransport();self.pipeline(t).qualify(1)
        self.assertFalse(any(c[1]=="rm" for c in t.calls))
    def test_25_no_stop(self):
        t=FakeTransport();self.pipeline(t).qualify(1)
        self.assertFalse(any(c[1]=="stop" for c in t.calls))
    def test_26_no_kill(self):
        t=FakeTransport();self.pipeline(t).qualify(1)
        self.assertFalse(any(c[1]=="kill" for c in t.calls))
    def test_27_no_exec(self):
        t=FakeTransport();self.pipeline(t).qualify(1)
        self.assertFalse(any(c[1]=="exec" for c in t.calls))
    def test_28_configuration_has_allowlist(self):
        self.assertEqual(len(self.pipeline().configuration["native_allowlist"]),3)
    def test_29_float_digest_rejected(self):
        with self.assertRaises(TypeError): m.digest({"x":1.25})
    def test_30_stage_foundation_loaded(self):
        p=self.pipeline();self.assertIsNotNone(p.executor);self.assertIsNotNone(p.binder)

if __name__=="__main__": unittest.main()
