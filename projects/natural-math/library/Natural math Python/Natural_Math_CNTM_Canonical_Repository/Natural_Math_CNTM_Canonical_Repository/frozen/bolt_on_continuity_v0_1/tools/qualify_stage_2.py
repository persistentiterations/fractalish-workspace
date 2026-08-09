from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"ledger"/"incident_ledger.py"
spec=importlib.util.spec_from_file_location("ledgerq",P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
CID="a"*64;CFG="sha256:"+"b"*64
def main():
    l=m.IncidentLedger("incident-stage2-0001",CID,CFG)
    l.append("INCIDENT_OPENED",100,"sha256:"+"1"*64,{"state":"RUNNING"})
    l.append("OBSERVATION_RECORDED",101,"sha256:"+"2"*64,{"health":"HEALTHY"})
    l.append("STATE_CHANGED",102,"sha256:"+"3"*64,{"from":"RUNNING","to":"PAUSED"})
    l.append("INCIDENT_NOTE",103,"sha256:"+"3"*64,{"note":"bounded fixture"})
    l.append("INCIDENT_CLOSED",104,"sha256:"+"4"*64,{"reason":"qualified"})
    export=l.export();replay=m.IncidentLedger.replay_export(export)
    rejected=0
    for mut in [
        lambda x:x["entries"][1].update(entry_digest="sha256:"+"f"*64),
        lambda x:x["entries"].reverse(),
        lambda x:x["entries"].pop(1),
        lambda x:x.update(export_digest="sha256:"+"f"*64),
        lambda x:x["entries"][1].update(container_id="c"*64),
    ]:
        import copy
        x=copy.deepcopy(export);mut(x)
        try:m.IncidentLedger.replay_export(x)
        except m.LedgerRejected:rejected+=1
        else:raise SystemExit("tamper accepted")
    print("Stage: BOLT-ON CONTINUITY FOR DOCKER 0.1.2")
    print("Mode: DETERMINISTIC_INCIDENT_LEDGER_QUALIFICATION")
    print("Stage foundation commit: f830672")
    print("Incident ID:",export["incident_id"])
    print("Entries:",export["entry_count"])
    print("Closed:",export["closed"])
    print("Host actions: 0")
    print("Action projections: 0")
    print("Gateway decisions: 0")
    print("Tamper cases:",5)
    print("Tamper cases safely rejected:",rejected)
    print("Terminal entry digest:",export["terminal_entry_digest"])
    print("Export digest:",export["export_digest"])
    print("Replay export digest:",replay["export_digest"])
    print("STAGE 2 DETERMINISTIC INCIDENT LEDGER: PASS")
    return 0
if __name__=="__main__":raise SystemExit(main())
