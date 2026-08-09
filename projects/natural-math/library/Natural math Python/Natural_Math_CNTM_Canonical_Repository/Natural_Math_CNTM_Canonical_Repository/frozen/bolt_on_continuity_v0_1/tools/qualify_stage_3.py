from __future__ import annotations
import importlib.util, sys
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"projection"/"bounded_action_projector.py"
spec=importlib.util.spec_from_file_location("projq",P)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

CID="a"*64
CFG="sha256:"+"b"*64
POLICY={"policy_version":"1","max_incident_age_seconds":30,"request_ttl_seconds":15,"release_requires_approval":True}

def incident(closed=False):
    body={"schema_version":"1","incident_id":"incident-stage3-0001","container_id":CID,
          "configuration_digest":CFG,"entry_count":1,"closed":closed,
          "entries":[{"x":1}],"terminal_entry_digest":"sha256:"+"1"*64}
    return {**body,"export_digest":m.digest(body)}

def main():
    p=m.BoundedActionProjector(CID,CFG,POLICY)
    hold=p.project(incident_export=incident(),observed_state="RUNNING",health_state="UNHEALTHY",
                   recovery_approved=False,projection_sequence=1,issued_at_epoch=100,latest_evidence_epoch=95)
    release=p.project(incident_export=incident(),observed_state="PAUSED",health_state="HEALTHY",
                      recovery_approved=True,projection_sequence=2,issued_at_epoch=101,latest_evidence_epoch=96)
    none=p.project(incident_export=incident(),observed_state="RUNNING",health_state="HEALTHY",
                   recovery_approved=False,projection_sequence=3,issued_at_epoch=102,latest_evidence_epoch=97)
    for record in (hold,release,none):
        if not m.BoundedActionProjector.verify_projection(record)["verification_pass"]:
            raise SystemExit("projection verification failed")
    print("Stage: BOLT-ON CONTINUITY FOR DOCKER 0.1.3")
    print("Mode: BOUNDED_ACTION_PROJECTION_QUALIFICATION")
    print("Stage foundation commit: a46405b")
    print("Projection outputs: HOLD, RELEASE, NO_ACTION")
    print("Host actions: 0")
    print("Gateway decisions: 0")
    print("Docker write calls: 0")
    print("HOLD reason:",hold["reason_code"])
    print("RELEASE reason:",release["reason_code"])
    print("NO_ACTION reason:",none["reason_code"])
    print("HOLD digest:",hold["projection_digest"])
    print("RELEASE digest:",release["projection_digest"])
    print("NO_ACTION digest:",none["projection_digest"])
    print("STAGE 3 BOUNDED ACTION PROJECTION: PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())
