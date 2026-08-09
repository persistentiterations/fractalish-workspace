from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=argparse.ArgumentParser()
p.add_argument("--container-id",required=True)
p.add_argument("--acknowledge-disposable-container",action="store_true")
p.add_argument("--issued-at-epoch",type=int,default=7317)
a=p.parse_args()
if not a.acknowledge_disposable_container:raise SystemExit("Refused: disposable-container acknowledgement required")
q=load(BASE/"src"/"bolt_on_continuity"/"qualification"/"adversarial_recovery.py","_s9q")
e=load(BASE/"src"/"bolt_on_continuity"/"execution"/"controlled_native_executor.py","_s9e")
r=q.BoundedRecoveryQualifier(BASE,a.container_id,e.DockerSubprocessTransport()).qualify(a.issued_at_epoch)
print(json.dumps(r,sort_keys=True,separators=(",",":")))
if r["qualified"] is not True or r["injected_failure_count"]!=1:raise SystemExit("Stage 9 did not qualify")
if r["final_state"]["running"] is not True or r["final_state"]["paused"] is not False:raise SystemExit("terminal state invalid")
print("STAGE 9 CONTROLLED LIVE RECOVERY QUALIFICATION: PASS")
