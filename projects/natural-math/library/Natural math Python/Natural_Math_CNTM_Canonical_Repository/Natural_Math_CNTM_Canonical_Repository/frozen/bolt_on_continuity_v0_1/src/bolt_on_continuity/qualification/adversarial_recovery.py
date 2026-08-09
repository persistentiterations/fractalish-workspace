from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

class Stage9Rejected(RuntimeError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message); self.reason_code = reason_code

def canonical_json(value: Any) -> bytes:
    if isinstance(value, float): raise TypeError("floating-point values are forbidden")
    if isinstance(value, dict):
        for item in value.values(): canonical_json(item)
    elif isinstance(value, (list, tuple)):
        for item in value: canonical_json(item)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()

def valid_id(value: str) -> bool:
    return isinstance(value, str) and len(value)==64 and all(c in "0123456789abcdefABCDEF" for c in value)

def load_class(path: Path, module_name: str, class_name: str):
    if not path.is_file(): raise Stage9Rejected("FOUNDATION_MISSING", str(path))
    spec=importlib.util.spec_from_file_location(module_name,path)
    if spec is None or spec.loader is None: raise Stage9Rejected("FOUNDATION_MISSING", str(path))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return getattr(module,class_name)

class FailFirstUnpauseTransport:
    def __init__(self, delegate: Any):
        self.delegate=delegate
        self.failure_injected=False
        self.injected_failure_count=0
        self.delegated_operations=[]

    def invoke(self,args:list[str])->dict[str,Any]:
        if len(args)!=3 or args[0]!="docker" or args[1] not in {"inspect","pause","unpause"} or not valid_id(args[2]):
            raise Stage9Rejected("COMMAND_OUTSIDE_ALLOWLIST","command rejected")
        if args[1]=="unpause" and not self.failure_injected:
            self.failure_injected=True
            self.injected_failure_count += 1
            return {"args":list(args),"returncode":75,"stdout":"","stderr":"stage9 injected first-release failure"}
        self.delegated_operations.append(args[1])
        return self.delegate.invoke(args)

class BoundedRecoveryQualifier:
    def __init__(self, product_root:Path, container_id:str, delegate_transport:Any):
        if not valid_id(container_id): raise ValueError("full 64-character hexadecimal container ID required")
        self.product_root=Path(product_root);self.container_id=container_id.lower()
        executor_path=self.product_root/"src"/"bolt_on_continuity"/"execution"/"controlled_native_executor.py"
        Executor=load_class(executor_path,"_stage9_executor","ControlledNativeExecutor")
        self.transport=FailFirstUnpauseTransport(delegate_transport)
        self.executor=Executor(self.container_id,self.transport)

    def qualify(self,issued_at_epoch:int)->dict[str,Any]:
        if type(issued_at_epoch) is not int or issued_at_epoch<0:
            raise Stage9Rejected("MALFORMED_TIME","time must be a nonnegative integer")
        initial=self.executor.inspect_state()
        if initial.get("running") is not True or initial.get("paused") is not False:
            raise Stage9Rejected("UNSAFE_INITIAL_STATE","container must begin running/unpaused")
        hold=self.executor.execute("HOLD",0,issued_at_epoch)
        if hold["after"].get("paused") is not True:
            raise Stage9Rejected("HOLD_NOT_VERIFIED","HOLD postcondition missing")

        first_release_rejected=False
        rejection_reason=""
        try:
            self.executor.execute("RELEASE",1,issued_at_epoch+1)
        except Exception as exc:
            first_release_rejected=True
            rejection_reason=getattr(exc,"reason_code",exc.__class__.__name__)

        if not first_release_rejected or self.transport.injected_failure_count != 1:
            raise Stage9Rejected("INJECTION_NOT_OBSERVED","first RELEASE was not rejected exactly once")

        stranded=self.executor.inspect_state()
        if stranded.get("running") is not True or stranded.get("paused") is not True:
            raise Stage9Rejected("RECOVERY_PRECONDITION_INVALID","container not safely paused after failure")

        recovery=self.executor.execute("RELEASE",999,issued_at_epoch+2)
        final=self.executor.inspect_state()
        if final.get("running") is not True or final.get("paused") is not False:
            raise Stage9Rejected("RECOVERY_FAILED","terminal state is not running/unpaused")
        if self.transport.injected_failure_count != 1:
            raise Stage9Rejected("RECOVERY_BUDGET_EXCEEDED","more than one failure was injected")

        body={
            "schema_version":"1",
            "container_id":self.container_id,
            "initial_state_digest":digest(initial),
            "hold_receipt_digest":hold["execution_receipt_digest"],
            "first_release_rejected":True,
            "first_release_rejection_reason":rejection_reason,
            "injected_failure_count":self.transport.injected_failure_count,
            "stranded_state_digest":digest(stranded),
            "recovery_receipt_digest":recovery["execution_receipt_digest"],
            "recovery_sequence":recovery["sequence"],
            "final_state":final,
            "qualified":True,
        }
        return {**body,"stage_9_recovery_qualification_digest":digest(body)}
