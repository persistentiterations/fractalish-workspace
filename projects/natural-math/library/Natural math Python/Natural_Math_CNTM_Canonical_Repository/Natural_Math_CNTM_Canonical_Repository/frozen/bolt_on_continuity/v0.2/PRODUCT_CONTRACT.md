# Product Contract — Bolt-On Continuity for Docker v0.2 Stage 0

## Contract identifier

```text
BONACQUI_BOLT_ON_CONTINUITY_DOCKER_PRODUCT_CONTRACT_0_2_STAGE_0
```

## Product objective

Build a removable local operator product around the qualified v0.1 engine baseline for one explicitly enrolled Linux Docker container. The product must make installation, configuration, observation, explanation, replay, export, approval, disablement, and uninstall understandable to an operator without weakening deterministic receipts, bounded authority, replayability, auditability, or fail-closed safety.

## First user

The first qualified user is an individual developer or small-service operator who:

- runs one important local Linux container;
- can install a local command-line application;
- needs a reliable incident record and explanation;
- does not want to reconstruct recurring incidents from scattered Docker state, logs, timestamps, and remembered interventions;
- remains responsible for enabling, approving, denying, and disabling native action authority.

Enterprise fleets, Kubernetes operators, remote Docker daemons, public services, and unattended production remediation are outside the v0.2 user contract.

## User-facing product

The product must provide a guided local workflow that:

1. checks supported prerequisites;
2. detects the local Docker Engine without modifying it;
3. lists eligible local Linux containers for operator selection;
4. resolves the selected subject to its full 64-character immutable container ID;
5. displays the identity and requires explicit enrollment;
6. creates and validates a local configuration;
7. defaults to observation-only mode;
8. starts and stops the local observer safely;
9. displays current status and incident history;
10. explains each bounded decision in operator-readable language;
11. replays an incident without Docker access;
12. exports a self-contained, tamper-detectable incident package;
13. enables or disables the gateway only through an explicit operator-controlled flow;
14. supports uninstall without impairing the monitored container.

A human-readable container name may aid selection and reporting, but it is never action authority. Replacement under the same name is a different subject and requires explicit re-enrollment.

## Operating modes

### Observation-only mode

This is the mandatory installation default.

- observation and receipt creation may run;
- decisions may be calculated and explained;
- projected actions are recorded as recommendations only;
- the gateway is disabled;
- no native pause or unpause may occur.

### Approval-required mode

This mode may be enabled only after configuration validation and an operator-controlled gateway enablement step.

- `HOLD` and `RELEASE` remain projections until approved;
- approval must bind to one exact request digest and exact container ID;
- stale, duplicate, conflicting, malformed, or tampered approvals are rejected;
- denial produces a receipt and no native action;
- approval does not bypass independent gateway validation.

No autonomous-action mode is defined for v0.2.

## Installation and configuration contract

The supported installation flow must be explicit, reversible, and local. It must not silently:

- select a container;
- enable the gateway;
- enable native actions;
- broaden Docker permissions;
- alter the monitored container;
- install a public-network listener;
- retain secrets in exported incident packages.

Configuration must bind at least:

- product and schema versions;
- full container ID;
- optional display name;
- supported environment declaration;
- observation bounds;
- configured divergence rules;
- receipt-store location;
- retention choice;
- operating mode;
- gateway enabled or disabled state;
- configuration digest.

Invalid, incomplete, unsupported, or tampered configuration must fail closed before observation or execution authority is granted.

## Interface contract

The primary v0.2 interface is a local command-line application. A read-only local report viewer may be added later in v0.2, but it must not invoke the gateway or become an execution surface.

The planned command surface is bounded to operator lifecycle and reporting functions such as:

```text
install
configure
doctor
start
status
incidents
explain
replay
export
gateway enable
gateway disable
stop
uninstall
```

These are product commands, not arbitrary Docker command passthroughs.

Status and incident reporting must clearly distinguish:

- observed state;
- detected condition;
- projected decision;
- approval status;
- gateway validation result;
- Docker result;
- verified resulting state.

The interface must never present a projected `HOLD` or `RELEASE` as though Docker executed it.

## Incident report contract

Each report must include, when applicable:

- product, schema, observer, decision, and gateway versions;
- configured display name and exact full container ID;
- configuration digest;
- incident identifier and digest;
- first and last observation sequence;
- bounded evidence summary;
- explicit truncation disclosures;
- decision and reason codes;
- projected, suppressed, denied, approved, rejected, or executed action status;
- gateway and Docker result receipts;
- resulting observed state;
- receipt-chain verification result;
- replay result;
- export digest.

Reports and exports must exclude credentials, Docker socket references, arbitrary command text, and unbounded logs.

## Lifecycle contract

The product must eventually qualify:

- clean installation;
- prerequisite rejection;
- explicit enrollment and re-enrollment;
- configuration validation;
- observation-only startup;
- controlled gateway enablement and disablement;
- safe process restart;
- no duplicate action after restart;
- deterministic recovery;
- missing, stopped, replaced, or inaccessible container behavior;
- receipt-store corruption and write-failure behavior;
- explicit retention or deletion choice;
- uninstall without container impairment.

Product failure must not stop, kill, remove, restart, reconfigure, or corrupt the monitored container.

## Frozen-baseline rule

The frozen v0.1 snapshot is immutable. v0.2 development must occur only under `products/bolt_on_continuity_v0_2` or another explicitly approved new location.

Reuse of v0.1 components is permitted only after:

1. the component is named in the reuse matrix;
2. its source boundary is identified;
3. frozen-source equivalence or behavior-equivalence tests are defined;
4. changed wrappers cannot broaden its authority;
5. the new product lifecycle around it is independently qualified.

## Non-goals

- autonomous root-cause diagnosis;
- arbitrary remediation;
- autonomous action approval;
- Docker restart, stop, kill, remove, exec, run, create, network, volume, or image mutation;
- multi-container coordination;
- remote daemon operation;
- Kubernetes or Swarm;
- public-network operation;
- universal platform support;
- production security certification;
- enterprise identity or authentication;
- generalized policy scripting;
- zero-failure, zero-drift, or universal production-readiness claims.
