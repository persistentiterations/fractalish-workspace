import pytest
from bolt_on_v0_4.stage_7 import *
RID="req-"+"a"*64; CID="b"*64; INC="sha256:"+"c"*64; CFG="sha256:"+"d"*64

def request(): return create_request(RID,CID,"HOLD",INC,CFG,10,20)
def test_request_valid(): assert validate_request(request().body(),15).body()["action"]=="HOLD"
@pytest.mark.parametrize("action",["NO_ACTION","hold",""])
def test_invalid_action(action):
    with pytest.raises(ApprovalError): create_request(RID,CID,action,INC,CFG,10,20)
def test_request_digest_tamper():
    value=request().body(); value["action"]="RELEASE"
    with pytest.raises(ApprovalError): validate_request(value)
def test_expired():
    with pytest.raises(ApprovalError): validate_request(request().body(),21)
def test_gateway_transitions():
    enabled=transition_gateway(GatewayState(),"ENABLED",11); assert enabled.state=="ENABLED"; assert transition_gateway(enabled,"DISABLED",12).state=="DISABLED"
def test_repeated_gateway_rejected():
    with pytest.raises(ApprovalError): transition_gateway(GatewayState(),"DISABLED",1)
def test_approve_requires_gateway():
    with pytest.raises(ApprovalError): record_decision(request().body(),GatewayState(),"APPROVE","OPERATOR_APPROVED",12)
def test_approve_enabled():
    rec=record_decision(request().body(),GatewayState("ENABLED",11),"APPROVE","OPERATOR_APPROVED",12); assert rec.body()["native_execution_authorized"] is False; validate_decision(rec)
def test_deny_disabled(): assert record_decision(request().body(),GatewayState(),"DENY","OPERATOR_DENIED",12).body()["decision"]=="DENY"
def test_outside_window():
    with pytest.raises(ApprovalError): record_decision(request().body(),GatewayState(),"DENY","OPERATOR_DENIED",21)
def test_duplicate():
    rec=record_decision(request().body(),GatewayState(),"DENY","OPERATOR_DENIED",12)
    with pytest.raises(ApprovalError,match="DUPLICATE"): record_decision(request().body(),GatewayState(),"DENY","OPERATOR_DENIED",12,[rec])
def test_conflict():
    rec=record_decision(request().body(),GatewayState(),"DENY","OPERATOR_DENIED",12)
    with pytest.raises(ApprovalError,match="CONFLICTING"): record_decision(request().body(),GatewayState("ENABLED",11),"APPROVE","OPERATOR_APPROVED",13,[rec])
def test_decision_digest_tamper():
    rec=record_decision(request().body(),GatewayState(),"DENY","OPERATOR_DENIED",12).body(); rec["reason_code"]="OTHER"
    with pytest.raises(ApprovalError): validate_decision(rec)
def test_exact_authority(): assert {k for k,v in AUTHORITY.items() if v}=={"projected_request_construction","projected_request_validation","gateway_state_transition","operator_decision_recording","duplicate_conflict_detection"}
def test_result_digest_and_boundary():
    out=result("request",request().body()).body(); assert out["native_execution_authorized"] is False; assert out["authority"]["docker_contact"] is False
