import copy, importlib.util, json, sys, unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"projection"/"bounded_action_projector.py"
spec=importlib.util.spec_from_file_location("proj",P)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

CID="a"*64
CFG="sha256:"+"b"*64
POLICY={"policy_version":"1","max_incident_age_seconds":30,"request_ttl_seconds":15,"release_requires_approval":True}

def incident(closed=False):
    body={
        "schema_version":"1","incident_id":"incident-0001","container_id":CID,
        "configuration_digest":CFG,"entry_count":1,"closed":closed,
        "entries":[{"x":1}],"terminal_entry_digest":"sha256:"+"1"*64,
    }
    return {**body,"export_digest":m.digest(body)}

class T(unittest.TestCase):
    def setUp(self): self.p=m.BoundedActionProjector(CID,CFG,POLICY)
    def project(self,**kw):
        args=dict(incident_export=incident(),observed_state="RUNNING",health_state="HEALTHY",
                  recovery_approved=False,projection_sequence=1,issued_at_epoch=100,
                  latest_evidence_epoch=95)
        args.update(kw);return self.p.project(**args)

    def test_01_hold(self): self.assertEqual(self.project(health_state="UNHEALTHY")["projected_action"],"HOLD")
    def test_02_release(self): self.assertEqual(self.project(observed_state="PAUSED",health_state="HEALTHY",recovery_approved=True)["projected_action"],"RELEASE")
    def test_03_no_action(self): self.assertEqual(self.project()["projected_action"],"NO_ACTION")
    def test_04_release_needs_approval(self): self.assertEqual(self.project(observed_state="PAUSED")["projected_action"],"NO_ACTION")
    def test_05_determinism(self): self.assertEqual(self.project(),self.project())
    def test_06_verify(self): self.assertTrue(m.BoundedActionProjector.verify_projection(self.project())["verification_pass"])
    def test_07_hold_reason(self): self.assertEqual(self.project(health_state="UNHEALTHY")["reason_code"],"UNHEALTHY_RUNNING")
    def test_08_release_reason(self): self.assertEqual(self.project(observed_state="PAUSED",recovery_approved=True)["reason_code"],"HEALTHY_PAUSED_APPROVED")
    def test_09_no_match_reason(self): self.assertEqual(self.project()["reason_code"],"NO_MATCH")
    def test_10_closed_no_action(self): self.assertEqual(self.project(incident_export=incident(True))["reason_code"],"INCIDENT_CLOSED")
    def test_11_stale_no_action(self): self.assertEqual(self.project(latest_evidence_epoch=60)["reason_code"],"STALE_INCIDENT")
    def test_12_future_no_action(self): self.assertEqual(self.project(latest_evidence_epoch=101)["reason_code"],"AMBIGUOUS_EVIDENCE")
    def test_13_bad_state_no_action(self): self.assertEqual(self.project(observed_state="BAD")["reason_code"],"UNSUPPORTED_STATE")
    def test_14_bad_health_no_action(self): self.assertEqual(self.project(health_state="BAD")["reason_code"],"AMBIGUOUS_EVIDENCE")
    def test_15_tampered_incident(self):
        x=incident();x["closed"]=True
        with self.assertRaises(m.ProjectionRejected):self.project(incident_export=x)
    def test_16_wrong_subject(self):
        x=incident();b=dict(x);b.pop("export_digest");b["container_id"]="c"*64;x={**b,"export_digest":m.digest(b)}
        with self.assertRaises(m.ProjectionRejected) as c:self.project(incident_export=x)
        self.assertEqual(c.exception.reason_code,"SUBJECT_MISMATCH")
    def test_17_wrong_config(self):
        x=incident();b=dict(x);b.pop("export_digest");b["configuration_digest"]="sha256:"+"c"*64;x={**b,"export_digest":m.digest(b)}
        with self.assertRaises(m.ProjectionRejected) as c:self.project(incident_export=x)
        self.assertEqual(c.exception.reason_code,"CONFIGURATION_MISMATCH")
    def test_18_extra_incident_field(self):
        x=incident();x["extra"]=1
        with self.assertRaises(m.ProjectionRejected):self.project(incident_export=x)
    def test_19_bad_policy_fields(self):
        with self.assertRaises(ValueError):m.BoundedActionProjector(CID,CFG,{})
    def test_20_bad_policy_version(self):
        p=dict(POLICY);p["policy_version"]="2"
        with self.assertRaises(ValueError):m.BoundedActionProjector(CID,CFG,p)
    def test_21_bad_ttl(self):
        p=dict(POLICY);p["request_ttl_seconds"]=0
        with self.assertRaises(ValueError):m.BoundedActionProjector(CID,CFG,p)
    def test_22_bad_age(self):
        p=dict(POLICY);p["max_incident_age_seconds"]=0
        with self.assertRaises(ValueError):m.BoundedActionProjector(CID,CFG,p)
    def test_23_bad_approval_type(self):
        p=dict(POLICY);p["release_requires_approval"]=1
        with self.assertRaises(ValueError):m.BoundedActionProjector(CID,CFG,p)
    def test_24_bad_container(self):
        with self.assertRaises(ValueError):m.BoundedActionProjector("z"*64,CFG,POLICY)
    def test_25_bad_config(self):
        with self.assertRaises(ValueError):m.BoundedActionProjector(CID,"bad",POLICY)
    def test_26_bad_sequence(self):
        with self.assertRaises(m.ProjectionRejected):self.project(projection_sequence=-1)
    def test_27_bad_issued(self):
        with self.assertRaises(m.ProjectionRejected):self.project(issued_at_epoch=-1)
    def test_28_bad_latest(self):
        with self.assertRaises(m.ProjectionRejected):self.project(latest_evidence_epoch=-1)
    def test_29_bad_approval(self):
        with self.assertRaises(m.ProjectionRejected):self.project(recovery_approved=1)
    def test_30_projection_digest_tamper(self):
        x=self.project();x["projection_digest"]="sha256:"+"f"*64
        with self.assertRaises(m.ProjectionRejected):m.BoundedActionProjector.verify_projection(x)
    def test_31_projection_payload_tamper(self):
        x=self.project();x["projected_action"]="HOLD"
        with self.assertRaises(m.ProjectionRejected):m.BoundedActionProjector.verify_projection(x)
    def test_32_projection_extra_field(self):
        x=self.project();x["extra"]=1
        with self.assertRaises(m.ProjectionRejected):m.BoundedActionProjector.verify_projection(x)
    def test_33_expiry_after_issue(self):
        x=self.project();self.assertGreater(x["expires_at_epoch"],x["issued_at_epoch"])
    def test_34_policy_digest_bound(self):
        self.assertEqual(self.project()["policy_digest"],self.p.policy_digest)
    def test_35_incident_digest_bound(self):
        self.assertEqual(self.project()["incident_export_digest"],incident()["export_digest"])
    def test_36_subject_bound(self): self.assertEqual(self.project()["container_id"],CID)
    def test_37_config_bound(self): self.assertEqual(self.project()["configuration_digest"],CFG)
    def test_38_no_command_field(self): self.assertNotIn("command",self.project())
    def test_39_no_gateway_field(self): self.assertNotIn("gateway",json.dumps(self.project()).lower())
    def test_40_no_docker_execution_fields(self):
        record=self.project()
        self.assertTrue({"docker_command","docker_socket","native_operation"}.isdisjoint(record))
    def test_41_no_executor_type(self): self.assertTrue({"execute","run","submit"}.isdisjoint(set(dir(self.p))))
    def test_42_release_without_approval_when_policy_allows(self):
        p=dict(POLICY);p["release_requires_approval"]=False
        q=m.BoundedActionProjector(CID,CFG,p)
        r=q.project(incident_export=incident(),observed_state="PAUSED",health_state="HEALTHY",
                    recovery_approved=False,projection_sequence=1,issued_at_epoch=100,latest_evidence_epoch=95)
        self.assertEqual(r["projected_action"],"RELEASE")
    def test_43_float_policy_rejected(self):
        p=dict(POLICY);p["request_ttl_seconds"]=1.5
        with self.assertRaises(ValueError):m.BoundedActionProjector(CID,CFG,p)
    def test_44_float_record_not_possible(self):
        with self.assertRaises(TypeError):m.digest({"x":1.5})

if __name__=="__main__": unittest.main()
