#!/usr/bin/env python3
"""Deterministic live sidecar lifecycle registry for Bolt-On v0.4 Stage 5.

This module owns only sidecar installation metadata and lifecycle receipts.
It never imports the host, adapter, projector, or gateway and exposes no host
command path. All operations are exact, append-only, replayable, and recoverable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Iterable, Mapping, Sequence, Tuple

LIFECYCLE_ID = "V04-LIVE-SIDECAR-LIFECYCLE"
LIFECYCLE_VERSION = "1.0"
EXECUTION_AUTHORITY = "NONE"
INSTALLATION_MODE = "SIDECAR_REGISTRY"
ZERO_DIGEST = "0" * 64

OBSERVATION = "OBSERVATION"
PROJECTION = "PROJECTION"
GATEWAY_BINDING = "GATEWAY_BINDING"
ALLOWED_KINDS = (OBSERVATION, PROJECTION, GATEWAY_BINDING)

INSTALL = "INSTALL"
ACTIVATE = "ACTIVATE"
DEACTIVATE = "DEACTIVATE"
REMOVE = "REMOVE"
RECOVER = "RECOVER"
ALLOWED_EVENTS = (INSTALL, ACTIVATE, DEACTIVATE, REMOVE, RECOVER)

INSTALLED = "INSTALLED"
ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
REMOVED = "REMOVED"
FAILED = "FAILED"
ALLOWED_STATES = (INSTALLED, ACTIVE, INACTIVE, REMOVED, FAILED)

class LifecycleRejected(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason

def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()

def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)

def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LifecycleRejected(f"{name.upper()}_INVALID")
    return value.strip()

def _int(value: object, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LifecycleRejected(f"{name.upper()}_TYPE_INVALID")
    if value < minimum:
        raise LifecycleRejected(f"{name.upper()}_RANGE_INVALID")
    return value

@dataclass(frozen=True)
class SidecarPackage:
    package_id: str
    package_version: str
    kind: str
    source_digest: str
    capabilities: Tuple[str, ...]
    execution_authority: str
    package_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "capabilities": list(self.capabilities),
            "execution_authority": self.execution_authority,
            "kind": self.kind,
            "package_id": self.package_id,
            "package_version": self.package_version,
            "source_digest": self.source_digest,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "package_digest": self.package_digest}

@dataclass(frozen=True)
class InstalledSidecar:
    package_id: str
    package_digest: str
    kind: str
    state: str
    generation: int
    failure_code: str
    entry_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "failure_code": self.failure_code,
            "generation": self.generation,
            "kind": self.kind,
            "package_digest": self.package_digest,
            "package_id": self.package_id,
            "state": self.state,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "entry_digest": self.entry_digest}

@dataclass(frozen=True)
class LifecycleReceipt:
    sequence: int
    event: str
    package_id: str
    before_state: str
    after_state: str
    accepted: bool
    reason: str
    generation: int
    registry_digest: str
    previous_digest: str
    receipt_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "after_state": self.after_state,
            "before_state": self.before_state,
            "event": self.event,
            "generation": self.generation,
            "package_id": self.package_id,
            "previous_digest": self.previous_digest,
            "reason": self.reason,
            "registry_digest": self.registry_digest,
            "sequence": self.sequence,
        }

    def record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "receipt_digest": self.receipt_digest}

@dataclass(frozen=True)
class LifecycleRegistry:
    registry_id: str
    entries: Tuple[InstalledSidecar, ...]
    receipts: Tuple[LifecycleReceipt, ...]
    registry_digest: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "entries": [entry.record() for entry in self.entries],
            "receipts": [receipt.record() for receipt in self.receipts],
            "registry_id": self.registry_id,
        }

@dataclass(frozen=True)
class ReplayResult:
    passed: bool
    reason: str
    receipt_count: int
    final_digest: str
    registry_digest: str

def build_package(
    package_id: str,
    package_version: str,
    kind: str,
    source_digest: str,
    capabilities: Iterable[str],
) -> SidecarPackage:
    package_id = _text(package_id, "package_id")
    package_version = _text(package_version, "package_version")
    kind = _text(kind, "kind").upper()
    if kind not in ALLOWED_KINDS:
        raise LifecycleRejected("KIND_INVALID")
    if not _is_digest(source_digest):
        raise LifecycleRejected("SOURCE_DIGEST_INVALID")
    rows = tuple(sorted({_text(v, "capability").upper() for v in tuple(capabilities)}))
    if not rows:
        raise LifecycleRejected("CAPABILITIES_EMPTY")
    unsigned = {
        "capabilities": list(rows),
        "execution_authority": EXECUTION_AUTHORITY,
        "kind": kind,
        "package_id": package_id,
        "package_version": package_version,
        "source_digest": source_digest,
    }
    return SidecarPackage(
        package_id, package_version, kind, source_digest, rows,
        EXECUTION_AUTHORITY, _digest(unsigned)
    )

def empty_registry() -> LifecycleRegistry:
    unsigned = {"entries": [], "receipts": [], "registry_id": LIFECYCLE_ID}
    return LifecycleRegistry(LIFECYCLE_ID, (), (), _digest(unsigned))

def _entry(package: SidecarPackage, state: str, generation: int, failure_code: str = "") -> InstalledSidecar:
    unsigned = {
        "failure_code": failure_code,
        "generation": generation,
        "kind": package.kind,
        "package_digest": package.package_digest,
        "package_id": package.package_id,
        "state": state,
    }
    return InstalledSidecar(
        package.package_id, package.package_digest, package.kind, state,
        generation, failure_code, _digest(unsigned)
    )

def _registry_digest(entries: Sequence[InstalledSidecar], receipts: Sequence[LifecycleReceipt]) -> str:
    return _digest({
        "entries": [e.record() for e in entries],
        "receipts": [r.record() for r in receipts],
        "registry_id": LIFECYCLE_ID,
    })

def _append(
    registry: LifecycleRegistry,
    event: str,
    package_id: str,
    before_state: str,
    after_state: str,
    accepted: bool,
    reason: str,
    generation: int,
    entries: Sequence[InstalledSidecar],
) -> LifecycleRegistry:
    interim_digest = _digest([e.record() for e in entries])
    unsigned = {
        "accepted": accepted,
        "after_state": after_state,
        "before_state": before_state,
        "event": event,
        "generation": generation,
        "package_id": package_id,
        "previous_digest": registry.receipts[-1].receipt_digest if registry.receipts else ZERO_DIGEST,
        "reason": reason,
        "registry_digest": interim_digest,
        "sequence": len(registry.receipts) + 1,
    }
    receipt = LifecycleReceipt(
        unsigned["sequence"], event, package_id, before_state, after_state,
        accepted, reason, generation, interim_digest,
        unsigned["previous_digest"], _digest(unsigned)
    )
    receipts = registry.receipts + (receipt,)
    entries = tuple(sorted(entries, key=lambda x: x.package_id))
    return LifecycleRegistry(LIFECYCLE_ID, entries, receipts, _registry_digest(entries, receipts))

def _find(registry: LifecycleRegistry, package_id: str) -> tuple[int, InstalledSidecar | None]:
    for i, entry in enumerate(registry.entries):
        if entry.package_id == package_id:
            return i, entry
    return -1, None

def apply_event(
    registry: LifecycleRegistry,
    event: str,
    package: SidecarPackage,
    *,
    failure_code: str = "",
) -> LifecycleRegistry:
    if not isinstance(registry, LifecycleRegistry):
        raise LifecycleRejected("REGISTRY_TYPE_INVALID")
    valid, reason = validate_package(package)
    if not valid:
        return _append(registry, event, getattr(package, "package_id", "UNKNOWN"), "ABSENT", "ABSENT", False, reason, 0, registry.entries)
    event = _text(event, "event").upper()
    if event not in ALLOWED_EVENTS:
        return _append(registry, event, package.package_id, "ABSENT", "ABSENT", False, "EVENT_INVALID", 0, registry.entries)
    idx, current = _find(registry, package.package_id)
    before = current.state if current else "ABSENT"
    generation = (current.generation + 1) if current else 1
    entries = list(registry.entries)

    if event == INSTALL:
        if current and current.state != REMOVED:
            return _append(registry, event, package.package_id, before, before, False, "ALREADY_INSTALLED", current.generation, entries)
        new = _entry(package, INSTALLED, generation)
        if idx >= 0: entries[idx] = new
        else: entries.append(new)
        return _append(registry, event, package.package_id, before, INSTALLED, True, "APPLIED", generation, entries)

    if current is None or current.package_digest != package.package_digest:
        return _append(registry, event, package.package_id, before, before, False, "PACKAGE_NOT_INSTALLED", 0 if current is None else current.generation, entries)

    if event == ACTIVATE:
        if current.state not in (INSTALLED, INACTIVE):
            return _append(registry, event, package.package_id, before, before, False, "INVALID_STATE", current.generation, entries)
        new = _entry(package, ACTIVE, generation)
    elif event == DEACTIVATE:
        if current.state != ACTIVE:
            return _append(registry, event, package.package_id, before, before, False, "INVALID_STATE", current.generation, entries)
        new = _entry(package, INACTIVE, generation)
    elif event == REMOVE:
        if current.state not in (INSTALLED, INACTIVE):
            return _append(registry, event, package.package_id, before, before, False, "INVALID_STATE", current.generation, entries)
        new = _entry(package, REMOVED, generation)
    else:  # RECOVER
        failure_code = _text(failure_code, "failure_code")
        if current.state == ACTIVE:
            failed = _entry(package, FAILED, generation, failure_code)
            entries[idx] = failed
            failed_registry = _append(registry, event, package.package_id, before, FAILED, True, failure_code, generation, entries)
            recovered = _entry(package, INACTIVE, generation + 1)
            entries[idx] = recovered
            return _append(failed_registry, RECOVER, package.package_id, FAILED, INACTIVE, True, "RECOVERED", generation + 1, entries)
        if current.state == FAILED:
            new = _entry(package, INACTIVE, generation)
        else:
            return _append(registry, event, package.package_id, before, before, False, "INVALID_STATE", current.generation, entries)

    entries[idx] = new
    return _append(registry, event, package.package_id, before, new.state, True, "APPLIED", new.generation, entries)

def validate_package(package: object) -> tuple[bool, str]:
    if not isinstance(package, SidecarPackage):
        return False, "PACKAGE_TYPE_INVALID"
    try:
        _text(package.package_id, "package_id")
        _text(package.package_version, "package_version")
        if package.kind not in ALLOWED_KINDS:
            return False, "KIND_INVALID"
        if package.execution_authority != EXECUTION_AUTHORITY:
            return False, "EXECUTION_AUTHORITY_INVALID"
        if not _is_digest(package.source_digest):
            return False, "SOURCE_DIGEST_INVALID"
        if tuple(sorted(set(package.capabilities))) != package.capabilities or not package.capabilities:
            return False, "CAPABILITIES_INVALID"
        if not _is_digest(package.package_digest) or _digest(package.unsigned_record()) != package.package_digest:
            return False, "PACKAGE_DIGEST_MISMATCH"
    except (TypeError, LifecycleRejected):
        return False, "PACKAGE_FIELDS_INVALID"
    return True, "VALID"

def replay_registry(registry: object) -> ReplayResult:
    if not isinstance(registry, LifecycleRegistry):
        return ReplayResult(False, "REGISTRY_TYPE_INVALID", 0, ZERO_DIGEST, ZERO_DIGEST)
    previous = ZERO_DIGEST
    for i, receipt in enumerate(registry.receipts, 1):
        if receipt.sequence != i:
            return ReplayResult(False, "SEQUENCE_MISMATCH", i-1, previous, ZERO_DIGEST)
        if receipt.previous_digest != previous:
            return ReplayResult(False, "CHAIN_MISMATCH", i-1, previous, ZERO_DIGEST)
        if _digest(receipt.unsigned_record()) != receipt.receipt_digest:
            return ReplayResult(False, "RECEIPT_DIGEST_MISMATCH", i-1, previous, ZERO_DIGEST)
        previous = receipt.receipt_digest
    for entry in registry.entries:
        if entry.state not in ALLOWED_STATES or _digest(entry.unsigned_record()) != entry.entry_digest:
            return ReplayResult(False, "ENTRY_INVALID", len(registry.receipts), previous, ZERO_DIGEST)
    expected = _registry_digest(registry.entries, registry.receipts)
    if expected != registry.registry_digest:
        return ReplayResult(False, "REGISTRY_DIGEST_MISMATCH", len(registry.receipts), previous, expected)
    return ReplayResult(True, "PASS", len(registry.receipts), previous, expected)

def build_reference_packages() -> tuple[SidecarPackage, ...]:
    return (
        build_package("READ-ONLY-OBSERVER", "1.0", OBSERVATION, hashlib.sha256(b"observer").hexdigest(), ("OBSERVE", "NORMALISE", "REPLAY")),
        build_package("BOUNDED-PROJECTOR", "1.0", PROJECTION, hashlib.sha256(b"projector").hexdigest(), ("PROJECT_HOLD", "PROJECT_RELEASE")),
        build_package("HOST-GATEWAY-BINDING", "1.0", GATEWAY_BINDING, hashlib.sha256(b"gateway").hexdigest(), ("BIND_ONLY",)),
    )

def run_reference_lifecycle() -> LifecycleRegistry:
    registry = empty_registry()
    packages = build_reference_packages()
    for package in packages:
        registry = apply_event(registry, INSTALL, package)
    for package in packages:
        registry = apply_event(registry, ACTIVATE, package)
    registry = apply_event(registry, RECOVER, packages[0], failure_code="OBSERVER_STREAM_INTERRUPTED")
    registry = apply_event(registry, ACTIVATE, packages[0])
    for package in reversed(packages):
        registry = apply_event(registry, DEACTIVATE, package)
    for package in reversed(packages):
        registry = apply_event(registry, REMOVE, package)
    return registry

if __name__ == "__main__":
    result = run_reference_lifecycle()
    replay = replay_registry(result)
    removed = sum(1 for entry in result.entries if entry.state == REMOVED)
    print(f"Lifecycle: {LIFECYCLE_ID} {LIFECYCLE_VERSION}")
    print(f"Execution authority: {EXECUTION_AUTHORITY}")
    print(f"Packages: {len(result.entries)}")
    print(f"Lifecycle receipts: {len(result.receipts)}")
    print(f"Removed packages: {removed}")
    print(f"Registry digest: {result.registry_digest}")
    print(f"Replay digest: {replay.registry_digest}")
    print("LIVE SIDECAR LIFECYCLE SELF-CHECK: PASS" if replay.passed and removed == 3 else "LIVE SIDECAR LIFECYCLE SELF-CHECK: FAIL")
