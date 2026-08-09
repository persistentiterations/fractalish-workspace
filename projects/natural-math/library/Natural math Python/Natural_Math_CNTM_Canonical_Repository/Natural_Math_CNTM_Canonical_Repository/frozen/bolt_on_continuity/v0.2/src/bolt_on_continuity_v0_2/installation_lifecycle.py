from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from .product_configuration import validate_configuration

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "9"
INSTALL_STATES = frozenset({"ABSENT", "INSTALLED", "PARTIAL", "CONFLICT"})
RETENTION_CHOICES = frozenset({"RETAIN_DATA", "DELETE_DATA"})
DELETE_CONFIRMATION = "DELETE RECEIPT DATA"


class LifecycleError(ValueError):
    pass


@dataclass(frozen=True)
class LifecycleResult:
    payload: dict[str, Any]

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.payload)


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(payload: Mapping[str, Any]) -> str:
    value = dict(payload)
    value.pop("plan_digest", None)
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _safe_defaults() -> dict[str, bool]:
    return {
        "container_mutation_authorized": False,
        "gateway_enabled": False,
        "native_execution_authorized": False,
        "observation_only": True,
    }


def _validate_state(state: Any) -> str:
    if not isinstance(state, str) or state not in INSTALL_STATES:
        raise LifecycleError("unsupported installation state")
    return state


def _product_paths(configuration: Mapping[str, Any]) -> tuple[str, ...]:
    validated = validate_configuration(configuration)
    data_dir = validated["storage"]["data_directory"]
    path = PurePosixPath(data_dir)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise LifecycleError("unsafe product path")
    return (
        "product/bin/bolt-on-continuity",
        "product/config/product.json",
        f"product/data/{data_dir}",
    )


def _result(*, kind: str, outcome: str, configuration: Mapping[str, Any], operations: list[dict[str, str]], data_choice: str | None = None) -> LifecycleResult:
    validated = validate_configuration(configuration)
    payload: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "kind": kind,
        "operations": operations,
        "outcome": outcome,
        "protected_subject": validated["subject"]["container_id"],
        "safe_defaults": _safe_defaults(),
        "schema_version": SCHEMA_VERSION,
    }
    if data_choice is not None:
        payload["data_choice"] = data_choice
    payload["plan_digest"] = _digest(payload)
    return LifecycleResult(payload)


def plan_install(configuration: Mapping[str, Any], installation_state: str) -> LifecycleResult:
    state = _validate_state(installation_state)
    paths = _product_paths(configuration)
    if state == "PARTIAL":
        return _result(kind="INSTALL", outcome="FAIL_CLOSED_PARTIAL", configuration=configuration, operations=[])
    if state == "CONFLICT":
        return _result(kind="INSTALL", outcome="FAIL_CLOSED_CONFLICT", configuration=configuration, operations=[])
    if state == "INSTALLED":
        return _result(kind="INSTALL", outcome="ALREADY_INSTALLED", configuration=configuration, operations=[])
    operations = [
        {"operation": "CREATE_PRODUCT_ARTIFACT", "target": paths[0]},
        {"operation": "CREATE_PRODUCT_ARTIFACT", "target": paths[1]},
        {"operation": "CREATE_PRODUCT_DATA_ROOT", "target": paths[2]},
    ]
    return _result(kind="INSTALL", outcome="PLAN_INSTALL", configuration=configuration, operations=operations)


def plan_uninstall(
    configuration: Mapping[str, Any],
    installation_state: str,
    *,
    data_choice: str = "RETAIN_DATA",
    confirmation: str | None = None,
) -> LifecycleResult:
    state = _validate_state(installation_state)
    if data_choice not in RETENTION_CHOICES:
        raise LifecycleError("unsupported retention choice")
    if state == "PARTIAL":
        return _result(kind="UNINSTALL", outcome="FAIL_CLOSED_PARTIAL", configuration=configuration, operations=[], data_choice=data_choice)
    if state == "CONFLICT":
        return _result(kind="UNINSTALL", outcome="FAIL_CLOSED_CONFLICT", configuration=configuration, operations=[], data_choice=data_choice)
    if state == "ABSENT":
        return _result(kind="UNINSTALL", outcome="ALREADY_ABSENT", configuration=configuration, operations=[], data_choice=data_choice)
    paths = _product_paths(configuration)
    if data_choice == "DELETE_DATA" and confirmation != DELETE_CONFIRMATION:
        return _result(kind="UNINSTALL", outcome="FAIL_CLOSED_CONFIRMATION", configuration=configuration, operations=[], data_choice=data_choice)
    operations = [
        {"operation": "REMOVE_PRODUCT_ARTIFACT", "target": paths[0]},
        {"operation": "REMOVE_PRODUCT_ARTIFACT", "target": paths[1]},
    ]
    if data_choice == "DELETE_DATA":
        operations.append({"operation": "DELETE_PRODUCT_DATA", "target": paths[2]})
        outcome = "PLAN_UNINSTALL_DELETE_DATA"
    else:
        outcome = "PLAN_UNINSTALL_RETAIN_DATA"
    return _result(kind="UNINSTALL", outcome=outcome, configuration=configuration, operations=operations, data_choice=data_choice)


def validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise LifecycleError("plan must be an object")
    expected = {"contract_version", "kind", "operations", "outcome", "plan_digest", "protected_subject", "safe_defaults", "schema_version"}
    if plan.get("kind") == "UNINSTALL":
        expected.add("data_choice")
    if set(plan) != expected:
        raise LifecycleError("plan fields mismatch")
    if plan["schema_version"] != SCHEMA_VERSION or plan["contract_version"] != CONTRACT_VERSION:
        raise LifecycleError("unsupported plan identity")
    if plan["safe_defaults"] != _safe_defaults():
        raise LifecycleError("unsafe plan defaults")
    if not isinstance(plan["operations"], list):
        raise LifecycleError("operations must be a list")
    protected = plan["protected_subject"]
    for operation in plan["operations"]:
        if not isinstance(operation, Mapping) or set(operation) != {"operation", "target"}:
            raise LifecycleError("operation fields mismatch")
        target = operation["target"]
        if not isinstance(target, str) or not target.startswith("product/") or protected in target:
            raise LifecycleError("unsafe operation target")
    if plan["plan_digest"] != _digest(plan):
        raise LifecycleError("plan digest mismatch")
    return json.loads(_canonical_bytes(plan).decode("utf-8"))
