import hashlib
import json
from dataclasses import replace

import pytest

from bolt_on.configuration_stage4 import (
    ConfigurationError,
    ConfigurationOptions,
    build_configuration,
    validate_configuration,
)
from bolt_on.discovery import EnrollmentRecord
from bolt_on.receipts import canonical_json_bytes

CID = "a" * 64


def enrollment() -> EnrollmentRecord:
    base = {
        "schema_version": 1,
        "contract": "bolt-on-continuity-v0.3-stage-3",
        "container_id": CID,
        "display_name": "demo",
        "image": "example:1",
        "observed_state": "running",
        "observation_only": True,
        "gateway_enabled": False,
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    return EnrollmentRecord(CID, "demo", "example:1", "running", digest)


def test_build_is_deterministic_and_newline_terminated():
    one = build_configuration(enrollment())
    two = build_configuration(enrollment())
    assert one.canonical_bytes() == two.canonical_bytes()
    assert one.canonical_bytes().endswith(b"\n")
    assert one.body["mode"]["observation_only"] is True
    assert one.body["mode"]["gateway_enabled"] is False


def test_valid_configuration_round_trip():
    built = build_configuration(enrollment())
    parsed = json.loads(built.canonical_bytes())
    validated = validate_configuration(parsed)
    assert validated.canonical_bytes() == built.canonical_bytes()


def test_tampered_enrollment_digest_rejected():
    with pytest.raises(ConfigurationError, match="ENROLLMENT_DIGEST_MISMATCH"):
        build_configuration(replace(enrollment(), enrollment_digest="0" * 64))


def test_unsafe_paths_rejected():
    for path in ("../escape", "C:/absolute", "/absolute", "data\\windows", "$HOME/data", "script.ps1"):
        with pytest.raises(ConfigurationError, match="INVALID_STORAGE_PATH"):
            build_configuration(enrollment(), ConfigurationOptions(data_directory=path))


def test_bool_and_out_of_range_bounds_rejected():
    with pytest.raises(ConfigurationError, match="INVALID_MAXIMUM_INCIDENTS"):
        build_configuration(enrollment(), ConfigurationOptions(maximum_incidents=True))
    with pytest.raises(ConfigurationError, match="INVALID_RECEIPT_BOUND"):
        build_configuration(enrollment(), ConfigurationOptions(maximum_receipt_bytes_per_incident=17))


def test_authority_or_digest_tampering_rejected():
    built = build_configuration(enrollment())
    value = json.loads(built.canonical_bytes())
    value["authority"].append("PAUSE")
    with pytest.raises(ConfigurationError, match="AUTHORITY_EXPANSION"):
        validate_configuration(value)

    value = json.loads(built.canonical_bytes())
    value["subject"]["display_name"] = "changed"
    with pytest.raises(ConfigurationError, match="CONFIGURATION_DIGEST_MISMATCH"):
        validate_configuration(value)