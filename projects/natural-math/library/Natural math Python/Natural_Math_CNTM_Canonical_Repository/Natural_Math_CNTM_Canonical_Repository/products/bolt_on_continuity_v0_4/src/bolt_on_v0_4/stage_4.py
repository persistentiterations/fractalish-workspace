"""Deterministic Stage 4 canonical configuration construction and validation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Mapping

from .stage_3 import AUTHORITY as STAGE_3_AUTHORITY
from .stage_3 import EnrollmentRecord, canonical_bytes

PRODUCT = "Bolt-On Continuity v0.4"
STAGE = 4
SCHEMA_VERSION = 1
QUALIFIED_STAGE_3_HEAD = "c6aa6590b46e802b1e59d05f3af94c2ce9ed58a0"
STAGE_3_QUALIFICATION_RECORD_SHA256 = "1715c97822c5639b4850a46f28f5620b09c19a981e1b32e93ecb4f9bbc741bf0"
STAGE_3_VERIFIER_MANIFEST_SHA256 = "f68cee14b5c47572e84b839cd2b2917f7c2c3f706bc87a7f83c0937b5e5fdbc9"
FULL_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_STATES = frozenset({"created", "restarting", "running", "removing", "paused", "exited", "dead"})
RETENTION_MODES = frozenset({"retain_until_operator_deletes", "bounded_count"})
ACTION_VOCABULARY = ("NO_ACTION", "HOLD", "RELEASE")
EXECUTABLE_SUFFIXES = frozenset({".exe", ".bat", ".cmd", ".ps1", ".sh", ".com"})

AUTHORITY = {
    "configuration_construction": True,
    "configuration_validation": True,
    "enrollment_record_consumption": True,
    "docker_contact": False,
    "docker_mutation": False,
    "container_enumeration": False,
    "container_inspection": False,
    "container_start_stop_restart": False,
    "container_exec": False,
    "container_create_remove": False,
    "filesystem_mutation": False,
    "installer_execution": False,
    "background_service": False,
    "network_contact": False,
    "automatic_recovery": False,
    "attach_or_distribute_packages": False,
    "publish_release": False,
    "production_claims": False,
}

class ConfigurationError(ValueError):
    """Stable fail-closed Stage 4 validation error."""

@dataclass(frozen=True)
class ConfigurationOptions:
    data_directory: str = "data/bolt-on-continuity"
    maximum_incidents: int = 1000
    maximum_receipt_bytes_per_incident: int = 1_048_576
    retention_mode: str = "retain_until_operator_deletes"

@dataclass(frozen=True)
class CanonicalConfiguration:
    body_value: Mapping[str, object]

    def body(self) -> dict[str, object]:
        return dict(self.body_value)

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.body()) + b"\n"

    def canonical_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")

    @property
    def configuration_digest(self) -> str:
        return str(self.body_value["configuration_digest"])


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_plain_int(value: object, minimum: int, maximum: int, code: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ConfigurationError(code)
    return value


def _validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ConfigurationError("INVALID_STORAGE_PATH")
    if any(token in value for token in ("$", "%", "\\", ":", "\x00")):
        raise ConfigurationError("INVALID_STORAGE_PATH")
    if value.startswith(("/", "//", "~")):
        raise ConfigurationError("INVALID_STORAGE_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ConfigurationError("INVALID_STORAGE_PATH")
    if path.suffix.lower() in EXECUTABLE_SUFFIXES:
        raise ConfigurationError("INVALID_STORAGE_PATH")
    return path.as_posix()


def enrollment_from_mapping(value: object) -> EnrollmentRecord:
    if not isinstance(value, dict):
        raise ConfigurationError("MALFORMED_ENROLLMENT")
    required = {"authority", "container_id", "display_name", "image", "observed_state", "platform", "product", "qualified_stage_2_head", "record_digest", "schema_version", "stage", "stage_2_qualification_record_sha256", "stage_2_verifier_manifest_sha256", "status"}
    if set(value) != required:
        raise ConfigurationError("ENROLLMENT_FIELDS_MISMATCH")
    authority = value["authority"]
    if not isinstance(authority, dict) or any(type(item) is not bool for item in authority.values()):
        raise ConfigurationError("INVALID_ENROLLMENT_AUTHORITY")
    return EnrollmentRecord(product=value["product"], stage=value["stage"], schema_version=value["schema_version"], qualified_stage_2_head=value["qualified_stage_2_head"], stage_2_qualification_record_sha256=value["stage_2_qualification_record_sha256"], stage_2_verifier_manifest_sha256=value["stage_2_verifier_manifest_sha256"], container_id=value["container_id"], display_name=value["display_name"], image=value["image"], observed_state=value["observed_state"], platform=value["platform"], authority=dict(authority), status=value["status"], record_digest=value["record_digest"])


def validate_enrollment(record: EnrollmentRecord) -> None:
    if record.product != PRODUCT or record.stage != 3 or record.schema_version != 1:
        raise ConfigurationError("INVALID_ENROLLMENT_CONTRACT")
    if record.status != "STAGE_3_ENROLLED":
        raise ConfigurationError("INVALID_ENROLLMENT_STATUS")
    if not isinstance(record.container_id, str) or not FULL_CONTAINER_ID.fullmatch(record.container_id):
        raise ConfigurationError("INVALID_SUBJECT_ID")
    if not isinstance(record.display_name, str) or not record.display_name or len(record.display_name) > 256:
        raise ConfigurationError("INVALID_SUBJECT_METADATA")
    if not isinstance(record.image, str) or not record.image or len(record.image) > 256:
        raise ConfigurationError("INVALID_SUBJECT_METADATA")
    if record.observed_state not in ALLOWED_STATES or record.platform != "linux":
        raise ConfigurationError("INVALID_SUBJECT_PLATFORM_OR_STATE")
    if dict(record.authority) != STAGE_3_AUTHORITY:
        raise ConfigurationError("INVALID_ENROLLMENT_AUTHORITY")
    if not isinstance(record.record_digest, str) or not DIGEST.fullmatch(record.record_digest):
        raise ConfigurationError("INVALID_ENROLLMENT_DIGEST")
    if record.record_digest != sha256(canonical_bytes(record.body_without_digest())):
        raise ConfigurationError("ENROLLMENT_DIGEST_MISMATCH")


def build_configuration(record: EnrollmentRecord, options: ConfigurationOptions = ConfigurationOptions()) -> CanonicalConfiguration:
    validate_enrollment(record)
    data_directory = _validate_relative_path(options.data_directory)
    maximum_incidents = _require_plain_int(options.maximum_incidents, 1, 100_000, "INVALID_MAXIMUM_INCIDENTS")
    maximum_bytes = _require_plain_int(options.maximum_receipt_bytes_per_incident, 1_024, 16_777_216, "INVALID_RECEIPT_BOUND")
    if options.retention_mode not in RETENTION_MODES:
        raise ConfigurationError("INVALID_RETENTION_MODE")
    base: dict[str, object] = {
        "action_vocabulary": list(ACTION_VOCABULARY),
        "authority": dict(AUTHORITY),
        "mode": {"approval_required": True, "autonomous_actions": False, "gateway_enabled": False, "observation_only": True},
        "product": PRODUCT,
        "qualified_stage_3_head": QUALIFIED_STAGE_3_HEAD,
        "retention": {"maximum_incidents": maximum_incidents, "mode": options.retention_mode},
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "stage_3_qualification_record_sha256": STAGE_3_QUALIFICATION_RECORD_SHA256,
        "stage_3_verifier_manifest_sha256": STAGE_3_VERIFIER_MANIFEST_SHA256,
        "storage": {"data_directory": data_directory, "maximum_receipt_bytes_per_incident": maximum_bytes, "persistence_authorized": False},
        "subject": {"container_id": record.container_id, "display_name": record.display_name, "image": record.image, "platform": record.platform},
    }
    body = {**base, "configuration_digest": sha256(canonical_bytes(base))}
    result = CanonicalConfiguration(body)
    validate_configuration(json.loads(result.canonical_bytes()))
    return result


def validate_configuration(value: object) -> CanonicalConfiguration:
    if not isinstance(value, dict):
        raise ConfigurationError("MALFORMED_CONFIGURATION")
    required = {"action_vocabulary", "authority", "configuration_digest", "mode", "product", "qualified_stage_3_head", "retention", "schema_version", "stage", "stage_3_qualification_record_sha256", "stage_3_verifier_manifest_sha256", "storage", "subject"}
    if set(value) != required:
        raise ConfigurationError("CONFIGURATION_FIELDS_MISMATCH")
    if value["schema_version"] != SCHEMA_VERSION or value["stage"] != STAGE or value["product"] != PRODUCT:
        raise ConfigurationError("UNSUPPORTED_CONFIGURATION_VERSION")
    if value["qualified_stage_3_head"] != QUALIFIED_STAGE_3_HEAD or value["stage_3_qualification_record_sha256"] != STAGE_3_QUALIFICATION_RECORD_SHA256 or value["stage_3_verifier_manifest_sha256"] != STAGE_3_VERIFIER_MANIFEST_SHA256:
        raise ConfigurationError("STAGE_3_BINDING_MISMATCH")
    if value["action_vocabulary"] != list(ACTION_VOCABULARY):
        raise ConfigurationError("ACTION_VOCABULARY_MISMATCH")
    if value["authority"] != AUTHORITY:
        raise ConfigurationError("AUTHORITY_EXPANSION")
    if value["mode"] != {"approval_required": True, "autonomous_actions": False, "gateway_enabled": False, "observation_only": True}:
        raise ConfigurationError("UNSAFE_MODE")
    subject = value["subject"]
    if not isinstance(subject, dict) or set(subject) != {"container_id", "display_name", "image", "platform"} or not isinstance(subject.get("container_id"), str) or not FULL_CONTAINER_ID.fullmatch(subject["container_id"]) or not isinstance(subject.get("display_name"), str) or not subject["display_name"] or not isinstance(subject.get("image"), str) or not subject["image"] or subject.get("platform") != "linux":
        raise ConfigurationError("INVALID_SUBJECT")
    storage = value["storage"]
    if not isinstance(storage, dict) or set(storage) != {"data_directory", "maximum_receipt_bytes_per_incident", "persistence_authorized"}:
        raise ConfigurationError("INVALID_STORAGE")
    _validate_relative_path(storage["data_directory"])
    _require_plain_int(storage["maximum_receipt_bytes_per_incident"], 1_024, 16_777_216, "INVALID_RECEIPT_BOUND")
    if storage["persistence_authorized"] is not False:
        raise ConfigurationError("PERSISTENCE_AUTHORITY_EXPANSION")
    retention = value["retention"]
    if not isinstance(retention, dict) or set(retention) != {"maximum_incidents", "mode"}:
        raise ConfigurationError("INVALID_RETENTION")
    _require_plain_int(retention["maximum_incidents"], 1, 100_000, "INVALID_MAXIMUM_INCIDENTS")
    if retention["mode"] not in RETENTION_MODES:
        raise ConfigurationError("INVALID_RETENTION_MODE")
    digest = value["configuration_digest"]
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise ConfigurationError("INVALID_CONFIGURATION_DIGEST")
    base = dict(value)
    del base["configuration_digest"]
    if digest != sha256(canonical_bytes(base)):
        raise ConfigurationError("CONFIGURATION_DIGEST_MISMATCH")
    return CanonicalConfiguration(dict(value))
