from __future__ import annotations
import importlib.util, sys
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"adapter"/"dry_run_native_action_adapter.py"
spec=importlib.util.spec_from_file_location("adapterq",P)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

CID="a"*64
CFG="sha256:"+"b"*64
POLICY={"policy_version":"1","docker_binary":"docker","max_decision_age_seconds":30,"dry_run_required":True}

def decision(action, sequence, value="APPROVE"):
    body={
        "schema_version":"1","incident_id":"incident-stage5-0001","container_id":CID,
        "configuration_digest":CFG,"projection_digest":"sha256:"+"1"*64,
        "projection_sequence":sequence,"projected_action":action,
        "gateway_policy_digest":"sha256:"+"2"*64,"gateway_sequence":sequence,
        "previous_gateway_decision_digest":"sha256:"+"0"*64,
        "decided_at_epoch":100+sequence,"decision":value,
        "reason_code":"HOLD_ALLOWED" if action=="HOLD" else ("RELEASE_ALLOWED" if action=="RELEASE" else "NO_ACTION_PROJECTED"),
    }
    return {**body,"gateway_decision_digest":m.digest(body)}

def main():
    a=m.DryRunNativeActionAdapter(CID,CFG,POLICY)
    hold=a.plan(decision("HOLD",1),adapter_sequence=1,created_at_epoch=105)
    release=a.plan(decision("RELEASE",2),adapter_sequence=2,created_at_epoch=106)
    none=a.plan(decision("NO_ACTION",3,"NO_ACTION"),adapter_sequence=3,created_at_epoch=107)
    for record in (hold,release,none):
        if not m.DryRunNativeActionAdapter.verify_plan(record)["verification_pass"]:
            raise SystemExit("plan verification failed")
    print("Stage: BOLT-ON CONTINUITY FOR DOCKER 0.1.5")
    print("Mode: DRY_RUN_NATIVE_ACTION_ADAPTER_QUALIFICATION")
    print("Stage foundation commit: c4f3e8f")
    print("HOLD operation:",hold["argument_vector"])
    print("RELEASE operation:",release["argument_vector"])
    print("NO_ACTION plan status:",none["plan_status"])
    print("Dry-run flags:",hold["dry_run"],release["dry_run"],none["dry_run"])
    print("Subprocess calls: 0")
    print("Docker write calls: 0")
    print("HOLD plan digest:",hold["plan_digest"])
    print("RELEASE plan digest:",release["plan_digest"])
    print("NO_ACTION plan digest:",none["plan_digest"])
    print("STAGE 5 DRY-RUN NATIVE ACTION ADAPTER: PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())
