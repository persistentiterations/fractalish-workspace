"""Stage 4 canonical configuration construction and validation."""

from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from .discovery import EnrollmentRecord
from .receipts import canonical_json_bytes
from .version import __version__

CID_RE = re.compile(r"^[0-9a-f]{64}$")
PRODUCT = "bolt-on-continuity-for-docker"
SCHEMA_VERSION = 1
AUTHORITY = ("NO_ACTION", "HOLD", "RELEASE")
RETENTION_MODES = {"retain_until_operator_deletes", "bounded_count"}
EXECUTABLE_SUFFIXES = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".com"}


class ConfigurationError(ValueError):
    """Stable fail-closed Stage 4 validation error."""


@dataclass(frozen=True)
class ConfigurationOptions:
    data_directory: str = "data/bolt-on-continuity"
    maximum_incidents: int = 1000
    maximum_receipt_bytes_per_incident: int = 1048576
    retention_mode: str = "retain_until_operator_deletes"


@dataclass(frozen=True)
class CanonicalConfiguration:
    body: Mapping[str, Any]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(dict(self.body)) + b"\n"

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")


def _validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ConfigurationError("INVALID_STORAGE_PATH")
    if "$" in value or "%" in value or "\\" in value or ":" in value or value.startswith(("/", "//")):
        raise ConfigurationError("INVALID_STORAGE_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ConfigurationError("INVALID_STORAGE_PATH")
    if path.suffix.lower() in EXECUTABLE_SUFFIXES:
        raise ConfigurationError("INVALID_STORAGE_PATH")
    return path.as_posix()


def _validate_int(value: object, minimum: int, maximum: int, code: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ConfigurationError(code)
    return value


def _enrollment_base(record: EnrollmentRecord) -> dict[str, object]:
    body = record.body()
    base = dict(body)
    base.pop("enrollment_digest", None)
    return base


def validate_enrollment(record: EnrollmentRecord) -> None:
    body = record.body()
    required = {
        "schema_version",
        "contract",
        "container_id",
        "display_name",
        "image",
        "observed_state",
        "observation_only",
        "gateway_enabled",
        "enrollment_digest",
    }
    if set(body) != required:
        raise ConfigurationError("INVALID_ENROLLMENT_CONTRACT")
    if body["schema_version"] != 1 or body["contract"] != "bolt-on-continuity-v0.3-stage-3":
        raise ConfigurationError("INVALID_ENROLLMENT_CONTRACT")
    if not isinstance(record.container_id, str) or not CID_RE.fullmatch(record.container_id):
        raise ConfigurationError("INVALID_SUBJECT_ID")
    if body["observation_only"] is not True or body["gateway_enabled"] is not False:
        raise ConfigurationError("UNSAFE_ENROLLMENT_AUTHORITY")
    expected = hashlib.sha256(canonical_json_bytes(_enrollment_base(record))).hexdigest()
    if record.enrollment_digest != expected:
        raise ConfigurationError("ENROLLMENT_DIGEST_MISMATCH")


def build_configuration(record: EnrollmentRecord, options: ConfigurationOptions = ConfigurationOptions()) -> CanonicalConfiguration:
    validate_enrollment(record)
    data_directory = _validate_relative_path(options.data_directory)
    maximum_incidents = _validate_int(options.maximum_incidents, 1, 100000, "INVALID_MAXIMUM_INCIDENTS")
    receipt_bytes = _validate_int(options.maximum_receipt_bytes_per_incident, 1024, 16777216, "INVALID_RECEIPT_BOUND")
    if options.retention_mode not in RETENTION_MODES:
        raise ConfigurationError("INVALID_RETENTION_MODE")

    base: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "product_version": __version__,
        "subject": {
            "container_id": record.container_id,
            "display_name": record.display_name,
            "image": record.image,
        },
        "mode": {
            "observation_only": True,
            "gateway_enabled": False,
            "approval_required": True,
            "autonomous_actions": False,
        },
        "storage": {
            "data_directory": data_directory,
            "maximum_receipt_bytes_per_incident": receipt_bytes,
        },
        "retention": {
            "mode": options.retention_mode,
            "maximum_incidents": maximum_incidents,
        },
        "authority": list(AUTHORITY),
    }
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    body = dict(base)
    body["configuration_digest"] = digest
    result = CanonicalConfiguration(body)
    validate_configuration(json.loads(result.canonical_bytes()))
    return result


def validate_configuration(value: object) -> CanonicalConfiguration:
    if not isinstance(value, dict):
        raise ConfigurationError("MALFORMED_CONFIGURATION")
    required = {"schema_version", "product", "product_version", "subject", "mode", "storage", "retention", "authority", "configuration_digest"}
    if set(value) != required:
        raise ConfigurationError("CONFIGURATION_FIELDS_MISMATCH")
    if value["schema_version"] != SCHEMA_VERSION or value["product"] != PRODUCT or value["product_version"] != __version__:
        raise ConfigurationError("UNSUPPORTED_CONFIGURATION_VERSION")

    subject = value["subject"]
    if not isinstance(subject, dict) or set(subject) != {"container_id", "display_name", "image"} or not CID_RE.fullmatch(subject.get("container_id", "")):
        raise ConfigurationError("INVALID_SUBJECT")
    if not isinstance(subject["display_name"], str) or not isinstance(subject["image"], str):
        raise ConfigurationError("INVALID_SUBJECT")

    expected_mode = {"observation_only": True, "gateway_enabled": False, "approval_required": True, "autonomous_actions": False}
    if value["mode"] != expected_mode:
        raise ConfigurationError("UNSAFE_MODE")
    if value["authority"] != list(AUTHORITY):
        raise ConfigurationError("AUTHORITY_EXPANSION")

    storage = value["storage"]
    if not isinstance(storage, dict) or set(storage) != {"data_directory", "maximum_receipt_bytes_per_incident"}:
        raise ConfigurationError("INVALID_STORAGE")
    _validate_relative_path(storage["data_directory"])
    _validate_int(storage["maximum_receipt_bytes_per_incident"], 1024, 16777216, "INVALID_RECEIPT_BOUND")

    retention = value["retention"]
    if not isinstance(retention, dict) or set(retention) != {"mode", "maximum_incidents"}:
        raise ConfigurationError("INVALID_RETENTION")
    if retention["mode"] not in RETENTION_MODES:
        raise ConfigurationError("INVALID_RETENTION_MODE")
    _validate_int(retention["maximum_incidents"], 1, 100000, "INVALID_MAXIMUM_INCIDENTS")

    digest = value["configuration_digest"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ConfigurationError("INVALID_CONFIGURATION_DIGEST")
    base = dict(value)
    del base["configuration_digest"]
    expected = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    if digest != expected:
        raise ConfigurationError("CONFIGURATION_DIGEST_MISMATCH")
    return CanonicalConfiguration(dict(value))