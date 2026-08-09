# Bolt-On Continuity v0.4 — Stage 0 Product Scope Contract

## Purpose

Stage 0 defines the first product-facing demonstrator without implementing installation, background services, native execution, container mutation, or publication.

## Product goal

An outside evaluator must eventually be able to run one bounded Docker-based demonstration, observe deterministic output, and inspect exact receipts without reconstructing the system by hand.

## Required v0.4 capabilities

1. One documented local launch path.
2. One bounded demonstration workflow.
3. Deterministic, replayable receipts.
4. Explicit observation-only behavior by default.
5. Clear success, hold, and failure output.
6. Qualification on a second machine before release consideration.

## Stage 0 acceptance criteria

Stage 0 passes only when the product goal, required capabilities, exclusions, evidence requirements, and authority limits are encoded deterministically and tested.

## Explicit exclusions

Stage 0 does not authorize or implement:

- installer execution;
- background observers or services;
- native gateways;
- Docker or host mutation;
- automatic recovery actions;
- uploaded binaries or packages;
- publication;
- production-readiness, universal-compatibility, zero-drift, or security-certification claims.

## Authority boundary

All operational and release authorities remain false. Later stages require separate qualification and explicit authorization.
