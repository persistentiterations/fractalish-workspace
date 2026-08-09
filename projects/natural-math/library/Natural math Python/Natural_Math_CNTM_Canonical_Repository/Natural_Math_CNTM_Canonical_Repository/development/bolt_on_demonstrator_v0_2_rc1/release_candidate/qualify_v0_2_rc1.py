#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys

RC_VERSION='v0.2-RC1'
EXPECTED_TEST_COUNT=150
DEV_REL=Path('development/bolt_on_demonstrator_v0_2')
FROZEN_REL=Path('frozen')
VERIFY_REL=Path('tools/verify_all_frozen.py')
STAGES=(
 ('stage_2',Path('mediation/mediated_hold_host.py'),'PASS'),
 ('stage_3',Path('release/controlled_release_host.py'),'STAGE 3 CONTROLLED RELEASE QUALIFICATION: PASS'),
 ('stage_4',Path('lifecycle/bounded_multi_action_lifecycle.py'),'STAGE 4 BOUNDED LIFECYCLE QUALIFICATION: PASS'),
 ('stage_5',Path('adversarial/integrated_active_control_adversarial.py'),'STAGE 5 INTEGRATED ADVERSARIAL QUALIFICATION: PASS'),
)
AUTHORITY_DECISIONS=('ALLOW','DENY')
PROHIBITED=('EXECUTE','DELETE','DROP','MUTATE','REWRITE','OVERRIDE','FORCE_EXECUTE')

class QualificationError(RuntimeError): pass

def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def shat(text:str)->str: return sha(text.encode())

def files(base:Path):
 for p in sorted(base.rglob('*')):
  if not p.is_file(): continue
  if '__pycache__' in p.parts or p.suffix in {'.pyc','.pyo'}: continue
  if p.name=='RC1_QUALIFICATION.json': continue
  yield p

def manifest(base:Path)->str:
 if not base.exists(): raise QualificationError(f'Missing tree: {base}')
 rows=[f'{sha(p.read_bytes())}  {p.relative_to(base).as_posix()}' for p in files(base)]
 return shat('\n'.join(rows)+('\n' if rows else ''))

def scan_actions(base:Path):
 hits=[]
 pat=re.compile(r"[\"']([A-Z][A-Z0-9_]{2,})[\"']")
 for p in files(base):
  if p.suffix!='.py' or 'tests' in p.parts: continue
  for n,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
   for value in pat.findall(line):
    if value in PROHIBITED: hits.append(f'{p.relative_to(base)}:{n}:{value}')
 return tuple(hits)

def run(name,cmd,cwd,marker):
 cp=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 out=cp.stdout+'\n'+cp.stderr
 if cp.returncode or marker not in out:
  raise QualificationError(f'{name} failed (code {cp.returncode}); marker={marker!r}\n{out}')
 return {'name':name,'command':list(cmd),'stdout_sha256':shat(cp.stdout),'stderr_sha256':shat(cp.stderr),'marker':marker}

def stable_evidence(results):
 return tuple((r['name'],tuple(r['command']),r['marker'],r.get('count')) for r in results)

def one_pass(repo:Path):
 dev=repo/DEV_REL; results=[]
 for name,rel,marker in STAGES:
  script=dev/rel
  if not script.is_file(): raise QualificationError(f'Missing {script}')
  results.append(run(name,[sys.executable,str(script)],repo,marker))
 cp=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(dev/'tests'),'-p','test_*.py','-v'],cwd=repo,capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 out=cp.stdout+'\n'+cp.stderr
 m=re.findall(r'Ran\s+(\d+)\s+tests?',out)
 if cp.returncode or 'OK' not in out or not m or int(m[-1])!=EXPECTED_TEST_COUNT:
  raise QualificationError(f'Complete suite failed or count != {EXPECTED_TEST_COUNT}\n{out}')
 results.append({'name':'complete_v0_2_tests','command':['unittest discover'],'stdout_sha256':shat(cp.stdout),'stderr_sha256':shat(cp.stderr),'marker':'OK','count':int(m[-1])})
 results.append(run('all_frozen_verification',[sys.executable,str(repo/VERIFY_REL)],repo,'ALL FROZEN RELEASE VERIFICATIONS PASSED'))
 return results

def git_head(repo):
 cp=subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True)
 if cp.returncode: raise QualificationError('Cannot resolve git HEAD')
 return cp.stdout.strip()

def qualify(repo:Path):
 repo=repo.resolve(); dev=repo/DEV_REL; frozen=repo/FROZEN_REL
 before_dev=manifest(dev); before_frozen=manifest(frozen)
 hits=scan_actions(dev)
 if hits: raise QualificationError('Prohibited executable action literals:\n'+'\n'.join(hits))
 first=one_pass(repo)
 if manifest(dev)!=before_dev or manifest(frozen)!=before_frozen: raise QualificationError('Tree changed during first pass')
 second=one_pass(repo)
 second_evidence=stable_evidence(second)
 first_evidence=stable_evidence(first)
 exact=(first_evidence==second_evidence and manifest(dev)==before_dev and manifest(frozen)==before_frozen)
 if not exact: raise QualificationError('Second pass qualification evidence was not equivalent')
 record={'rc_version':RC_VERSION,'source_commit':git_head(repo),'expected_test_count':EXPECTED_TEST_COUNT,'observed_test_count':EXPECTED_TEST_COUNT,'development_manifest_sha256':before_dev,'frozen_manifest_sha256':before_frozen,'prohibited_action_hits':list(hits),'commands':first,'deterministic_second_pass':True,'second_pass_comparison':'stable qualification evidence; console timing excluded','approved_for_freeze_procedure':True}
 digest=shat(json.dumps(record,sort_keys=True,separators=(',',':')))
 return record,digest

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,default=Path.cwd()); ap.add_argument('--output',type=Path,default=Path('development/bolt_on_demonstrator_v0_2/RC1_QUALIFICATION.json')); a=ap.parse_args()
 try: record,digest=qualify(a.repo)
 except QualificationError as e:
  print(f'RC1 QUALIFICATION FAILED: {e}',file=sys.stderr); return 1
 out=a.output if a.output.is_absolute() else a.repo/a.output
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({'record':record,'record_sha256':digest},indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(f'RC version: {RC_VERSION}'); print(f'Source commit: {record["source_commit"]}'); print('Observed tests: 150'); print(f'Development manifest: {record["development_manifest_sha256"]}'); print('Frozen tree unchanged: True'); print('Second pass exact: True'); print(f'Qualification record digest: {digest}'); print(f'Record written: {out}'); print('V0.2 RC1 QUALIFICATION: PASS'); print('APPROVED FOR SEPARATE FREEZE PROCEDURE: YES'); return 0
if __name__=='__main__': raise SystemExit(main())
