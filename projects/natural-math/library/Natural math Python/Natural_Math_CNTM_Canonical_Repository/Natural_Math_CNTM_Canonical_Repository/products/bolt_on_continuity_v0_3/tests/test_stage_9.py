import hashlib

import pytest

from bolt_on.configuration_stage4 import build_configuration
from bolt_on.discovery import EnrollmentRecord
from bolt_on.installation_stage9 import (
    DELETE_CONFIRMATION,
    InstallationPlanError,
    plan_install,
    plan_uninstall,
)
from bolt_on.receipts import canonical_json_bytes

CID = "a" * 64


def configuration():
    base = {
        "container_id": CID,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "display_name": "demo",
        "gateway_enabled": False,
        "image": "example:1",
        "observation_only": True,
        "observed_state": "running",
        "schema_version": 1,
    }
    record = EnrollmentRecord(CID, "demo", "example:1", "running", hashlib.sha256(canonical_json_bytes(base)).hexdigest())
    return build_configuration(record)


def test_install_plan_is_deterministic_and_non_executing():
    one = plan_install(configuration(), "ABSENT")
    two = plan_install(configuration(), "ABSENT")
    assert one.canonical_bytes() == two.canonical_bytes()
    assert one.body["outcome"] == "PLAN_INSTALL"
    assert one.body["execution_performed"] is False
    assert one.body["container_mutation_authorized"] is False


def test_installed_partial_and_conflict_classify():
    assert plan_install(configuration(), "INSTALLED").body["outcome"] == "ALREADY_INSTALLED"
    assert plan_install(configuration(), "PARTIAL").body["outcome"] == "FAIL_CLOSED_PARTIAL"
    assert plan_install(configuration(), "CONFLICT").body["outcome"] == "FAIL_CLOSED_CONFLICT"


def test_uninstall_retains_data_by_default():
    plan = plan_uninstall(configuration(), "INSTALLED")
    assert plan.body["outcome"] == "PLAN_UNINSTALL_RETAIN_DATA"
    assert plan.body["deletion_performed"] is False
    assert plan.body["product_owned_paths"] == ["data/bolt-on-continuity/configuration.json"]


def test_delete_plan_requires_exact_confirmation():
    denied = plan_uninstall(configuration(), "INSTALLED", "DELETE_DATA", "delete receipt data")
    accepted = plan_uninstall(configuration(), "INSTALLED", "DELETE_DATA", DELETE_CONFIRMATION)
    assert denied.body["outcome"] == "FAIL_CLOSED_CONFIRMATION"
    assert accepted.body["outcome"] == "PLAN_UNINSTALL_DELETE_DATA"
    assert accepted.body["deletion_performed"] is False


def test_subject_is_protected_reference_not_target():
    plan = plan_install(configuration(), "ABSENT")
    assert plan.body["protected_subject"] == {"container_id": CID}
    assert all(CID not in path for path in plan.body["product_owned_paths"])


def test_unknown_inputs_fail_closed():
    with pytest.raises(InstallationPlanError, match="INVALID_INSTALLATION_STATE"):
        plan_install(configuration(), "UNKNOWN")
    with pytest.raises(InstallationPlanError, match="INVALID_RETENTION_CHOICE"):
        plan_uninstall(configuration(), "INSTALLED", "MAYBE")
