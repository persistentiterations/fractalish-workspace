import argparse,importlib.util,json,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];P=BASE/"src"/"bolt_on_continuity"/"execution"/"controlled_native_executor.py"
s=importlib.util.spec_from_file_location("exlive",P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
ap=argparse.ArgumentParser()
ap.add_argument("--container-id",required=True)
ap.add_argument("--acknowledge-disposable-container",action="store_true")
args=ap.parse_args()
if not args.acknowledge_disposable_container:
 raise SystemExit("REFUSED: explicit disposable-container acknowledgment required")
e=m.ControlledNativeExecutor(args.container_id,m.DockerSubprocessTransport())
q=e.qualify_hold_release(int(time.time()))
print(json.dumps(q,sort_keys=True,separators=(",",":")))
print("STAGE 6 CONTROLLED NATIVE EXECUTION LIVE: PASS")
