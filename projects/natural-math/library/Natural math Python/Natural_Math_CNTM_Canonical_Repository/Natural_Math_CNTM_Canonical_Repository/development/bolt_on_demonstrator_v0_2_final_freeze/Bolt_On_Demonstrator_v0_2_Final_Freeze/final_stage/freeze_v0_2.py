#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess, sys

DEV=Path("development/bolt_on_demonstrator_v0_2")
RC=DEV/"RC1_QUALIFICATION.json"
TARGET=Path("frozen/bolt_on/v0.2")
VERIFY=Path("tools/verify_bolt_on_v0_2.py")
VERIFY_ALL=Path("tools/verify_all_frozen.py")
COUNT=150
STAGES=(
 ("stage_2",Path("mediation/mediated_hold_host.py"),"PASS"),
 ("stage_3",Path("release/controlled_release_host.py"),"STAGE 3 CONTROLLED RELEASE QUALIFICATION: PASS"),
 ("stage_4",Path("lifecycle/bounded_multi_action_lifecycle.py"),"STAGE 4 BOUNDED LIFECYCLE QUALIFICATION: PASS"),
 ("stage_5",Path("adversarial/integrated_active_control_adversarial.py"),"STAGE 5 INTEGRATED ADVERSARIAL QUALIFICATION: PASS"),
)
class FreezeError(RuntimeError): pass
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(v): return sha(json.dumps(v,sort_keys=True,separators=(",",":")).encode())
def files(root, exclude_rc=False):
 for p in sorted(root.rglob("*")):
  if not p.is_file() or "__pycache__" in p.parts or p.suffix in {".pyc",".pyo"}: continue
  if p.name=="RELEASE_MANIFEST_SHA256.txt": continue
  if exclude_rc and p.name=="RC1_QUALIFICATION.json": continue
  yield p
def tree(root, exclude_rc=False):
 if not root.is_dir(): raise FreezeError(f"Missing tree: {root}")
 rows=[f"{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}" for p in files(root,exclude_rc)]
 return sha(("\n".join(rows)+("\n" if rows else "")).encode())
def run(cmd,cwd,marker):
 cp=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding="utf-8",errors="replace",
                   env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
 out=cp.stdout+"\n"+cp.stderr
 if cp.returncode or marker not in out: raise FreezeError(f"Command failed; marker={marker!r}\n{out}")
 return {"command":cmd,"marker":marker,"stdout_sha256":sha(cp.stdout.encode()),"stderr_sha256":sha(cp.stderr.encode())}
def head(repo):
 cp=subprocess.run(["git","rev-parse","HEAD"],cwd=repo,capture_output=True,text=True)
 if cp.returncode: raise FreezeError("Cannot resolve Git HEAD")
 return cp.stdout.strip()
def verifier():
 return """#!/usr/bin/env python3
from pathlib import Path
import hashlib
def h(p):
 d=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): d.update(b)
 return d.hexdigest()
def main():
 root=Path(__file__).resolve().parents[1]/"frozen"/"bolt_on"/"v0.2"
 man=root/"RELEASE_MANIFEST_SHA256.txt"
 if not root.is_dir() or not man.is_file(): print("MISSING v0.2 frozen release"); return 1
 expected={}
 for n,line in enumerate(man.read_text(encoding="utf-8").splitlines(),1):
  if not line.strip(): continue
  parts=line.split("  ",1)
  if len(parts)!=2 or len(parts[0])!=64 or parts[1] in expected:
   print(f"INVALID MANIFEST LINE {n}: {line}"); return 1
  expected[parts[1]]=parts[0].lower()
 actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p!=man}
 failed=False
 for rel in sorted(set(expected)-actual): print("MISSING ",rel); failed=True
 for rel in sorted(actual-set(expected)): print("EXTRA   ",rel); failed=True
 for rel in sorted(set(expected)&actual):
  if h(root/rel)!=expected[rel]: print("CHANGED ",rel); failed=True
 if failed: print("BOLT-ON v0.2 FROZEN VERIFICATION FAILED"); return 1
 print(f"BOLT-ON v0.2 FROZEN VERIFICATION PASSED: {len(expected)} files"); return 0
if __name__=="__main__": raise SystemExit(main())
"""
def qualify(repo):
 results=[]
 for name,rel,marker in STAGES:
  results.append({"name":name,**run([sys.executable,str(repo/DEV/rel)],repo,marker)})
 cp=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(repo/DEV/"tests"),"-p","test_*.py","-v"],
  cwd=repo,capture_output=True,text=True,encoding="utf-8",errors="replace",env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
 out=cp.stdout+"\n"+cp.stderr; m=re.findall(r"Ran\s+(\d+)\s+tests?",out)
 if cp.returncode or "OK" not in out or not m or int(m[-1])!=COUNT:
  raise FreezeError(f"Complete suite failed or count != {COUNT}\n{out}")
 results.append({"name":"complete_v0_2_tests","count":COUNT,"marker":"OK"})
 return results
