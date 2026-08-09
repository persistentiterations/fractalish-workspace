from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

SCHEMA_VERSION = "1"
PRODUCT = "Bolt-On Continuity for Docker"
PRODUCT_VERSION = "0.2"
ALLOWED_ACTIONS = ("NO_ACTION", "HOLD", "RELEASE")
ALLOWED_RETENTION_MODES = ("bounded_count", "retain_until_operator_deletes")
MAX_INCIDENT_COUNT = 100_000
MAX_RECEIPT_BYTES_PER_INCIDENT = 64 * 1024 * 1024
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ConfigurationOptions:
    data_directory: str = "bolt-on-continuity-data"
    retention_mode: str = "bounded_count"
    max_incident_count: int = 1000
    max_receipt_bytes_per_incident: int = 4 * 1024 * 1024


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest_payload(configuration: Mapping[str, Any]) -> str:
    payload = dict(configuration)
    payload.pop("configuration_digest", None)
    return "sha256:" + hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _validate_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ConfigurationError("invalid data directory")
    if "\\" in value or value.startswith(("/", "~")) or ":" in value or "$" in value or "%" in value:
        raise ConfigurationError("unsafe data directory")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ConfigurationError("unsafe data directory")
    return value


def _bounded_int(value: Any, *, maximum: int, field: str) -> int:
    if type(value) is not int or value <= 0 or value > maximum:
        raise ConfigurationError(f"invalid {field}")
    return value


def _validate_enrollment(enrollment: Mapping[str, Any]) -> tuple[str, str, str]:
    if not isinstance(enrollment, Mapping):
        raise ConfigurationError("enrollment must be an object")
    container_id = enrollment.get("container_id")
    display_name = enrollment.get("display_name")
    image = enrollment.get("image")
    if not isinstance(container_id, str) or CONTAINER_ID_RE.fullmatch(container_id) is None:
        raise ConfigurationError("invalid enrolled container ID")
    if not isinstance(display_name, str) or not display_name:
        raise ConfigurationError("invalid display name")
    if not isinstance(image, str) or not image:
        raise ConfigurationError("invalid image")
    if enrollment.get("observation_only") is not True or enrollment.get("gateway_enabled") is not False:
        raise ConfigurationError("unsafe enrollment defaults")
    return container_id, display_name, image


def build_configuration(enrollment: Mapping[str, Any], options: ConfigurationOptions | None = None) -> dict[str, Any]:
    container_id, display_name, image = _validate_enrollment(enrollment)
    options = options or ConfigurationOptions()
    data_directory = _validate_relative_path(options.data_directory)
    if options.retention_mode not in ALLOWED_RETENTION_MODES:
        raise ConfigurationError("unsupported retention mode")
    max_incident_count = _bounded_int(options.max_incident_count, maximum=MAX_INCIDENT_COUNT, field="max incident count")
    max_receipt_bytes = _bounded_int(
        options.max_receipt_bytes_per_incident,
        maximum=MAX_RECEIPT_BYTES_PER_INCIDENT,
        field="max receipt bytes per incident",
    )
    configuration: dict[str, Any] = {
        "authority": {"decision_vocabulary": list(ALLOWED_ACTIONS), "native_execution_authorized": False},
        "mode": {
            "approval_required": True,
            "autonomous_actions": False,
            "gateway_enabled": False,
            "observation_only": True,
        },
        "product": PRODUCT,
        "product_version": PRODUCT_VERSION,
        "retention": {"max_incident_count": max_incident_count, "mode": options.retention_mode},
        "schema_version": SCHEMA_VERSION,
        "storage": {"data_directory": data_directory, "max_receipt_bytes_per_incident": max_receipt_bytes},
        "subject": {"container_id": container_id, "display_name": display_name, "image": image},
    }
    configuration["configuration_digest"] = _digest_payload(configuration)
    return configuration


def validate_configuration(configuration: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(configuration, Mapping):
        raise ConfigurationError("configuration must be an object")
    expected_top = {
        "authority", "configuration_digest", "mode", "product", "product_version",
        "retention", "schema_version", "storage", "subject",
    }
    if set(configuration) != expected_top:
        raise ConfigurationError("configuration fields mismatch")
    if configuration["schema_version"] != SCHEMA_VERSION or configuration["product"] != PRODUCT or configuration["product_version"] != PRODUCT_VERSION:
        raise ConfigurationError("unsupported configuration identity")
    subject = configuration["subject"]
    if not isinstance(subject, Mapping) or set(subject) != {"container_id", "display_name", "image"}:
        raise ConfigurationError("subject fields mismatch")
    container_id = subject["container_id"]
    if not isinstance(container_id, str) or CONTAINER_ID_RE.fullmatch(container_id) is None:
        raise ConfigurationError("invalid subject container ID")
    if not isinstance(subject["display_name"], str) or not subject["display_name"] or not isinstance(subject["image"], str) or not subject["image"]:
        raise ConfigurationError("invalid subject metadata")
    mode = configuration["mode"]
    required_mode = {"approval_required": True, "autonomous_actions": False, "gateway_enabled": False, "observation_only": True}
    if mode != required_mode:
        raise ConfigurationError("unsafe mode")
    authority = configuration["authority"]
    if authority != {"decision_vocabulary": list(ALLOWED_ACTIONS), "native_execution_authorized": False}:
        raise ConfigurationError("authority expansion")
    storage = configuration["storage"]
    if not isinstance(storage, Mapping) or set(storage) != {"data_directory", "max_receipt_bytes_per_incident"}:
        raise ConfigurationError("storage fields mismatch")
    _validate_relative_path(storage["data_directory"])
    _bounded_int(storage["max_receipt_bytes_per_incident"], maximum=MAX_RECEIPT_BYTES_PER_INCIDENT, field="max receipt bytes per incident")
    retention = configuration["retention"]
    if not isinstance(retention, Mapping) or set(retention) != {"max_incident_count", "mode"}:
        raise ConfigurationError("retention fields mismatch")
    if retention["mode"] not in ALLOWED_RETENTION_MODES:
        raise ConfigurationError("unsupported retention mode")
    _bounded_int(retention["max_incident_count"], maximum=MAX_INCIDENT_COUNT, field="max incident count")
    digest = configuration["configuration_digest"]
    if not isinstance(digest, str) or digest != _digest_payload(configuration):
        raise ConfigurationError("configuration digest mismatch")
    return json.loads(_canonical_bytes(configuration).decode("utf-8"))


def serialize_configuration(configuration: Mapping[str, Any]) -> bytes:
    validated = validate_configuration(configuration)
    return _canonical_bytes(validated)
