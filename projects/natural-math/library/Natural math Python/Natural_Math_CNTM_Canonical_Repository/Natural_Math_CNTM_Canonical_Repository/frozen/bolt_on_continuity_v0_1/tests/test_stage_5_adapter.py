import importlib.util, json, sys, unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"adapter"/"dry_run_native_action_adapter.py"
spec=importlib.util.spec_from_file_location("adapter",P)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

CID="a"*64
CFG="sha256:"+"b"*64
POLICY={"policy_version":"1","docker_binary":"docker","max_decision_age_seconds":30,"dry_run_required":True}

def decision(action="HOLD", decision_value="APPROVE", sequence=1, decided=100):
    body={
        "schema_version":"1","incident_id":"incident-0001","container_id":CID,
        "configuration_digest":CFG,"projection_digest":"sha256:"+"1"*64,
        "projection_sequence":sequence,"projected_action":action,
        "gateway_policy_digest":"sha256:"+"2"*64,"gateway_sequence":sequence,
        "previous_gateway_decision_digest":"sha256:"+"0"*64,
        "decided_at_epoch":decided,"decision":decision_value,
        "reason_code":"HOLD_ALLOWED" if action=="HOLD" else "RELEASE_ALLOWED",
    }
    return {**body,"gateway_decision_digest":m.digest(body)}

