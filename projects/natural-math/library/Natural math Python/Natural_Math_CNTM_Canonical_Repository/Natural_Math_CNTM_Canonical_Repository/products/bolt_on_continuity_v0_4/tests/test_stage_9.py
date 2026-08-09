import json
import pytest

from bolt_on_v0_4.stage_3 import canonical_bytes
from bolt_on_v0_4.stage_9 import (
    AUTHORITY,
    DELETE_CONFIRMATION,
    InstallationPlanError,
    plan_install,
    plan_uninstall,
    sha256,
)

CONFIG = json.loads(r'''{"action_vocabulary":["NO_ACTION","HOLD","RELEASE"],"authority":{"attach_or_distribute_packages":false,"automatic_recovery":false,"background_service":false,"configuration_construction":true,"configuration_validation":true,"container_create_remove":false,"container_enumeration":false,"container_exec":false,"container_inspection":false,"container_start_stop_restart":false,"docker_contact":false,"docker_mutation":false,"enrollment_record_consumption":true,"filesystem_mutation":false,"installer_execution":false,"network_contact":false,"production_claims":false,"publish_release":false},"configuration_digest":"30a66283d7c7d0e775a0de417201e1ba8bee2c96a980cf62da68d58e2dfdb883","mode":{"approval_required":true,"autonomous_actions":false,"gateway_enabled":false,"observation_only":true},"product":"Bolt-On Continuity v0.4","qualified_stage_3_head":"c6aa6590b46e802b1e59d05f3af94c2ce9ed58a0","retention":{"maximum_incidents":1000,"mode":"retain_until_operator_deletes"},"schema_version":1,"stage":4,"stage_3_qualification_record_sha256":"1715c97822c5639b4850a46f28f5620b09c19a981e1b32e93ecb4f9bbc741bf0","stage_3_verifier_manifest_sha256":"f68cee14b5c47572e84b839cd2b2917f7c2c3f706bc87a7f83c0937b5e5fdbc9","storage":{"data_directory":"data/bolt-on-continuity","maximum_receipt_bytes_per_incident":1048576,"persistence_authorized":false},"subject":{"container_id":"e9bb79a0afa1913de3604814cfe26e77c67b7c8cdc74ce31eb0584128b116ea3","display_name":"bolt-on-v0-4-stage4-fixture","image":"alpine:3.20","platform":"linux"}}''')

@pytest.mark.parametrize(("state", "outcome"), [
    ("ABSENT", "PLAN_INSTALL"),
    ("INSTALLED", "ALREADY_INSTALLED"),
    ("PARTIAL", "FAIL_CLOSED_PARTIAL"),
    ("CONFLICT", "FAIL_CLOSED_CONFLICT"),
])
def test_install_outcomes(state, outcome):
    assert plan_install(CONFIG, state).body()["outcome"] == outcome

@pytest.mark.parametrize(("state", "choice", "token", "outcome"), [
    ("INSTALLED", "RETAIN_DATA", "", "PLAN_UNINSTALL_RETAIN_DATA"),
    ("INSTALLED", "DELETE_DATA", "", "FAIL_CLOSED_CONFIRMATION"),
    ("INSTALLED", "DELETE_DATA", DELETE_CONFIRMATION, "PLAN_UNINSTALL_DELETE_DATA"),
    ("ABSENT", "RETAIN_DATA", "", "ALREADY_ABSENT"),
    ("PARTIAL", "RETAIN_DATA", "", "FAIL_CLOSED_PARTIAL"),
    ("CONFLICT", "RETAIN_DATA", "", "FAIL_CLOSED_CONFLICT"),
])
def test_uninstall_outcomes(state, choice, token, outcome):
    assert plan_uninstall(CONFIG, state, choice, token).body()["outcome"] == outcome

def test_uninstall_defaults_to_retention():
    body = plan_uninstall(CONFIG, "INSTALLED").body()
    assert body["retention_choice"] == "RETAIN_DATA"
    assert body["outcome"] == "PLAN_UNINSTALL_RETAIN_DATA"

def test_invalid_installation_state_rejected():
    with pytest.raises(InstallationPlanError):
        plan_install(CONFIG, "UNKNOWN")

def test_invalid_retention_choice_rejected():
    with pytest.raises(InstallationPlanError):
        plan_uninstall(CONFIG, "INSTALLED", "MAYBE")

def test_invalid_configuration_rejected():
    bad = dict(CONFIG)
    bad["configuration_digest"] = "0" * 64
    with pytest.raises(InstallationPlanError):
        plan_install(bad, "ABSENT")

def test_delete_confirmation_is_exact():
    assert plan_uninstall(CONFIG, "INSTALLED", "DELETE_DATA", "delete receipt data").body()["outcome"] == "FAIL_CLOSED_CONFIRMATION"

def test_subject_is_protected_not_targeted():
    body = plan_install(CONFIG, "ABSENT").body()
    cid = body["protected_subject"]["container_id"]
    assert all(cid not in target for target in body["product_owned_paths"])

def test_authority_exact_enabled_set():
    enabled = {key for key, value in AUTHORITY.items() if value}
    assert enabled == {
        "stage_4_configuration_consumption",
        "stage_8_record_binding",
        "installation_plan_construction",
        "uninstall_plan_construction",
        "retention_choice_validation",
        "deletion_confirmation_validation",
    }

def test_plan_digest_valid():
    body = plan_install(CONFIG, "ABSENT").body()
    base = dict(body)
    digest = base.pop("plan_digest")
    assert digest == "sha256:" + sha256(canonical_bytes(base))

def test_deterministic():
    assert plan_install(CONFIG, "ABSENT").canonical_bytes() == plan_install(CONFIG, "ABSENT").canonical_bytes()

def test_safety_fields_are_false():
    body = plan_uninstall(CONFIG, "INSTALLED", "DELETE_DATA", DELETE_CONFIRMATION).body()
    for key in ("native_execution_authorized", "container_mutation_authorized", "execution_performed", "filesystem_mutation_performed", "deletion_performed", "gateway_enabled"):
        assert body[key] is False
    assert body["observation_only"] is True

def test_paths_derived_from_configuration():
    body = plan_install(CONFIG, "ABSENT").body()
    assert body["product_owned_paths"] == [
        "data/bolt-on-continuity/configuration.json",
        "data/bolt-on-continuity/receipts",
    ]
