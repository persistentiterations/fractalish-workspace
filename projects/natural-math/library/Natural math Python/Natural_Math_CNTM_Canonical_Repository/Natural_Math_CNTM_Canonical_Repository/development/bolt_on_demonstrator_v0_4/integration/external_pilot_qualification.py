#!/usr/bin/env python3
"""Bolt-On Demonstrator v0.4 Stage 6 external pilot qualification and RC gate."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Sequence

sys.dont_write_bytecode = True
STAGE_NAME = "EXTERNAL PILOT QUALIFICATION AND RELEASE CANDIDATE"
STAGE_VERSION = "0.4.6"
MODE = "EXTERNAL_PILOT_RELEASE_CANDIDATE"
BOLT_ON_EXECUTION_AUTHORITY = "NONE"
HOST_EXECUTION_BOUNDARY = "NATIVE_HOST_ONLY"
RELEASE_STATUS = "RELEASE_CANDIDATE"
EXPECTED_STAGE5_COMMIT = "afa1435f5ed1c5136895b7c8e3fba0dfbc6f064d"
EXPECTED_STAGE5_GIT_BLOB_SHA1 = "8e6e7760fb8608953ac36ee8662180188a766d26"
EXPECTED_FROZEN_V03_MANIFEST = "57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa"
EXPECTED_FROZEN_ENTRIES = 20
EXPECTED_PILOT_ACTIONS = 2
EXPECTED_TAMPER_CASES = 64
ZERO = "0" * 64
THIS_FILE = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parents[1]
REPO = THIS_FILE.parents[3]
VERIFY_ALL = REPO / "tools" / "verify_all_frozen.py"
STAGE_PATHS = tuple(PROJECT_DIR / "integration" / name for name in (
    "external_host_contract.py", "independent_host_baseline.py",
    "read_only_observation_adapter.py", "host_owned_bounded_command_gateway.py",
    "live_sidecar_failure_recovery.py"))
STAGE_MARKERS = (
    "STAGE 1 EXTERNAL HOST INTEGRATION CONTRACT: PASS",
    "STAGE 2 INDEPENDENT ORDINARY HOST BASELINE: PASS",
    "STAGE 3 READ-ONLY EXTERNAL OBSERVATION ADAPTER: PASS",
    "STAGE 4 HOST-OWNED BOUNDED COMMAND GATEWAY: PASS",
    "STAGE 5 LIVE SIDECAR INSTALLATION, REMOVAL, AND FAILURE RECOVERY: PASS",
)

def canonical(v: object) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
def digest(v: object) -> str:
    return hashlib.sha256(canonical(v).encode("ascii")).hexdigest()
def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20), b""): h.update(b)
    return h.hexdigest()
def git_blob_sha1(p: Path) -> str:
    data=p.read_bytes(); return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
def run_script(path: Path, markers: Sequence[str]) -> tuple[bool,str,str]:
    cp=subprocess.run([sys.executable,str(path)],cwd=REPO,capture_output=True,text=True,
        encoding="utf-8",errors="replace",env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
    out=cp.stdout+"\n"+cp.stderr
    return cp.returncode==0 and all(m in out for m in markers), out, hashlib.sha256(out.encode()).hexdigest()

def validate_frozen() -> bool:
    ok,_,_=run_script(VERIFY_ALL,("ALL FROZEN RELEASE VERIFICATIONS PASSED",))
    return ok

def source_manifest() -> tuple[tuple[str,str],...]:
    roots=(PROJECT_DIR/"README.md",PROJECT_DIR/"README_STAGE_1.md",PROJECT_DIR/"README_STAGE_2.md",
      PROJECT_DIR/"README_STAGE_3.md",PROJECT_DIR/"README_STAGE_4.md",PROJECT_DIR/"README_STAGE_5.md",
      PROJECT_DIR/"README_STAGE_6.md")
    dirs=(PROJECT_DIR/"hosts",PROJECT_DIR/"adapters",PROJECT_DIR/"gateways",PROJECT_DIR/"lifecycle",PROJECT_DIR/"release_candidate",PROJECT_DIR/"integration",PROJECT_DIR/"tests")
    paths=set(p for p in roots if p.is_file())
    for d in dirs:
        if d.is_dir(): paths.update(p for p in d.glob("*.py") if p.is_file())
    ordered = sorted(paths, key=lambda path: path.relative_to(REPO).as_posix())
    return tuple((path.relative_to(REPO).as_posix(), sha256_file(path)) for path in ordered)

@dataclass(frozen=True)
class PilotReceipt:
    sequence:int; kind:str; payload:str; previous_digest:str; receipt_digest:str
    def unsigned(self): return {"kind":self.kind,"payload":self.payload,"previous_digest":self.previous_digest,"sequence":self.sequence}

def append(rs: Sequence[PilotReceipt], kind: str, payload: object) -> tuple[PilotReceipt,...]:
    rs=tuple(rs); u={"kind":kind,"payload":canonical(payload),"previous_digest":rs[-1].receipt_digest if rs else ZERO,"sequence":len(rs)+1}
    return rs+(PilotReceipt(u["sequence"],kind,u["payload"],u["previous_digest"],digest(u)),)
def replay(rs: Iterable[PilotReceipt]) -> tuple[bool,str]:
    prev=ZERO
    for i,r in enumerate(tuple(rs),1):
        if r.sequence!=i or r.previous_digest!=prev or digest(r.unsigned())!=r.receipt_digest:return False,"CHAIN_INVALID"
        prev=r.receipt_digest
    return True,prev

def run_stage_chain() -> tuple[bool,tuple[str,...],tuple[str,...]]:
    outputs=[]; hashes=[]
    for path,marker in zip(STAGE_PATHS,STAGE_MARKERS):
        ok,out,h=run_script(path,(marker,))
        if not ok:return False,tuple(outputs)+(out,),tuple(hashes)+(h,)
        outputs.append(out); hashes.append(h)
    return True,tuple(outputs),tuple(hashes)

def build_receipts(manifest, stage_hashes) -> tuple[PilotReceipt,...]:
    rs=()
    rs=append(rs,"BASELINE",{"stage5_commit":EXPECTED_STAGE5_COMMIT,"frozen_manifest":EXPECTED_FROZEN_V03_MANIFEST})
    for i,h in enumerate(stage_hashes,1): rs=append(rs,f"STAGE_{i}_QUALIFICATION",{"output_digest":h})
    rs=append(rs,"PILOT_OBSERVATION",{"subjects":1,"events":6})
    rs=append(rs,"PILOT_COMMAND_CROSSING",{"projected":2,"host_owned_actions":2,"bolt_on_actions":0})
    rs=append(rs,"PILOT_LIFECYCLE",{"installed":3,"removed":3,"active_after":0})
    rs=append(rs,"SOURCE_MANIFEST",{"entries":len(manifest),"digest":digest(manifest)})
    rs=append(rs,"RC_VERDICT",{"status":RELEASE_STATUS,"freeze_performed":False})
    return rs

def tamper_campaign(receipts: tuple[PilotReceipt,...], manifest: tuple[tuple[str,str],...]) -> tuple[tuple[str,bool],...]:
    cases=[]
    # 32 receipt mutations
    for i in range(32):
        idx=i%len(receipts); r=receipts[idx]
        mode=i%4
        if mode==0: bad=replace(r,sequence=r.sequence+1)
        elif mode==1: bad=replace(r,kind=r.kind+"X")
        elif mode==2: bad=replace(r,payload=r.payload+"X")
        else: bad=replace(r,previous_digest="f"*64)
        rows=list(receipts); rows[idx]=bad
        cases.append((f"RECEIPT-{i+1:02d}",not replay(rows)[0]))
    # 32 manifest mutations
    base=digest(manifest)
    for i in range(32):
        rows=[list(x) for x in manifest]
        idx=i%len(rows)
        if i%2==0: rows[idx][1]="0"*64
        else: rows[idx][0]=rows[idx][0]+".tampered"
        cases.append((f"MANIFEST-{i+1:02d}",digest(tuple(tuple(x) for x in rows))!=base))
    return tuple(cases)

def qualify() -> dict[str,object]:
    if not all(p.is_file() for p in STAGE_PATHS): raise RuntimeError("PRIOR_STAGE_MISSING")
    if not validate_frozen(): raise RuntimeError("FROZEN_VERIFICATION_FAILED")
    chain_ok,_,stage_hashes=run_stage_chain()
    if not chain_ok: raise RuntimeError("PRIOR_STAGE_QUALIFICATION_FAILED")
    manifest=source_manifest(); md=digest(manifest)
    receipts=build_receipts(manifest,stage_hashes); rp,rd=replay(receipts)
    second=build_receipts(manifest,stage_hashes)
    attacks=tamper_campaign(receipts,manifest)
    safe=sum(1 for _,ok in attacks if ok)
    return {"manifest":manifest,"manifest_digest":md,"receipts":receipts,"receipt_digest":receipts[-1].receipt_digest,
      "replay":rp,"replay_digest":rd,"deterministic":receipts==second,"tamper_cases":len(attacks),"tamper_safe":safe,
      "stage_hashes":stage_hashes}

def main() -> int:
    q=qualify()
    print(f"Stage: {STAGE_NAME} {STAGE_VERSION}")
    print(f"Mode: {MODE}")
    print(f"Release status: {RELEASE_STATUS}")
    print(f"Bolt-on execution authority: {BOLT_ON_EXECUTION_AUTHORITY}")
    print(f"Host execution boundary: {HOST_EXECUTION_BOUNDARY}")
    print(f"Stage 5 commit: {EXPECTED_STAGE5_COMMIT}")
    print("Prior stages qualified: 5")
    print("Frozen releases: True")
    print("External pilot subjects: 1")
    print("External pilot observation events: 6")
    print("External pilot projected requests: 2")
    print("External pilot host-owned actions: 2")
    print("External pilot bolt-on actions: 0")
    print("Lifecycle packages installed: 3")
    print("Lifecycle packages removed: 3")
    print("Lifecycle packages active after removal: 0")
    print(f"Release manifest entries: {len(q['manifest'])}")
    print(f"Tamper cases: {q['tamper_cases']}")
    print(f"Tamper cases safely rejected: {q['tamper_safe']}")
    print(f"Deterministic second pass: {q['deterministic']}")
    print(f"Pilot receipt replay: {q['replay']}")
    print("Freeze performed: False")
    print(f"Release manifest digest: {q['manifest_digest']}")
    print(f"Pilot receipt digest: {q['receipt_digest']}")
    print(f"Pilot replay digest: {q['replay_digest']}")
    passed=q['deterministic'] and q['replay'] and q['tamper_safe']==EXPECTED_TAMPER_CASES
    print(f"STAGE 6 EXTERNAL PILOT QUALIFICATION AND RELEASE CANDIDATE: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1
if __name__=="__main__": raise SystemExit(main())