class T(unittest.TestCase):
    def setUp(self): self.a=m.DryRunNativeActionAdapter(CID,CFG,POLICY)

    def test_01_hold_plan(self): self.assertEqual(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["native_operation"],"pause")
    def test_02_release_plan(self): self.assertEqual(self.a.plan(decision("RELEASE"),adapter_sequence=1,created_at_epoch=105)["native_operation"],"unpause")
    def test_03_hold_args(self): self.assertEqual(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["argument_vector"],["docker","pause",CID])
    def test_04_release_args(self): self.assertEqual(self.a.plan(decision("RELEASE"),adapter_sequence=1,created_at_epoch=105)["argument_vector"],["docker","unpause",CID])
    def test_05_dry_run(self): self.assertTrue(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["dry_run"])
    def test_06_verify(self): self.assertTrue(m.DryRunNativeActionAdapter.verify_plan(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105))["verification_pass"])
    def test_07_determinism(self):
        a=m.DryRunNativeActionAdapter(CID,CFG,POLICY);b=m.DryRunNativeActionAdapter(CID,CFG,POLICY)
        self.assertEqual(a.plan(decision(),adapter_sequence=1,created_at_epoch=105),b.plan(decision(),adapter_sequence=1,created_at_epoch=105))
    def test_08_deny_no_plan(self): self.assertEqual(self.a.plan(decision(decision_value="DENY"),adapter_sequence=1,created_at_epoch=105)["plan_status"],"NO_PLAN")
    def test_09_no_action_no_plan(self): self.assertEqual(self.a.plan(decision("NO_ACTION","NO_ACTION"),adapter_sequence=1,created_at_epoch=105)["plan_status"],"NO_PLAN")
    def test_10_deny_no_args(self): self.assertEqual(self.a.plan(decision(decision_value="DENY"),adapter_sequence=1,created_at_epoch=105)["argument_vector"],[])
    def test_11_no_action_none_operation(self): self.assertIsNone(self.a.plan(decision("NO_ACTION","NO_ACTION"),adapter_sequence=1,created_at_epoch=105)["native_operation"])
    def test_12_chain(self):
        p1=self.a.plan(decision(sequence=1),adapter_sequence=1,created_at_epoch=105)
        p2=self.a.plan(decision("RELEASE",sequence=2),adapter_sequence=2,created_at_epoch=106)
        self.assertEqual(p2["previous_plan_digest"],p1["plan_digest"])
    def test_13_adapter_sequence_regression(self):
        self.a.plan(decision(sequence=1),adapter_sequence=2,created_at_epoch=105)
        with self.assertRaises(m.AdapterRejected):self.a.plan(decision("RELEASE",sequence=2),adapter_sequence=1,created_at_epoch=106)
    def test_14_gateway_replay(self):
        self.a.plan(decision(sequence=2),adapter_sequence=1,created_at_epoch=105)
        with self.assertRaises(m.AdapterRejected):self.a.plan(decision("RELEASE",sequence=2),adapter_sequence=2,created_at_epoch=106)
    def test_15_time_reverse(self):
        with self.assertRaises(m.AdapterRejected):self.a.plan(decision(decided=100),adapter_sequence=1,created_at_epoch=99)
    def test_16_too_old(self):
        with self.assertRaises(m.AdapterRejected):self.a.plan(decision(decided=50),adapter_sequence=1,created_at_epoch=100)
    def test_17_tampered_decision(self):
        x=decision();x["decision"]="DENY"
        with self.assertRaises(m.AdapterRejected):self.a.plan(x,adapter_sequence=1,created_at_epoch=105)
    def test_18_wrong_subject(self):
        x=decision();b=dict(x);b.pop("gateway_decision_digest");b["container_id"]="c"*64;x={**b,"gateway_decision_digest":m.digest(b)}
        with self.assertRaises(m.AdapterRejected) as c:self.a.plan(x,adapter_sequence=1,created_at_epoch=105)
        self.assertEqual(c.exception.reason_code,"SUBJECT_MISMATCH")
    def test_19_wrong_config(self):
        x=decision();b=dict(x);b.pop("gateway_decision_digest");b["configuration_digest"]="sha256:"+"c"*64;x={**b,"gateway_decision_digest":m.digest(b)}
        with self.assertRaises(m.AdapterRejected) as c:self.a.plan(x,adapter_sequence=1,created_at_epoch=105)
        self.assertEqual(c.exception.reason_code,"CONFIGURATION_MISMATCH")
    def test_20_bad_action(self):
        x=decision();b=dict(x);b.pop("gateway_decision_digest");b["projected_action"]="BAD";x={**b,"gateway_decision_digest":m.digest(b)}
        with self.assertRaises(m.AdapterRejected):self.a.plan(x,adapter_sequence=1,created_at_epoch=105)
    def test_21_bad_decision_value(self):
        x=decision();b=dict(x);b.pop("gateway_decision_digest");b["decision"]="BAD";x={**b,"gateway_decision_digest":m.digest(b)}
        with self.assertRaises(m.AdapterRejected):self.a.plan(x,adapter_sequence=1,created_at_epoch=105)
    def test_22_extra_decision_field(self):
        x=decision();x["extra"]=1
        with self.assertRaises(m.AdapterRejected):self.a.plan(x,adapter_sequence=1,created_at_epoch=105)
    def test_23_bad_adapter_sequence(self):
        with self.assertRaises(m.AdapterRejected):self.a.plan(decision(),adapter_sequence=-1,created_at_epoch=105)
    def test_24_bad_created_time(self):
        with self.assertRaises(m.AdapterRejected):self.a.plan(decision(),adapter_sequence=1,created_at_epoch=-1)
    def test_25_bad_container(self):
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter("z"*64,CFG,POLICY)
    def test_26_bad_config(self):
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter(CID,"bad",POLICY)
    def test_27_bad_policy_fields(self):
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter(CID,CFG,{})
    def test_28_bad_policy_version(self):
        p=dict(POLICY);p["policy_version"]="2"
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter(CID,CFG,p)
    def test_29_bad_binary(self):
        p=dict(POLICY);p["docker_binary"]="podman"
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter(CID,CFG,p)
    def test_30_bad_age(self):
        p=dict(POLICY);p["max_decision_age_seconds"]=0
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter(CID,CFG,p)
    def test_31_dry_run_required(self):
        p=dict(POLICY);p["dry_run_required"]=False
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter(CID,CFG,p)
    def test_32_plan_tamper(self):
        p=self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105);p["native_operation"]="unpause"
        with self.assertRaises(m.AdapterRejected):m.DryRunNativeActionAdapter.verify_plan(p)
    def test_33_plan_digest_tamper(self):
        p=self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105);p["plan_digest"]="sha256:"+"f"*64
        with self.assertRaises(m.AdapterRejected):m.DryRunNativeActionAdapter.verify_plan(p)
    def test_34_plan_extra_field(self):
        p=self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105);p["extra"]=1
        with self.assertRaises(m.AdapterRejected):m.DryRunNativeActionAdapter.verify_plan(p)
    def test_35_argument_tamper(self):
        p=self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105);p["argument_vector"][1]="unpause"
        with self.assertRaises(m.AdapterRejected):m.DryRunNativeActionAdapter.verify_plan(p)
    def test_36_no_plan_operation_tamper(self):
        p=self.a.plan(decision(decision_value="DENY"),adapter_sequence=1,created_at_epoch=105);p["native_operation"]="pause"
        with self.assertRaises(m.AdapterRejected):m.DryRunNativeActionAdapter.verify_plan(p)
    def test_37_policy_digest_bound(self): self.assertEqual(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["adapter_policy_digest"],self.a.policy_digest)
    def test_38_gateway_digest_bound(self):
        d=decision();self.assertEqual(self.a.plan(d,adapter_sequence=1,created_at_epoch=105)["gateway_decision_digest"],d["gateway_decision_digest"])
    def test_39_subject_bound(self): self.assertEqual(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["container_id"],CID)
    def test_40_config_bound(self): self.assertEqual(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["configuration_digest"],CFG)
    def test_41_state_copy(self):
        s=self.a.state;s["last_adapter_sequence"]=99;self.assertEqual(self.a.state["last_adapter_sequence"],-1)
    def test_42_no_execute_method(self): self.assertNotIn("execute",dir(self.a))
    def test_43_no_run_method(self): self.assertNotIn("run",dir(self.a))
    def test_44_no_submit_method(self): self.assertNotIn("submit",dir(self.a))
    def test_45_no_pause_method(self): self.assertNotIn("pause",dir(self.a))
    def test_46_no_unpause_method(self): self.assertNotIn("unpause",dir(self.a))
    def test_47_no_shell_field(self): self.assertNotIn("shell",self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105))
    def test_48_no_socket_field(self): self.assertNotIn("socket",json.dumps(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)).lower())
    def test_49_float_policy_rejected(self):
        p=dict(POLICY);p["max_decision_age_seconds"]=1.5
        with self.assertRaises(ValueError):m.DryRunNativeActionAdapter(CID,CFG,p)
    def test_50_float_digest_rejected(self):
        with self.assertRaises(TypeError):m.digest({"x":1.5})
    def test_51_first_previous_digest_zero(self): self.assertEqual(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["previous_plan_digest"],m.ZERO_DIGEST)
    def test_52_exact_binary_only(self): self.assertEqual(self.a.plan(decision(),adapter_sequence=1,created_at_epoch=105)["argument_vector"][0],"docker")

if __name__=="__main__": unittest.main()
