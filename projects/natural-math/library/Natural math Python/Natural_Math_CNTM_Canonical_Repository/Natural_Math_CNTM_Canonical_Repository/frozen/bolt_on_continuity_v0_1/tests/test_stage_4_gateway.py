import copy, importlib.util, json, sys, unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"gateway"/"host_owned_gateway.py"
spec=importlib.util.spec_from_file_location("gw",P)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

CID="a"*64
CFG="sha256:"+"b"*64
POLICY={"policy_version":"1","hold_enabled":True,"release_enabled":True,"max_projection_age_seconds":30}

def projection(action="HOLD", sequence=1, issued=100, expires=115):
    body={
        "schema_version":"1",
        "contract_version":"BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_1_STAGE_0",
        "incident_id":"incident-0001",
        "container_id":CID,
        "configuration_digest":CFG,
        "incident_export_digest":"sha256:"+"1"*64,
        "policy_digest":"sha256:"+"2"*64,
        "projected_action":action,
        "expected_state":"RUNNING" if action=="HOLD" else "PAUSED",
        "reason_code":"UNHEALTHY_RUNNING" if action=="HOLD" else ("HEALTHY_PAUSED_APPROVED" if action=="RELEASE" else "NO_MATCH"),
        "projection_sequence":sequence,
        "issued_at_epoch":issued,
        "expires_at_epoch":expires,
    }
    return {**body,"projection_digest":m.digest(body)}

