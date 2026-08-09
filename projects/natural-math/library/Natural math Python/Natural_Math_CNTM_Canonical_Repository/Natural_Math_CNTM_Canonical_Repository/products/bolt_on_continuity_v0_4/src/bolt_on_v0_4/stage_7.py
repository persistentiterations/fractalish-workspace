"""Deterministic Stage 7 operator approval and gateway-state boundary."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, re
from typing import Mapping, Sequence

PRODUCT="Bolt-On Continuity v0.4"; STAGE=7; SCHEMA_VERSION=1
QUALIFIED_STAGE_6_HEAD="01dbfdc0ba8da3203be6ffcb759ef74edbd7d255"
STAGE_6_QUALIFICATION_RECORD_SHA256="cd45ee04b1f872f6a98cbc2c52995ebdfcf4eb64feb9a1a6bb912072ef78af7d"
STAGE_6_VERIFIER_MANIFEST_SHA256="6a6df9fcae5fbcd8ea3987c8bdeed5ae959cef631820de3d4fdc0b2a653dd6bc"
REQUEST_ID=re.compile(r"^req-[0-9a-f]{64}$"); CONTAINER_ID=re.compile(r"^[0-9a-f]{64}$")
SHA256_PREFIXED=re.compile(r"^sha256:[0-9a-f]{64}$"); REASON_CODE=re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
ACTIONS=frozenset({"HOLD","RELEASE"}); DECISIONS=frozenset({"APPROVE","DENY"}); GATEWAY_STATES=frozenset({"DISABLED","ENABLED"})
AUTHORITY={
"projected_request_construction":True,"projected_request_validation":True,"gateway_state_transition":True,"operator_decision_recording":True,"duplicate_conflict_detection":True,
"docker_contact":False,"docker_mutation":False,"native_command_construction":False,"native_execution":False,"container_start_stop_restart":False,"container_exec":False,
"filesystem_read":False,"filesystem_mutation":False,"subprocess_execution":False,"socket_access":False,"network_contact":False,"credential_write":False,
"autonomous_approval":False,"background_service":False,"thread_creation":False,"automatic_recovery":False,"attach_or_distribute_packages":False,"publish_release":False,"production_claims":False}

class ApprovalError(ValueError): pass

def canonical_bytes(value:object)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
def sha256_prefixed(value:bytes)->str: return "sha256:"+hashlib.sha256(value).hexdigest()

@dataclass(frozen=True)
class ProjectedRequest:
    body_value:Mapping[str,object]
    def body(self): return dict(self.body_value)
    def canonical_bytes(self): return canonical_bytes(self.body())
@dataclass(frozen=True)
class GatewayState:
    state:str="DISABLED"; sequence:int=0
    def body(self): return {"schema_version":1,"state":self.state,"sequence":self.sequence}
@dataclass(frozen=True)
class DecisionRecord:
    body_value:Mapping[str,object]
    def body(self): return dict(self.body_value)
    def canonical_bytes(self): return canonical_bytes(self.body())
@dataclass(frozen=True)
class StageSevenResult:
    body_value:Mapping[str,object]
    def body(self): return dict(self.body_value)
    def canonical_bytes(self): return canonical_bytes(self.body())
    def canonical_json(self): return self.canonical_bytes().decode("utf-8")

def _nonnegative(value:object,code:str)->int:
    if type(value) is not int or value<0: raise ApprovalError(code)
    return value

def create_request(request_id:str,container_id:str,action:str,incident_digest:str,configuration_digest:str,issued_sequence:int,expiry_sequence:int)->ProjectedRequest:
    base={"action":action,"configuration_digest":configuration_digest,"container_id":container_id,"expiry_sequence":expiry_sequence,"incident_digest":incident_digest,"issued_sequence":issued_sequence,"request_id":request_id,"schema_version":1}
    out=ProjectedRequest({**base,"request_digest":sha256_prefixed(canonical_bytes(base))}); validate_request(out.body()); return out

def validate_request(value:object,current_sequence:int|None=None)->ProjectedRequest:
    if not isinstance(value,dict): raise ApprovalError("MALFORMED_REQUEST")
    required={"schema_version","request_id","container_id","action","incident_digest","configuration_digest","issued_sequence","expiry_sequence","request_digest"}
    if set(value)!=required: raise ApprovalError("REQUEST_FIELDS_MISMATCH")
    if value["schema_version"]!=1: raise ApprovalError("UNSUPPORTED_REQUEST_VERSION")
    if not isinstance(value["request_id"],str) or not REQUEST_ID.fullmatch(value["request_id"]): raise ApprovalError("INVALID_REQUEST_ID")
    if not isinstance(value["container_id"],str) or not CONTAINER_ID.fullmatch(value["container_id"]): raise ApprovalError("INVALID_CONTAINER_ID")
    if value["action"] not in ACTIONS: raise ApprovalError("INVALID_ACTION")
    for key in ("incident_digest","configuration_digest","request_digest"):
        if not isinstance(value[key],str) or not SHA256_PREFIXED.fullmatch(value[key]): raise ApprovalError("INVALID_DIGEST")
    issued=_nonnegative(value["issued_sequence"],"INVALID_ISSUED_SEQUENCE"); expiry=_nonnegative(value["expiry_sequence"],"INVALID_EXPIRY_SEQUENCE")
    if expiry<=issued: raise ApprovalError("INVALID_SEQUENCE_WINDOW")
    if current_sequence is not None and _nonnegative(current_sequence,"INVALID_CURRENT_SEQUENCE")>expiry: raise ApprovalError("REQUEST_EXPIRED")
    base=dict(value); digest=base.pop("request_digest")
    if digest!=sha256_prefixed(canonical_bytes(base)): raise ApprovalError("REQUEST_DIGEST_MISMATCH")
    return ProjectedRequest(dict(value))

def transition_gateway(current:GatewayState,target:str,sequence:int)->GatewayState:
    if current.state not in GATEWAY_STATES or target not in GATEWAY_STATES: raise ApprovalError("INVALID_GATEWAY_STATE")
    seq=_nonnegative(sequence,"INVALID_GATEWAY_SEQUENCE")
    if seq<=current.sequence: raise ApprovalError("INVALID_GATEWAY_SEQUENCE")
    if target==current.state: raise ApprovalError("NO_GATEWAY_TRANSITION")
    return GatewayState(target,seq)

def validate_decision(value:object)->DecisionRecord:
    if isinstance(value,DecisionRecord): value=value.body()
    if not isinstance(value,dict): raise ApprovalError("MALFORMED_DECISION")
    required={"schema_version","request_id","request_digest","decision","reason_code","decision_sequence","native_execution_authorized","decision_digest"}
    if set(value)!=required: raise ApprovalError("DECISION_FIELDS_MISMATCH")
    if value["schema_version"]!=1 or value["native_execution_authorized"] is not False: raise ApprovalError("UNSAFE_DECISION_RECORD")
    if not isinstance(value["request_id"],str) or not REQUEST_ID.fullmatch(value["request_id"]): raise ApprovalError("INVALID_REQUEST_ID")
    if not isinstance(value["request_digest"],str) or not SHA256_PREFIXED.fullmatch(value["request_digest"]): raise ApprovalError("INVALID_DIGEST")
    if value["decision"] not in DECISIONS: raise ApprovalError("INVALID_DECISION")
    if not isinstance(value["reason_code"],str) or not REASON_CODE.fullmatch(value["reason_code"]): raise ApprovalError("INVALID_REASON_CODE")
    _nonnegative(value["decision_sequence"],"INVALID_DECISION_SEQUENCE")
    if not isinstance(value["decision_digest"],str) or not SHA256_PREFIXED.fullmatch(value["decision_digest"]): raise ApprovalError("INVALID_DIGEST")
    base=dict(value); digest=base.pop("decision_digest")
    if digest!=sha256_prefixed(canonical_bytes(base)): raise ApprovalError("DECISION_DIGEST_MISMATCH")
    return DecisionRecord(dict(value))

def record_decision(request_value:object,gateway:GatewayState,decision:str,reason_code:str,decision_sequence:int,prior:Sequence[object]=())->DecisionRecord:
    request=validate_request(request_value,decision_sequence).body()
    if decision not in DECISIONS: raise ApprovalError("INVALID_DECISION")
    if not isinstance(reason_code,str) or not REASON_CODE.fullmatch(reason_code): raise ApprovalError("INVALID_REASON_CODE")
    seq=_nonnegative(decision_sequence,"INVALID_DECISION_SEQUENCE")
    if not request["issued_sequence"]<=seq<=request["expiry_sequence"]: raise ApprovalError("DECISION_OUTSIDE_WINDOW")
    if decision=="APPROVE" and (gateway.state!="ENABLED" or gateway.sequence>seq): raise ApprovalError("GATEWAY_NOT_ENABLED")
    for item in [validate_decision(x).body() for x in prior]:
        if item["request_id"]!=request["request_id"]: continue
        if item["request_digest"]!=request["request_digest"]: raise ApprovalError("REQUEST_IDENTIFIER_REUSE")
        same=item["decision"]==decision and item["reason_code"]==reason_code and item["decision_sequence"]==seq
        raise ApprovalError("DUPLICATE_DECISION" if same else "CONFLICTING_DECISION")
    base={"decision":decision,"decision_sequence":seq,"native_execution_authorized":False,"reason_code":reason_code,"request_digest":request["request_digest"],"request_id":request["request_id"],"schema_version":1}
    return DecisionRecord({**base,"decision_digest":sha256_prefixed(canonical_bytes(base))})

def result(operation:str,payload:object)->StageSevenResult:
    body={"accepted":True,"authority":dict(AUTHORITY),"native_execution_authorized":False,"operation":operation,"payload":payload,"product":PRODUCT,"qualified_stage_6_head":QUALIFIED_STAGE_6_HEAD,"reason_code":"STAGE_7_DATA_READY","schema_version":SCHEMA_VERSION,"stage":STAGE,"stage_6_qualification_record_sha256":STAGE_6_QUALIFICATION_RECORD_SHA256,"stage_6_verifier_manifest_sha256":STAGE_6_VERIFIER_MANIFEST_SHA256}
    return StageSevenResult({**body,"result_digest":sha256_prefixed(canonical_bytes(body))})

def render_human(value:StageSevenResult)->str:
    body=value.body(); return "\n".join([f"PASS stage6.binding: {body['qualified_stage_6_head']}",f"PASS operation: {body['operation']}","PASS accepted: TRUE","PASS native.execution.authorized: FALSE","PASS docker.contact: DENIED","PASS filesystem.mutation: DENIED",body["reason_code"],f"RESULT SHA-256 {body['result_digest']}"])
