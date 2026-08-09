# Authority and Claim Boundary — Bolt-On Continuity for Docker v0.2 Stage 0

## Authority principle

v0.2 improves usability around the frozen v0.1 engine. It does not expand native Docker command authority.

## Component separation

```text
Docker Engine / enrolled container
        |
        | bounded read-only evidence
        v
Observer
        |
        | canonical normalized evidence
        v
Decision and receipt core
        |
        | NO_ACTION / HOLD / RELEASE projection
        v
Operator approval boundary
        |
        | exact approved request only
        v
Host-owned validating gateway
        |
        | exact allowlisted native operation
        v
Docker Engine
```

The CLI and any report viewer are operator interfaces. They do not inherit gateway authority.

## Qualified native command ceiling

The maximum native Docker authority remains limited to:

```text
docker inspect <full 64-character container ID>
docker pause <full 64-character container ID>
docker unpause <full 64-character container ID>
```

No Stage 0 document grants permission to execute these commands. Later stages must preserve the v0.1 validation chain before execution is enabled.

## Prohibited authority

The product must not provide or construct authority for:

- `docker stop`;
- `docker kill`;
- `docker restart`;
- `docker rm`;
- `docker exec`;
- `docker run`;
- `docker create`;
- arbitrary `docker logs` arguments;
- network mutation;
- volume mutation;
- image mutation;
- Docker configuration mutation;
- wildcard, prefix, name-only, or user-entered command targets;
- shell text or arbitrary Docker arguments;
- remote daemon or public-network control.

## Interface authority

The local CLI may:

- guide installation and configuration;
- display eligible subjects;
- request explicit enrollment;
- start and stop product components;
- display status and incident records;
- explain and replay decisions;
- export verified incident packages;
- request gateway enablement or disablement;
- collect an approval or denial bound to one request digest.

The CLI must not:

- directly invoke pause or unpause;
- accept arbitrary Docker command text;
- convert a container name into execution authority;
- mark an action executed before resulting state is observed;
- silently approve an action;
- bypass gateway validation.

A read-only report viewer must not invoke the gateway or modify configuration.

## Mandatory fail-closed conditions

No native action may result from:

- observation-only mode;
- disabled gateway;
- missing explicit approval;
- malformed or unknown schema;
- unsupported contract version;
- missing or forbidden fields;
- wrong, shortened, name-only, or replaced container identity;
- stale or future evidence;
- expired request or approval;
- duplicate request;
- conflicting identifier reuse;
- receipt, configuration, request, approval, or export digest mismatch;
- unsupported action or current state;
- inaccessible validation evidence;
- ambiguous Docker state;
- receipt-store uncertainty;
- restart recovery uncertainty;
- missing local authorization;
- unsupported environment.

When safe execution cannot be proven under the exact contract, the gateway rejects and records the rejection.

## Bounded v0.2 claim target

After all future v0.2 qualification gates pass, evidence may support wording similar to:

> Bolt-On Continuity for Docker v0.2 provided a guided local operator workflow for one explicitly enrolled Linux Docker container in the qualified environments, preserved deterministic incident receipts, explained and replayed bounded decisions, exported verifiable incident packages, and retained host-owned approval and execution authority for the qualified pause and unpause operations.

Final wording must identify the tested versions, environments, modes, duration, and limitations.

## Unsupported claims

Do not claim:

- universal production readiness;
- autonomous remediation;
- autonomous approval;
- prevention of all incidents or failures;
- root-cause identification;
- no data loss;
- zero drift;
- perfect continuity;
- infallible reconstruction;
- universal Docker, Windows, Linux, cloud, or hardware compatibility;
- Kubernetes, Swarm, remote-daemon, or multi-host support;
- enterprise security certification;
- production-scale performance;
- commercially proven demand;
- authorization for arbitrary production containers.

## Drift wording

Unless a later frozen contract formally defines drift, measurement, populations, duration, exceptions, and replay evidence, use only bounded wording such as:

```text
divergence detection under the qualified contract
```
