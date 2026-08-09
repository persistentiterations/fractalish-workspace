import pytest
from bolt_on_v0_4.stage_8 import AUTHORITY,RecoveryError,canonical_bytes,classify_recovery,sha256
CID="a"*64

def base(): return {"enrolled_id":CID,"enrolled_name":"subject","current_subjects":[{"container_id":CID,"display_name":"subject","state":"running"}],"store_classification":"STORE_HEALTHY","prior_requests":[]}

def test_resume(): assert classify_recovery(base()).body()["disposition"]=="RESUME_OBSERVATION_ONLY"
@pytest.mark.parametrize("state",["exited","dead","stopped"])
def test_stopped(state):
    value=base(); value["current_subjects"][0]["state"]=state
    assert classify_recovery(value).body()["disposition"]=="REPORT_SUBJECT_UNAVAILABLE"
def test_missing():
    value=base(); value["current_subjects"]=[]
    assert classify_recovery(value).body()["subject_classification"]=="SUBJECT_MISSING"
def test_replaced():
    value=base(); value["current_subjects"]=[{"container_id":"b"*64,"display_name":"subject","state":"running"}]
    assert classify_recovery(value).body()["disposition"]=="REQUIRE_REENROLLMENT"
def test_duplicate_ids_ambiguous():
    value=base(); value["current_subjects"]*=2
    assert classify_recovery(value).body()["disposition"]=="FAIL_CLOSED_UNCERTAIN"
@pytest.mark.parametrize("store",["STORE_MISSING","STORE_PERMISSION_DENIED","STORE_PARTIAL_WRITE","STORE_CORRUPT","STORE_DISK_FULL","STORE_AMBIGUOUS","bad"])
def test_store_fail_closed(store):
    value=base(); value["store_classification"]=store
    assert classify_recovery(value).body()["disposition"]=="FAIL_CLOSED_STORE"
def test_terminal_suppressed():
    value=base(); value["prior_requests"]=[{"request_id":"req-"+"c"*64,"request_digest":"sha256:"+"d"*64,"action_status":"DENIED"}]
    assert classify_recovery(value).body()["disposition"]=="SUPPRESS_DUPLICATE"
@pytest.mark.parametrize("status",["PROJECTED","APPROVED","UNKNOWN"])
def test_uncertain(status):
    value=base(); value["prior_requests"]=[{"request_id":"req-"+"c"*64,"request_digest":"sha256:"+"d"*64,"action_status":status}]
    assert classify_recovery(value).body()["disposition"]=="FAIL_CLOSED_UNCERTAIN"
def test_conflicting_reuse():
    value=base(); rid="req-"+"c"*64
    value["prior_requests"]=[{"request_id":rid,"request_digest":"sha256:"+"d"*64,"action_status":"DENIED"},{"request_id":rid,"request_digest":"sha256:"+"e"*64,"action_status":"DENIED"}]
    assert classify_recovery(value).body()["disposition"]=="FAIL_CLOSED_UNCERTAIN"
def test_fields_exact():
    value=base(); value["extra"]=1
    with pytest.raises(RecoveryError): classify_recovery(value)
def test_authority():
    assert {key for key,value in AUTHORITY.items() if value}=={"recovery_classification","subject_evidence_validation","store_evidence_validation","duplicate_suppression","stage_7_record_consumption"}
def test_result_digest():
    body=classify_recovery(base()).body(); digest=body.pop("result_digest")
    assert digest==sha256(canonical_bytes(body))
def test_safety():
    body=classify_recovery(base()).body()
    assert body["native_execution_authorized"] is False and body["gateway_enabled"] is False and body["observation_only"] is True
