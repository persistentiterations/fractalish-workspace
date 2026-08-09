import os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
def run(pattern):
 env=dict(os.environ); env['PYTHONPATH']=str(ROOT/'src'); return subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p',pattern],env=env).returncode
if __name__=='__main__':
 if run('test_stage_4.py'): raise SystemExit(1)
 if not os.environ.get('CONTROL_ROOM_STAGE4_EVIDENCE'): raise SystemExit('Stage 4 evidence required')
 if run('test_stage_4_docker_integration.py'): raise SystemExit(1)
 if subprocess.run([sys.executable,str(REPO/'tools/verify_frozen.py')],cwd=REPO).returncode: raise SystemExit(1)
 print('CONTROL ROOM v0.1 STAGE 4 VERIFICATION PASSED')
