from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/"src"/"bolt_on_continuity"/"observer"/"read_only_docker_observer.py"
spec=importlib.util.spec_from_file_location("stage1q",P)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
CID="a"*64;CFG="sha256:"+"b"*64;NOW=1700000010

def fail(m): print("FAIL:",m); raise SystemExit(1)

def main():
    inspect=(BASE/"fixtures"/"inspect_running.json").read_text(encoding="utf-8")
    events=(BASE/"fixtures"/"events_running.jsonl").read_text(encoding="utf-8").splitlines()
    logs=(BASE/"fixtures"/"logs_running.bin").read_bytes()
    o=mod.ReadOnlyDockerObserver(CID,CFG)
    kw=dict(raw_inspect=inspect,raw_events=events,raw_logs=logs,collection_sequence=7,collected_at_epoch=NOW)
    a=o.normalize_capture(**kw);b=o.normalize_capture(**kw)
    if a!=b:fail("repeat differs")
    replay=o.replay(a)
    if not replay["replay_pass"]:fail("replay failed")
    if mod.DockerCLIReadOnlyTransport().allowed_operations!=frozenset({"inspect","events","logs","version"}):fail("allowlist differs")
    source=P.read_text(encoding="utf-8")
    forbidden=['["pause"','["unpause"','["stop"','["restart"','["kill"','["rm"','["exec"','["update"','["run"','["create"']
    if any(x in source for x in forbidden):fail("write call fragment present")
    cases=[]
    cases.append(("MALFORMED_INSPECT",dict(raw_inspect="{")))
    wrong=json.loads(inspect);wrong[0]["Id"]="c"*64;cases.append(("WRONG_SUBJECT",dict(raw_inspect=json.dumps(wrong))))
    stale=json.loads(events[0]);stale["time"]=NOW-31;cases.append(("STALE_EVIDENCE",dict(raw_events=[json.dumps(stale)])))
    future=json.loads(events[0]);future["time"]=NOW+6;cases.append(("FUTURE_EVIDENCE",dict(raw_events=[json.dumps(future)])))
    cases.append(("LIMIT_EXCEEDED",dict(raw_logs=b"x"*65537)))
    rejected=0
    for expected,override in cases:
        test=dict(kw);test.update(override)
        try:o.normalize_capture(**test)
        except mod.ObservationRejected as e:
            if e.reason_code!=expected:fail(f"expected {expected}, got {e.reason_code}")
            rejected+=1
        else:fail(f"{expected} accepted")
    qd="sha256:"+hashlib.sha256(json.dumps(a,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    n=a["normalized_evidence"];r=a["receipt"]
    print("Stage: BOLT-ON CONTINUITY FOR DOCKER 0.1.1")
    print("Mode: READ_ONLY_DOCKER_OBSERVER_FIXTURE_QUALIFICATION")
    print("Stage foundation commit: 3ba6ca0")
    print("Configured subjects: 1")
    print("Docker write authority: NONE")
    print("Action projection: NONE")
    print("Gateway: NONE")
    print("Read operations: events, inspect, logs, version")
    print("Normalized state:",n["observed_state"])
    print("Normalized health:",n["health_state"])
    print("Events accepted:",n["event_count"])
    print("Log bytes accepted:",n["log_byte_count"])
    print("Adversarial rejection cases:",len(cases))
    print("Adversarial cases safely rejected:",rejected)
    print("Evidence digest:",n["evidence_digest"])
    print("Receipt digest:",r["receipt_digest"])
    print("Replay evidence digest:",replay["evidence_digest"])
    print("Replay receipt digest:",replay["receipt_digest"])
    print("Qualification digest:",qd)
    print("STAGE 1 READ-ONLY DOCKER OBSERVER: PASS")
    return 0
if __name__=="__main__":raise SystemExit(main())
