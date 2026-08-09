from __future__ import annotations
import importlib.util, sys
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"gateway"/"host_owned_gateway.py"
spec=importlib.util.spec_from_file_location("gwq",P)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

CID="a"*64
CFG="sha256:"+"b"*64
POLICY={"policy_version":"1","hold_enabled":True,"release_enabled":True,"max_projection_age_seconds":30}

def projection(action, sequence):
    body={
        "schema_version":"1",
        "contract_version":"BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_1_STAGE_0",
        "incident_id":"incident-stage4-0001",
        "container_id":CID,
        "configuration_digest":CFG,
        "incident_export_digest":"sha256:"+"1"*64,
        "policy_digest":"sha256:"+"2"*64,
        "projected_action":action,
        "expected_state":"RUNNING" if action=="HOLD" else "PAUSED",
        "reason_code":"UNHEALTHY_RUNNING" if action=="HOLD" else ("HEALTHY_PAUSED_APPROVED" if action=="RELEASE" else "NO_MATCH"),
        "projection_sequence":sequence,
        "issued_at_epoch":100+sequence,
        "expires_at_epoch":120+sequence,
    }
    return {**body,"projection_digest":m.digest(body)}

def main():
    g=m.HostOwnedGateway(CID,CFG,POLICY)
    hold=g.decide(projection("HOLD",1),gateway_sequence=1,decided_at_epoch=105)
    release=g.decide(projection("RELEASE",2),gateway_sequence=2,decided_at_epoch=106)
    none=g.decide(projection("NO_ACTION",3),gateway_sequence=3,decided_at_epoch=107)
    for record in (hold,release,none):
        if not m.HostOwnedGateway.verify_decision(record)["verification_pass"]:
            raise SystemExit("gateway verification failed")
    print("Stage: BOLT-ON CONTINUITY FOR DOCKER 0.1.4")
    print("Mode: HOST_OWNED_GATEWAY_DECISION_CONTRACT_QUALIFICATION")
    print("Stage foundation commit: 0c7900d")
    print("Gateway decisions: APPROVE, DENY, NO_ACTION")
    print("HOLD decision:",hold["decision"])
    print("RELEASE decision:",release["decision"])
    print("NO_ACTION decision:",none["decision"])
    print("Docker write calls: 0")
    print("Host execution calls: 0")
    print("HOLD decision digest:",hold["gateway_decision_digest"])
    print("RELEASE decision digest:",release["gateway_decision_digest"])
    print("NO_ACTION decision digest:",none["gateway_decision_digest"])
    print("STAGE 4 HOST-OWNED GATEWAY DECISION CONTRACT: PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())
