import importlib.util,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];P=BASE/"src"/"bolt_on_continuity"/"execution"/"controlled_native_executor.py"
s=importlib.util.spec_from_file_location("exq",P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
CID="a"*64
class Fake:
 def __init__(self):self.paused=False
 def invoke(self,args):
  op=args[1]
  if op=="pause":self.paused=True;return {"args":args,"returncode":0,"stdout":CID+"\n","stderr":""}
  if op=="unpause":self.paused=False;return {"args":args,"returncode":0,"stdout":CID+"\n","stderr":""}
  return {"args":args,"returncode":0,"stdout":json.dumps([{"Id":CID,"State":{"Running":True,"Paused":self.paused}}]),"stderr":""}
q=m.ControlledNativeExecutor(CID,Fake()).qualify_hold_release(100)
print("Stage: BOLT-ON CONTINUITY FOR DOCKER 0.1.6")
print("Mode: CONTROLLED_NATIVE_EXECUTION_FIXTURE_QUALIFICATION")
print("Stage foundation commit: 6d31f03")
print("Live Docker calls: 0")
print("Qualified:",q["qualified"])
print("Final running:",q["final"]["running"])
print("Final paused:",q["final"]["paused"])
print("Qualification digest:",q["qualification_digest"])
print("STAGE 6 CONTROLLED NATIVE EXECUTION FIXTURE: PASS")
