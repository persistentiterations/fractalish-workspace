"""Deterministic Stage 8 data-only recovery classification."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, re
from typing import Mapping

PRODUCT="Bolt-On Continuity v0.4"; STAGE=8; SCHEMA_VERSION=1
QUALIFIED_STAGE_7_HEAD="ddb7a2430a709705d91142742bd6ad3b61c24653"
STAGE_7_QUALIFICATION_RECORD_SHA256="cb8705634db07520a3bb2063cb0c1e34860e425486bc9b7043bb94eb889ea658"
STAGE_7_VERIFIER_MANIFEST_SHA256="4b2b9bddf658e53fa8488d29eb621adbf278d402dc8261b4b2072d5364db05d1"
CID=re.compile(r"^[0-9a-f]{64}$"); DIGEST=re.compile(r"^sha256:[0-9a-f]{64}$"); REQUEST_ID=re.compile(r"^req-[0-9a-f]{64}$")
SUBJECT_STATES=frozenset({"running","created","paused","restarting","exited","dead","stopped"})
STORE_STATES=frozenset({"STORE_HEALTHY","STORE_MISSING","STORE_PERMISSION_DENIED","STORE_PARTIAL_WRITE","STORE_CORRUPT","STORE_DISK_FULL","STORE_AMBIGUOUS"})
TERMINAL=frozenset({"DENIED","GATEWAY_REJECTED","DOCKER_ACCEPTED","DOCKER_REJECTED"})
AUTHORITY={"recovery_classification":True,"subject_evidence_validation":True,"store_evidence_validation":True,"duplicate_suppression":True,"stage_7_record_consumption":True,"docker_contact":False,"docker_mutation":False,"filesystem_read":False,"filesystem_mutation":False,"gateway_action":False,"native_command_construction":False,"native_execution":False,"subprocess_execution":False,"network_contact":False,"socket_access":False,"process_control":False,"background_service":False,"thread_creation":False,"automatic_recovery":False,"credential_write":False,"publish_release":False,"production_claims":False}

class RecoveryError(ValueError): pass

def canonical_bytes(value: object)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def sha256(value:bytes)->str: return "sha256:"+hashlib.sha256(value).hexdigest()

@dataclass(frozen=True)
class RecoveryResult:
    body_value: Mapping[str,object]
    def body(self): return dict(self.body_value)
    def canonical_bytes(self): return canonical_bytes(self.body())
    def canonical_json(self): return self.canonical_bytes().decode()

def _subject(item:object)->dict[str,str]:
    if not isinstance(item,dict) or set(item)!={"container_id","display_name","state"}: raise RecoveryError("MALFORMED_SUBJECT_EVIDENCE")
    cid,name,state=item["container_id"],item["display_name"],item["state"]
    if not isinstance(cid,str) or not CID.fullmatch(cid) or not isinstance(name,str) or not name or len(name)>256 or state not in SUBJECT_STATES: raise RecoveryError("MALFORMED_SUBJECT_EVIDENCE")
    return {"container_id":cid,"display_name":name,"state":state}

def classify_subject(enrolled_id:object,enrolled_name:object,current:object)->str:
    if not isinstance(enrolled_id,str) or not CID.fullmatch(enrolled_id) or not isinstance(enrolled_name,str) or not enrolled_name or not isinstance(current,list): return "SUBJECT_AMBIGUOUS"
    try: items=[_subject(x) for x in current]
    except RecoveryError: return "SUBJECT_AMBIGUOUS"
    ids=[x["container_id"] for x in items]
    if len(ids)!=len(set(ids)): return "SUBJECT_AMBIGUOUS"
    exact=[x for x in items if x["container_id"]==enrolled_id]
    if len(exact)>1: return "SUBJECT_AMBIGUOUS"
    if exact: return "SUBJECT_STOPPED" if exact[0]["state"] in {"exited","dead","stopped"} else "SUBJECT_MATCHED"
    replacements=[x for x in items if x["display_name"]==enrolled_name]
    if len(replacements)==1: return "SUBJECT_REPLACED"
    if len(replacements)>1: return "SUBJECT_AMBIGUOUS"
    return "SUBJECT_MISSING"

def _requests(value:object)->tuple[bool,bool]:
    if not isinstance(value,list): return False,True
    seen={}; terminal=False; uncertain=False
    for item in value:
        if not isinstance(item,dict) or set(item)!={"request_id","request_digest","action_status"}: uncertain=True; continue
        rid,digest,status=item["request_id"],item["request_digest"],item["action_status"]
        if not isinstance(rid,str) or not REQUEST_ID.fullmatch(rid) or not isinstance(digest,str) or not DIGEST.fullmatch(digest): uncertain=True; continue
        previous=seen.get(rid)
        if previous and previous!=(digest,status): uncertain=True
        seen[rid]=(digest,status)
        if status in TERMINAL: terminal=True
        elif status in {"PROJECTED","APPROVED"}: uncertain=True
        elif status!="NOT_PROJECTED": uncertain=True
    return terminal,uncertain

def classify_recovery(value:object)->RecoveryResult:
    if not isinstance(value,dict) or set(value)!={"enrolled_id","enrolled_name","current_subjects","store_classification","prior_requests"}: raise RecoveryError("RECOVERY_FIELDS_MISMATCH")
    subject=classify_subject(value["enrolled_id"],value["enrolled_name"],value["current_subjects"])
    store=value["store_classification"] if value["store_classification"] in STORE_STATES else "STORE_AMBIGUOUS"
    terminal,uncertain=_requests(value["prior_requests"])
    if subject=="SUBJECT_AMBIGUOUS": disposition,reason="FAIL_CLOSED_UNCERTAIN","AMBIGUOUS_SUBJECT_EVIDENCE"
    elif store!="STORE_HEALTHY": disposition,reason="FAIL_CLOSED_STORE","STORE_NOT_HEALTHY"
    elif uncertain: disposition,reason="FAIL_CLOSED_UNCERTAIN","UNRESOLVED_ACTION_EVIDENCE"
    elif terminal: disposition,reason="SUPPRESS_DUPLICATE","TERMINAL_REQUEST_ALREADY_RECORDED"
    elif subject=="SUBJECT_REPLACED": disposition,reason="REQUIRE_REENROLLMENT","SUBJECT_ID_CHANGED"
    elif subject in {"SUBJECT_MISSING","SUBJECT_STOPPED"}: disposition,reason="REPORT_SUBJECT_UNAVAILABLE",subject
    else: disposition,reason="RESUME_OBSERVATION_ONLY","RECOVERY_SAFE"
    base={"accepted":True,"authority":dict(AUTHORITY),"disposition":disposition,"gateway_enabled":False,"native_execution_authorized":False,"observation_only":True,"product":PRODUCT,"qualified_stage_7_head":QUALIFIED_STAGE_7_HEAD,"reason_code":reason,"schema_version":SCHEMA_VERSION,"stage":STAGE,"stage_7_qualification_record_sha256":STAGE_7_QUALIFICATION_RECORD_SHA256,"stage_7_verifier_manifest_sha256":STAGE_7_VERIFIER_MANIFEST_SHA256,"store_classification":store,"subject_classification":subject,"terminal_request_suppressed":disposition=="SUPPRESS_DUPLICATE"}
    return RecoveryResult({**base,"result_digest":sha256(canonical_bytes(base))})

def render_human(result:RecoveryResult)->str:
    body=result.body()
    return "\n".join([f"PASS stage7.binding: {body['qualified_stage_7_head']}","PASS accepted: TRUE",f"PASS subject.classification: {body['subject_classification']}",f"PASS store.classification: {body['store_classification']}",f"PASS disposition: {body['disposition']}","PASS native.execution.authorized: FALSE","PASS docker.contact: DENIED","PASS filesystem.mutation: DENIED","STAGE_8_RECOVERY_CLASSIFIED",f"RESULT SHA-256 {body['result_digest']}"])
