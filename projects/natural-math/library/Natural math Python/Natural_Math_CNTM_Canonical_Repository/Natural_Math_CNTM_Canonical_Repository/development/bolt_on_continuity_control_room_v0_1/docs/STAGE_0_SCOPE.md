# Bolt-On Continuity Control Room v0.1 — Stage 0 Scope Contract

## Purpose

Stage 0 establishes the repository, evidence, authority, and claim boundaries for the first real Control Room vertical slice. Stage 0 is documentation and qualification only. It does not implement or launch the application or a container.

## Foundation binding

- Development branch: `agent/bolt-on-continuity-control-room-v0.1`
- Required foundation tag: `bolt-on-continuity-v0.4`
- Required foundation commit: `4cc817441d3447e54303550090eaf8b95c451a83`
- Development location: `development/bolt_on_continuity_control_room_v0_1`
- Immutable destination: `frozen/bolt_on_continuity/v0.4`

The branch must descend from the exact foundation commit. No file under `frozen/` may change.

## Stage 1 authorized vertical slice

The next stage may implement only this workflow:

1. Launch one harmless Docker demonstration container by an explicit local operator command.
2. Observe that container using Docker's real read-only inspection interface.
3. Show its live identity and status in a local web page.
4. Capture one observation record and generate one deterministic receipt from canonicalized source fields.
5. Label displayed values as observed, derived, retained, or operator-entered.

The page must show, when Docker provides them:

- container name;
- full container ID;
- image identity;
- running or stopped status;
- creation and start information;
- observer connection status;
- latest observation time;
- receipt identifier; and
- observation source interface or command.

Unavailable information must be labeled unavailable. No value may be fabricated, pre-scripted, or animated as though an unobserved event occurred.

## Evidence contract

Every displayed container fact must trace to a captured observation record. The receipt must include:

- receipt schema/version;
- observation subject;
- observation source;
- raw or canonicalized source fields;
- observation result; and
- deterministic SHA-256 receipt digest.

The digest input must use deterministic serialization. Observation time is retained as external event metadata and excluded from the deterministic digest unless a later contract explicitly binds it as source event data.

## Observed versus classified

Docker-source values are **observed facts**. Bolt-On interpretations are **classifications** and must be visibly separate. Retention state and operator-entered values must also be visibly labeled. A classification must cite the observed fields that support it.

## Explicit exclusions

Stage 0 and the Stage 1 authorization exclude:

- container stop, restart, pause, unpause, kill, rename, remove, or replacement;
- container creation by the observer or web application;
- Docker write APIs or commands from the observer or web application;
- recovery classification or automatic remediation;
- operator approve, deny, hold, release, or incident controls;
- background service installation or host-level registration;
- native installers, publication, distribution, or production-readiness claims;
- fake incidents, scripted status changes, or simulated telemetry; and
- observing the Bolt-On product itself as the demonstration subject.

## Stage 0 acceptance criteria

Stage 0 passes only when:

1. the current branch has the required name;
2. the required tag resolves to the required commit;
3. the branch descends from that commit;
4. the frozen manifest verifier passes;
5. this contract contains the authorized scope, evidence rules, and exclusions;
6. Stage 0 tests and the independent Stage 0 verifier pass; and
7. no product implementation, Docker invocation, web server, or container lifecycle action exists in the Stage 0 development tree.

Passing Stage 0 authorizes implementation of the bounded Stage 1 slice. It does not prove Docker availability, live observation, receipt correctness in the future application, portability, security, recovery, or production readiness.
