import json
from dataclasses import replace
import pytest
from bolt_on_v0_4.stage_3 import AUTHORITY as STAGE_3_AUTHORITY, EnrollmentRecord, canonical_bytes, sha256
from bolt_on_v0_4.stage_4 import (
    ACTION_VOCABULARY, AUTHORITY, CanonicalConfiguration, ConfigurationError,
    ConfigurationOptions, QUALIFIED_STAGE_3_HEAD, STAGE_3_QUALIFICATION_RECORD_SHA256,
    STAGE_3_VERIFIER_MANIFEST_SHA256, build_configuration, enrollment_from_mapping,
    validate_configuration, validate_enrollment,
)

def enrollment(cid="a"*64):
    base={"authority":dict(STAGE_3_AUTHORITY),"container_id":cid,"display_name":"bolt-on-v0-4-fixture","image":"alpine:3.20","observed_state":"created","platform":"linux","product":"Bolt-On Continuity v0.4","qualified_stage_2_head":"15e29c94d81e5e5eae3ddf384eb8fa6af8ffcdc4","schema_version":1,"stage":3,"stage_2_qualification_record_sha256":"97b92c58c6bf342c44dd793bfe0a78401b9c606ecaccd27ca1f9c48cd2d6141e","stage_2_verifier_manifest_sha256":"6f1c6c119c8114ed20e84c6d28dc1e9de9000e6df861939e5775373e4d957192","status":"STAGE_3_ENROLLED"}
    return EnrollmentRecord(**base,record_digest=sha256(canonical_bytes(base)))

def test_valid_enrollment(): validate_enrollment(enrollment())
def test_mapping_round_trip(): assert enrollment_from_mapping(enrollment().body()) == enrollment()
def test_mapping_requires_dict():
    with pytest.raises(ConfigurationError): enrollment_from_mapping([])
def test_mapping_rejects_extra_field():
    value=enrollment().body(); value["extra"]=1
    with pytest.raises(ConfigurationError): enrollment_from_mapping(value)
def test_mapping_rejects_nonboolean_authority():
    value=enrollment().body(); value["authority"]["docker_mutation"]="false"
    with pytest.raises(ConfigurationError): enrollment_from_mapping(value)
def test_invalid_contract():
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),stage=2))
def test_invalid_status():
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),status="READY"))
def test_invalid_id():
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),container_id="abc"))
def test_invalid_metadata():
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),display_name=""))
def test_invalid_platform():
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),platform="windows"))
def test_invalid_authority():
    bad=dict(STAGE_3_AUTHORITY); bad["docker_mutation"]=True
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),authority=bad))
def test_invalid_digest_format():
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),record_digest="x"))
def test_digest_mismatch():
    with pytest.raises(ConfigurationError): validate_enrollment(replace(enrollment(),display_name="changed"))
def test_default_configuration():
    result=build_configuration(enrollment()); assert isinstance(result,CanonicalConfiguration); assert result.body()["stage"]==4
def test_configuration_is_deterministic(): assert build_configuration(enrollment()).canonical_bytes()==build_configuration(enrollment()).canonical_bytes()
def test_trailing_newline(): assert build_configuration(enrollment()).canonical_bytes().endswith(b"\n")
def test_stage3_bindings():
    body=build_configuration(enrollment()).body(); assert body["qualified_stage_3_head"]==QUALIFIED_STAGE_3_HEAD; assert body["stage_3_qualification_record_sha256"]==STAGE_3_QUALIFICATION_RECORD_SHA256; assert body["stage_3_verifier_manifest_sha256"]==STAGE_3_VERIFIER_MANIFEST_SHA256
def test_authority_exact(): assert build_configuration(enrollment()).body()["authority"]==AUTHORITY
def test_action_vocabulary_exact(): assert build_configuration(enrollment()).body()["action_vocabulary"]==list(ACTION_VOCABULARY)
def test_unsafe_path_parent():
    with pytest.raises(ConfigurationError): build_configuration(enrollment(),ConfigurationOptions(data_directory="../x"))
def test_unsafe_path_windows():
    with pytest.raises(ConfigurationError): build_configuration(enrollment(),ConfigurationOptions(data_directory="C:\\x"))
def test_unsafe_path_executable():
    with pytest.raises(ConfigurationError): build_configuration(enrollment(),ConfigurationOptions(data_directory="data/run.ps1"))
def test_boolean_maximum_rejected():
    with pytest.raises(ConfigurationError): build_configuration(enrollment(),ConfigurationOptions(maximum_incidents=True))
def test_incident_bound_rejected():
    with pytest.raises(ConfigurationError): build_configuration(enrollment(),ConfigurationOptions(maximum_incidents=0))
def test_receipt_bound_rejected():
    with pytest.raises(ConfigurationError): build_configuration(enrollment(),ConfigurationOptions(maximum_receipt_bytes_per_incident=1023))
def test_retention_rejected():
    with pytest.raises(ConfigurationError): build_configuration(enrollment(),ConfigurationOptions(retention_mode="forever"))
def test_validate_rejects_authority_expansion():
    body=build_configuration(enrollment()).body(); body["authority"]["docker_mutation"]=True
    with pytest.raises(ConfigurationError): validate_configuration(body)
def test_validate_rejects_digest_mismatch():
    body=build_configuration(enrollment()).body(); body["retention"]["maximum_incidents"]=2
    with pytest.raises(ConfigurationError): validate_configuration(body)
