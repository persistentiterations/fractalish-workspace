from __future__ import annotations
import hashlib, json, subprocess
from typing import Any, Protocol

ZERO_DIGEST="sha256:"+"0"*64

class ExecutionRejected(RuntimeError):
    def __init__(self, reason_code:str,message:str):
        super().__init__(message);self.reason_code=reason_code

def canonical_json(v:Any)->bytes:
    if isinstance(v,float): raise TypeError("floats forbidden")
    if isinstance(v,dict):
        for x in v.values(): canonical_json(x)
    elif isinstance(v,(list,tuple)):
        for x in v: canonical_json(x)
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def digest(v:Any)->str:
    return "sha256:"+hashlib.sha256(canonical_json(v)).hexdigest()

def valid_id(v:str)->bool:
    return isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdefABCDEF" for c in v)

class Transport(Protocol):
    def invoke(self,args:list[str])->dict[str,Any]: ...

class DockerSubprocessTransport:
    ALLOWED={("docker","inspect"),("docker","pause"),("docker","unpause")}
    def invoke(self,args:list[str])->dict[str,Any]:
        if len(args)!=3 or tuple(args[:2]) not in self.ALLOWED or not valid_id(args[2]):
            raise ExecutionRejected("COMMAND_OUTSIDE_ALLOWLIST","command rejected")
        cp=subprocess.run(args,capture_output=True,text=True,shell=False,timeout=20,check=False)
        return {"args":args,"returncode":cp.returncode,"stdout":cp.stdout,"stderr":cp.stderr}

class ControlledNativeExecutor:
    def __init__(self,container_id:str,transport:Transport):
        if not valid_id(container_id): raise ValueError("full 64-character container ID required")
        self.container_id=container_id.lower();self.transport=transport;self.previous_receipt_digest=ZERO_DIGEST

    def _invoke(self,op:str)->dict[str,Any]:
        return self.transport.invoke(["docker",op,self.container_id])

    def inspect_state(self)->dict[str,Any]:
        result=self._invoke("inspect")
        if result["returncode"]!=0: raise ExecutionRejected("INSPECT_FAILED",result["stderr"])
        try:
            parsed=json.loads(result["stdout"])
            if not isinstance(parsed,list) or len(parsed)!=1: raise ValueError
            item=parsed[0]
            if item.get("Id","").lower()!=self.container_id: raise ExecutionRejected("SUBJECT_MISMATCH","inspect subject differs")
            state=item["State"]
            running=state["Running"];paused=state["Paused"]
            if type(running) is not bool or type(paused) is not bool: raise ValueError
        except ExecutionRejected: raise
        except Exception as exc: raise ExecutionRejected("MALFORMED_INSPECT","inspect malformed") from exc
        return {"container_id":self.container_id,"running":running,"paused":paused,
                "inspect_digest":digest(parsed),"raw_digest":"sha256:"+hashlib.sha256(result["stdout"].encode()).hexdigest()}

    def execute(self,action:str,sequence:int,issued_at_epoch:int)->dict[str,Any]:
        if action not in {"HOLD","RELEASE"}: raise ExecutionRejected("UNSUPPORTED_ACTION","action rejected")
        if type(sequence) is not int or sequence<0 or type(issued_at_epoch) is not int or issued_at_epoch<0:
            raise ExecutionRejected("MALFORMED_REQUEST","sequence/time invalid")
        before=self.inspect_state()
        expected_before={"HOLD":(True,False),"RELEASE":(True,True)}[action]
        if (before["running"],before["paused"])!=expected_before:
            raise ExecutionRejected("PRECONDITION_FAILED","container state does not match action")
        op="pause" if action=="HOLD" else "unpause"
        result=self._invoke(op)
        if result["returncode"]!=0: raise ExecutionRejected("NATIVE_OPERATION_FAILED",result["stderr"])
        after=self.inspect_state()
        expected_after={"HOLD":(True,True),"RELEASE":(True,False)}[action]
        if (after["running"],after["paused"])!=expected_after:
            raise ExecutionRejected("POSTCONDITION_FAILED","native state not verified")
        body={"schema_version":"1","container_id":self.container_id,"action":action,
              "native_operation":op,"argument_vector":["docker",op,self.container_id],
              "sequence":sequence,"issued_at_epoch":issued_at_epoch,"before":before,"after":after,
              "returncode":result["returncode"],
              "stdout_digest":"sha256:"+hashlib.sha256(result["stdout"].encode()).hexdigest(),
              "stderr_digest":"sha256:"+hashlib.sha256(result["stderr"].encode()).hexdigest(),
              "previous_receipt_digest":self.previous_receipt_digest}
        receipt={**body,"execution_receipt_digest":digest(body)}
        self.previous_receipt_digest=receipt["execution_receipt_digest"]
        return receipt

    def qualify_hold_release(self,issued_at_epoch:int)->dict[str,Any]:
        initial=self.inspect_state()
        if not initial["running"] or initial["paused"]:
            raise ExecutionRejected("UNSAFE_INITIAL_STATE","container must begin running and unpaused")
        hold=None;release=None;recovery_attempted=False
        try:
            hold=self.execute("HOLD",0,issued_at_epoch)
            release=self.execute("RELEASE",1,issued_at_epoch+1)
        except Exception:
            try:
                state=self.inspect_state()
                if state["running"] and state["paused"]:
                    recovery_attempted=True
                    self.execute("RELEASE",999,issued_at_epoch+2)
            finally:
                raise
        final=self.inspect_state()
        if not final["running"] or final["paused"]:
            raise ExecutionRejected("RECOVERY_FAILED","final state is not running/unpaused")
        body={"schema_version":"1","container_id":self.container_id,"initial":initial,
              "hold_receipt_digest":hold["execution_receipt_digest"],
              "release_receipt_digest":release["execution_receipt_digest"],
              "final":final,"recovery_attempted":recovery_attempted,
              "qualified":True}
        return {**body,"qualification_digest":digest(body)}
