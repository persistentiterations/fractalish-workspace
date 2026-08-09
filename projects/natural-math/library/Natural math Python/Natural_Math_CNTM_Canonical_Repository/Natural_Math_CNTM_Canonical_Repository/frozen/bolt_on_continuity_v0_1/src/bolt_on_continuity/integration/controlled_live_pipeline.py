from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

class Stage8Rejected(RuntimeError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code

def canonical_json(value: Any) -> bytes:
    if isinstance(value, float):
        raise TypeError("floating-point values are forbidden")
    if isinstance(value, dict):
        for item in value.values():
            canonical_json(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            canonical_json(item)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()

def valid_container_id(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdefABCDEF" for ch in value)
    )

def _load_class(path: Path, module_name: str, class_name: str):
    if not path.is_file():
        raise Stage8Rejected("FOUNDATION_MISSING", f"missing foundation module: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise Stage8Rejected("FOUNDATION_MISSING", f"cannot load foundation module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)

class ControlledLivePipeline:
    def __init__(self, product_root: Path, container_id: str, transport: Any):
        if not valid_container_id(container_id):
            raise ValueError("full 64-character hexadecimal container ID required")
        self.product_root = Path(product_root)
        self.container_id = container_id.lower()
        self.configuration = {
            "schema_version": "1",
            "product": "bolt_on_continuity_v0_1",
            "stage": "8",
            "native_allowlist": [
                ["docker", "inspect"],
                ["docker", "pause"],
                ["docker", "unpause"],
            ],
            "subject_binding": "full_64_character_container_id",
            "final_state": {"running": True, "paused": False},
        }
        self.configuration_digest = digest(self.configuration)

        executor_path = self.product_root / "src" / "bolt_on_continuity" / "execution" / "controlled_native_executor.py"
        binder_path = self.product_root / "src" / "bolt_on_continuity" / "integration" / "continuity_pipeline.py"
        Executor = _load_class(executor_path, "_stage8_executor", "ControlledNativeExecutor")
        Binder = _load_class(binder_path, "_stage8_binder", "ContinuityPipelineBinder")
        self.executor = Executor(self.container_id, transport)
        self.binder = Binder(self.container_id, self.configuration_digest)

    def _governance_records(self, observation: dict[str, Any], issued_at_epoch: int):
        observation_digest = digest(observation)
        incident_body = {
            "schema_version": "1",
            "incident_id": "incident-" + observation_digest[7:23],
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "observation_digest": observation_digest,
            "opened_at_epoch": issued_at_epoch,
            "incident_class": "CONTROLLED_CONTINUITY_QUALIFICATION",
        }
        incident = {**incident_body, "export_digest": digest(incident_body)}

        hold_projection_body = {
            "schema_version": "1",
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "incident_export_digest": incident["export_digest"],
            "projected_action": "HOLD",
            "projection_sequence": 0,
        }
        hold_projection = {**hold_projection_body, "projection_digest": digest(hold_projection_body)}

        hold_gateway_body = {
            "schema_version": "1",
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "projection_digest": hold_projection["projection_digest"],
            "decision": "APPROVE",
            "gateway_sequence": 0,
        }
        hold_gateway = {**hold_gateway_body, "gateway_decision_digest": digest(hold_gateway_body)}

        hold_plan_body = {
            "schema_version": "1",
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "gateway_decision_digest": hold_gateway["gateway_decision_digest"],
            "native_operation": "pause",
            "argument_vector": ["docker", "pause", self.container_id],
            "dry_run": True,
            "adapter_sequence": 0,
        }
        hold_plan = {**hold_plan_body, "plan_digest": digest(hold_plan_body)}

        release_projection_body = {
            "schema_version": "1",
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "incident_export_digest": incident["export_digest"],
            "projected_action": "RELEASE",
            "projection_sequence": 1,
        }
        release_projection = {**release_projection_body, "projection_digest": digest(release_projection_body)}

        release_gateway_body = {
            "schema_version": "1",
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "projection_digest": release_projection["projection_digest"],
            "decision": "APPROVE",
            "gateway_sequence": 1,
        }
        release_gateway = {**release_gateway_body, "gateway_decision_digest": digest(release_gateway_body)}

        release_plan_body = {
            "schema_version": "1",
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "gateway_decision_digest": release_gateway["gateway_decision_digest"],
            "native_operation": "unpause",
            "argument_vector": ["docker", "unpause", self.container_id],
            "dry_run": True,
            "adapter_sequence": 1,
        }
        release_plan = {**release_plan_body, "plan_digest": digest(release_plan_body)}

        return {
            "incident_export": incident,
            "hold_projection": hold_projection,
            "hold_gateway": hold_gateway,
            "hold_plan": hold_plan,
            "release_projection": release_projection,
            "release_gateway": release_gateway,
            "release_plan": release_plan,
        }

    def qualify(self, issued_at_epoch: int) -> dict[str, Any]:
        if type(issued_at_epoch) is not int or issued_at_epoch < 0:
            raise Stage8Rejected("MALFORMED_TIME", "issued_at_epoch must be a nonnegative integer")

        initial = self.executor.inspect_state()
        if initial.get("running") is not True or initial.get("paused") is not False:
            raise Stage8Rejected("UNSAFE_INITIAL_STATE", "container must begin running and unpaused")

        records = self._governance_records(initial, issued_at_epoch)
        hold_receipt = None
        recovery_attempted = False
        try:
            hold_receipt = self.executor.execute("HOLD", 0, issued_at_epoch)
            release_receipt = self.executor.execute("RELEASE", 1, issued_at_epoch + 1)
        except Exception:
            if hold_receipt is not None:
                try:
                    state = self.executor.inspect_state()
                    if state.get("running") is True and state.get("paused") is True:
                        recovery_attempted = True
                        self.executor.execute("RELEASE", 999, issued_at_epoch + 2)
                finally:
                    pass
            raise

        final_state = self.executor.inspect_state()
        if final_state.get("running") is not True or final_state.get("paused") is not False:
            raise Stage8Rejected("FINAL_STATE_INVALID", "container did not recover to running/unpaused")

        continuity = self.binder.bind(
            incident_export=records["incident_export"],
            hold_projection=records["hold_projection"],
            hold_gateway=records["hold_gateway"],
            hold_plan=records["hold_plan"],
            hold_receipt=hold_receipt,
            release_projection=records["release_projection"],
            release_gateway=records["release_gateway"],
            release_plan=records["release_plan"],
            release_receipt=release_receipt,
            final_state=final_state,
        )
        verification = self.binder.verify(continuity)

        body = {
            "schema_version": "1",
            "container_id": self.container_id,
            "configuration_digest": self.configuration_digest,
            "incident_id": records["incident_export"]["incident_id"],
            "initial_state_digest": digest(initial),
            "hold_execution_receipt_digest": hold_receipt["execution_receipt_digest"],
            "release_execution_receipt_digest": release_receipt["execution_receipt_digest"],
            "continuity_qualification_digest": continuity["continuity_qualification_digest"],
            "continuity_verification_pass": verification["verification_pass"],
            "final_state": final_state,
            "recovery_attempted": recovery_attempted,
            "qualified": True,
        }
        return {**body, "stage_8_qualification_digest": digest(body)}