class T(unittest.TestCase):
    def setUp(self): self.g=m.HostOwnedGateway(CID,CFG,POLICY)

    def test_01_hold_approve(self): self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)["decision"],"APPROVE")
    def test_02_release_approve(self): self.assertEqual(self.g.decide(projection("RELEASE"),gateway_sequence=1,decided_at_epoch=105)["decision"],"APPROVE")
    def test_03_no_action(self): self.assertEqual(self.g.decide(projection("NO_ACTION"),gateway_sequence=1,decided_at_epoch=105)["decision"],"NO_ACTION")
    def test_04_hold_reason(self): self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)["reason_code"],"HOLD_ALLOWED")
    def test_05_release_reason(self): self.assertEqual(self.g.decide(projection("RELEASE"),gateway_sequence=1,decided_at_epoch=105)["reason_code"],"RELEASE_ALLOWED")
    def test_06_no_action_reason(self): self.assertEqual(self.g.decide(projection("NO_ACTION"),gateway_sequence=1,decided_at_epoch=105)["reason_code"],"NO_ACTION_PROJECTED")
    def test_07_hold_disabled(self):
        p=dict(POLICY);p["hold_enabled"]=False
        g=m.HostOwnedGateway(CID,CFG,p)
        self.assertEqual(g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)["reason_code"],"HOLD_DISABLED")
    def test_08_release_disabled(self):
        p=dict(POLICY);p["release_enabled"]=False
        g=m.HostOwnedGateway(CID,CFG,p)
        self.assertEqual(g.decide(projection("RELEASE"),gateway_sequence=1,decided_at_epoch=105)["reason_code"],"RELEASE_DISABLED")
    def test_09_expired(self): self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=116)["reason_code"],"PROJECTION_EXPIRED")
    def test_10_future_decision(self): self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=99)["reason_code"],"DECISION_TIME_PRECEDES_PROJECTION")
    def test_11_too_old(self):
        p=dict(POLICY);p["max_projection_age_seconds"]=2
        g=m.HostOwnedGateway(CID,CFG,p)
        self.assertEqual(g.decide(projection(expires=200),gateway_sequence=1,decided_at_epoch=105)["reason_code"],"PROJECTION_TOO_OLD")
    def test_12_verify(self):
        r=self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)
        self.assertTrue(m.HostOwnedGateway.verify_decision(r)["verification_pass"])
    def test_13_determinism(self):
        g1=m.HostOwnedGateway(CID,CFG,POLICY);g2=m.HostOwnedGateway(CID,CFG,POLICY)
        self.assertEqual(g1.decide(projection(),gateway_sequence=1,decided_at_epoch=105),g2.decide(projection(),gateway_sequence=1,decided_at_epoch=105))
    def test_14_chain(self):
        a=self.g.decide(projection(sequence=1),gateway_sequence=1,decided_at_epoch=105)
        b=self.g.decide(projection("RELEASE",sequence=2),gateway_sequence=2,decided_at_epoch=106)
        self.assertEqual(b["previous_gateway_decision_digest"],a["gateway_decision_digest"])
    def test_15_gateway_sequence_regression(self):
        self.g.decide(projection(sequence=1),gateway_sequence=2,decided_at_epoch=105)
        self.assertEqual(self.g.decide(projection("RELEASE",sequence=2),gateway_sequence=1,decided_at_epoch=106)["reason_code"],"GATEWAY_SEQUENCE_REGRESSION")
    def test_16_projection_replay(self):
        self.g.decide(projection(sequence=2),gateway_sequence=1,decided_at_epoch=105)
        self.assertEqual(self.g.decide(projection("RELEASE",sequence=2),gateway_sequence=2,decided_at_epoch=106)["reason_code"],"PROJECTION_REPLAY")
    def test_17_tampered_projection(self):
        x=projection();x["projected_action"]="RELEASE"
        with self.assertRaises(m.GatewayRejected):self.g.decide(x,gateway_sequence=1,decided_at_epoch=105)
    def test_18_wrong_subject(self):
        x=projection();b=dict(x);b.pop("projection_digest");b["container_id"]="c"*64;x={**b,"projection_digest":m.digest(b)}
        with self.assertRaises(m.GatewayRejected) as c:self.g.decide(x,gateway_sequence=1,decided_at_epoch=105)
        self.assertEqual(c.exception.reason_code,"SUBJECT_MISMATCH")
    def test_19_wrong_config(self):
        x=projection();b=dict(x);b.pop("projection_digest");b["configuration_digest"]="sha256:"+"c"*64;x={**b,"projection_digest":m.digest(b)}
        with self.assertRaises(m.GatewayRejected) as c:self.g.decide(x,gateway_sequence=1,decided_at_epoch=105)
        self.assertEqual(c.exception.reason_code,"CONFIGURATION_MISMATCH")
    def test_20_extra_projection_field(self):
        x=projection();x["extra"]=1
        with self.assertRaises(m.GatewayRejected):self.g.decide(x,gateway_sequence=1,decided_at_epoch=105)
    def test_21_bad_action(self):
        x=projection();b=dict(x);b.pop("projection_digest");b["projected_action"]="BAD";x={**b,"projection_digest":m.digest(b)}
        with self.assertRaises(m.GatewayRejected):self.g.decide(x,gateway_sequence=1,decided_at_epoch=105)
    def test_22_bad_gateway_sequence(self):
        with self.assertRaises(m.GatewayRejected):self.g.decide(projection(),gateway_sequence=-1,decided_at_epoch=105)
    def test_23_bad_decision_time(self):
        with self.assertRaises(m.GatewayRejected):self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=-1)
    def test_24_bad_container(self):
        with self.assertRaises(ValueError):m.HostOwnedGateway("z"*64,CFG,POLICY)
    def test_25_bad_config(self):
        with self.assertRaises(ValueError):m.HostOwnedGateway(CID,"bad",POLICY)
    def test_26_bad_policy_fields(self):
        with self.assertRaises(ValueError):m.HostOwnedGateway(CID,CFG,{})
    def test_27_bad_policy_version(self):
        p=dict(POLICY);p["policy_version"]="2"
        with self.assertRaises(ValueError):m.HostOwnedGateway(CID,CFG,p)
    def test_28_bad_hold_type(self):
        p=dict(POLICY);p["hold_enabled"]=1
        with self.assertRaises(ValueError):m.HostOwnedGateway(CID,CFG,p)
    def test_29_bad_release_type(self):
        p=dict(POLICY);p["release_enabled"]=1
        with self.assertRaises(ValueError):m.HostOwnedGateway(CID,CFG,p)
    def test_30_bad_age(self):
        p=dict(POLICY);p["max_projection_age_seconds"]=0
        with self.assertRaises(ValueError):m.HostOwnedGateway(CID,CFG,p)
    def test_31_decision_tamper(self):
        r=self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105);r["decision"]="DENY"
        with self.assertRaises(m.GatewayRejected):m.HostOwnedGateway.verify_decision(r)
    def test_32_decision_digest_tamper(self):
        r=self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105);r["gateway_decision_digest"]="sha256:"+"f"*64
        with self.assertRaises(m.GatewayRejected):m.HostOwnedGateway.verify_decision(r)
    def test_33_decision_extra_field(self):
        r=self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105);r["extra"]=1
        with self.assertRaises(m.GatewayRejected):m.HostOwnedGateway.verify_decision(r)
    def test_34_policy_digest_bound(self):
        self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)["gateway_policy_digest"],self.g.policy_digest)
    def test_35_projection_digest_bound(self):
        p=projection();self.assertEqual(self.g.decide(p,gateway_sequence=1,decided_at_epoch=105)["projection_digest"],p["projection_digest"])
    def test_36_subject_bound(self): self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)["container_id"],CID)
    def test_37_config_bound(self): self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)["configuration_digest"],CFG)
    def test_38_state_copy(self):
        s=self.g.state;s["last_gateway_sequence"]=999;self.assertEqual(self.g.state["last_gateway_sequence"],-1)
    def test_39_no_command_field(self): self.assertNotIn("command",self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105))
    def test_40_no_socket_field(self): self.assertNotIn("socket",json.dumps(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)).lower())
    def test_41_no_executor_methods(self): self.assertTrue({"execute","run","submit","pause","unpause"}.isdisjoint(set(dir(self.g))))
    def test_42_float_policy_rejected(self):
        p=dict(POLICY);p["max_projection_age_seconds"]=1.5
        with self.assertRaises(ValueError):m.HostOwnedGateway(CID,CFG,p)
    def test_43_float_digest_rejected(self):
        with self.assertRaises(TypeError):m.digest({"x":1.5})
    def test_44_previous_digest_zero_first(self):
        self.assertEqual(self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)["previous_gateway_decision_digest"],m.ZERO_DIGEST)
    def test_45_projection_sequence_recorded(self):
        self.assertEqual(self.g.decide(projection(sequence=7),gateway_sequence=1,decided_at_epoch=105)["projection_sequence"],7)
    def test_46_gateway_sequence_recorded(self):
        self.assertEqual(self.g.decide(projection(),gateway_sequence=9,decided_at_epoch=105)["gateway_sequence"],9)
    def test_47_decision_enum(self):
        r=self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105);self.assertIn(r["decision"],m.DECISIONS)
    def test_48_host_actions_absent(self):
        r=self.g.decide(projection(),gateway_sequence=1,decided_at_epoch=105)
        self.assertTrue({"native_operation","shell","args","docker_socket","executable"}.isdisjoint(r))

if __name__=="__main__": unittest.main()