def freeze(repo):
 repo=repo.resolve(); dev=repo/DEV; target=repo/TARGET; vp=repo/VERIFY; vap=repo/VERIFY_ALL
 if target.exists() or vp.exists(): raise FreezeError("v0.2 freeze target or verifier already exists")
 env=json.loads((repo/RC).read_text(encoding="utf-8")); rec=env["record"]; rd=env["record_sha256"]
 if canon(rec)!=rd: raise FreezeError("RC1 approval-record digest mismatch")
 for k,v in {"rc_version":"v0.2-RC1","expected_test_count":COUNT,"observed_test_count":COUNT,
             "deterministic_second_pass":True,"approved_for_freeze_procedure":True}.items():
  if rec.get(k)!=v: raise FreezeError(f"RC1 requirement failed: {k}")
 dev_before=tree(dev,True)
 if dev_before!=rec.get("development_manifest_sha256"): raise FreezeError("Development tree differs from RC1")
 frozen_before=tree(repo/"frozen")
 aggregate=vap.read_text(encoding="utf-8")
 run([sys.executable,str(vap)],repo,"ALL FROZEN RELEASE VERIFICATIONS PASSED")
 results=qualify(repo)
 if tree(dev,True)!=dev_before or tree(repo/"frozen")!=frozen_before: raise FreezeError("Tree changed during qualification")
 try:
  target.mkdir(parents=True)
  for s in files(dev):
   d=target/s.relative_to(dev); d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(s,d)
  receipt={"release":"v0.2","status":"FROZEN","freeze_source_commit":head(repo),
   "rc_source_commit":rec["source_commit"],"rc_record_sha256":rd,
   "development_manifest_sha256":dev_before,"observed_tests":COUNT,
   "prior_frozen_tree_sha256":frozen_before,"host_actions":["HOLD","RELEASE"],
   "authority_decisions":["ALLOW","DENY"],"qualification":results}
  (target/"FREEZE_RECEIPT.json").write_text(json.dumps({"record":receipt,"record_sha256":canon(receipt)},indent=2,sort_keys=True)+"\n")
  rows=[f"{sha(p.read_bytes())}  {p.relative_to(target).as_posix()}" for p in files(target)]
  (target/"RELEASE_MANIFEST_SHA256.txt").write_text("\n".join(rows)+"\n")
  vp.write_text(verifier(),encoding="utf-8",newline="\n")
  anchor='        tools / "verify_bolt_on_v0_1.py",'
  entry='        tools / "verify_bolt_on_v0_2.py",'
  if anchor not in aggregate: raise FreezeError("Cannot safely extend aggregate verifier")
  vap.write_text(aggregate.replace(anchor,anchor+"\n"+entry,1),encoding="utf-8",newline="\n")
  run([sys.executable,str(vp)],repo,"BOLT-ON v0.2 FROZEN VERIFICATION PASSED")
  run([sys.executable,str(vap)],repo,"ALL FROZEN RELEASE VERIFICATIONS PASSED")
  if tree(dev,True)!=dev_before: raise FreezeError("Development tree changed during freeze")
  return receipt,sha((target/"RELEASE_MANIFEST_SHA256.txt").read_bytes())
 except Exception:
  if target.exists(): shutil.rmtree(target)
  if vp.exists(): vp.unlink()
  vap.write_text(aggregate,encoding="utf-8",newline="\n")
  raise
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--repo",type=Path,default=Path.cwd()); a=ap.parse_args()
 try: r,m=freeze(a.repo)
 except Exception as e: print(f"V0.2 FINAL FREEZE FAILED: {e}",file=sys.stderr); return 1
 print("Release: v0.2"); print(f'Source commit: {r["freeze_source_commit"]}')
 print("Observed tests: 150"); print(f'Development manifest: {r["development_manifest_sha256"]}')
 print(f'RC qualification record: {r["rc_record_sha256"]}'); print(f"Release manifest: {m}")
 print("Prior frozen releases unchanged: True"); print("Development tree unchanged: True")
 print("ALL FROZEN RELEASE VERIFICATIONS PASSED")
 print("BOLT-ON DEMONSTRATOR v0.2 FINAL FREEZE: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
