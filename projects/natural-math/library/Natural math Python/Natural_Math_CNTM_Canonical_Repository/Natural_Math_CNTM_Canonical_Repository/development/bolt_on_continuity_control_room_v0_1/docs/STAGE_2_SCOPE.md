# Bolt-On Continuity Control Room v0.1 — Stage 2 Scope Contract

## Purpose

Stage 2 may add one bounded continuity claim: retain two or more explicit,
read-only observations of exactly one operator-selected Docker container and
deterministically classify whether all retained observations carry the same full
Docker container ID.

This document defines Stage 2 only. It does not implement retention, comparison,
Docker observation, or presentation behavior.

## Foundation and ancestry

- Controlling branch: `agent/bolt-on-continuity-control-room-v0.1`
- Required Stage 1 commit: `51dffe72c43a2c5f98c20cc9d9ea4ae1b336f225`
- Required Stage 1 observation schema:
  `bolt-on-continuity-control-room-observation/v1`
- Required Stage 1 receipt schema:
  `bolt-on-continuity-control-room-receipt/v1`
- Immutable tree: `frozen/`

The Stage 2 branch head must descend from the exact qualified Stage 1 commit.
Stage 1 observation, receipt, and read-only Docker boundaries remain authoritative
and must not be weakened or bypassed.

## Authorized workflow

Stage 2 implementation may perform only this foreground, operator-initiated
workflow:

1. Accept exactly one operator-entered container name or ID as the observation
   selector.
2. Make two or more explicit calls through the existing
   `ContainerObserver.inspect_one(subject)` interface.
3. Build a Stage 1 canonical observation and Stage 1 deterministic receipt for
   each successful call.
4. Retain the resulting records locally in deterministic observation order.
5. Compare only the full observed `container_id` values.
6. Emit one bounded classification and one deterministic comparison receipt.
7. Expose the ordered evidence and its provenance without implying an incident,
   replacement, duplicate, recovery, or operator decision.

There is no automatic polling, timer, scheduler, watcher, daemon, or background
capture loop. Each observation is caused by an explicit foreground request.

## Retained-observation record format

The local retained document must use schema
`bolt-on-continuity-control-room-retained-observations/v1` and contain:

- the operator-entered subject selector, labeled **operator-entered**;
- an `observations` array with at least two entries; and
- no container data that is not present in the referenced Stage 1 records.

Each retained entry must contain exactly:

- `observation_index`: a positive integer assigned at successful retention;
- `observation_schema`: the Stage 1 observation schema;
- `observation_receipt_id`: the complete Stage 1 receipt ID;
- `container_id`: the full observed Docker container ID, without truncation;
- `observed_at`: the Stage 1 external event timestamp; and
- `source_interface`: the Stage 1 observation source interface.

The retained document is local evidence, not an installed database or service.
Its persistence mechanism must be an explicit foreground operation. Stage 2 may
write only its own operator-selected local evidence destination and must not
write to `frozen/`, Docker, the observed container, or host service state.

## Deterministic observation ordering

Ordering is defined only by `observation_index`, ascending. The first retained
success is index 1, the next is index 2, with no duplicate, zero, negative, or
missing index. Input array order and timestamps do not override this rule.

Comparison must reject duplicate or non-contiguous indices as
`INDETERMINATE`. Timestamps remain retained external event metadata; they are
not the ordering authority and are excluded from deterministic digest inputs.

## Identity evidence and classification

The full Docker `Id` captured as Stage 1 `container_id` is the only authorized
identity comparison field. Container name, configured or resolved image, state,
running flag, creation time, start time, operator selector, and observation time
must not influence identity classification.

The finite Stage 2 classification set is:

- `SAME_SUBJECT`: at least two valid, deterministically ordered observations are
  present, every full `container_id` is available, and every value is exactly
  equal; or
- `INDETERMINATE`: evidence is missing, invalid, unordered, unverifiable, or the
  full IDs differ.

`INDETERMINATE` is fail-closed and must include one bounded reason such as
`insufficient_observations`, `invalid_order`, `missing_identity`,
`unverified_observation_receipt`, or `identity_mismatch_out_of_scope`.

A differing ID does not authorize or imply `REPLACED`, `DUPLICATE`, incident,
recovery, cause, continuity loss, or any container action.

## Comparison receipt

The deterministic comparison receipt must use schema
`bolt-on-continuity-control-room-comparison-receipt/v1`. Its digest input must
contain only:

- the comparison receipt schema;
- the retained-observation schema;
- the subject selector;
- an array ordered by `observation_index`, each entry containing only
  `observation_index`, full `container_id`, and `observation_receipt_id`;
- the classification; and
- the bounded reason, or `null` for `SAME_SUBJECT`.

The digest is SHA-256 over UTF-8 JSON with sorted keys, fixed compact separators,
and no timestamp. Reordering source records before canonical ordering must not
change the receipt. Changing an index, full container ID, observation receipt
ID, classification, or reason must change it.

## Evidence provenance

Presentation must keep these categories visibly separate:

- **observed**: Docker fields captured by each Stage 1 observation;
- **retained**: observation index, observation time, Stage 1 receipt ID, and the
  local ordered record;
- **derived**: record count, ordering validity, and exact-ID equality predicate;
- **classification**: `SAME_SUBJECT` or `INDETERMINATE` with bounded reason;
- **operator-entered**: the one container selector and optional local evidence
  destination; and
- **unavailable**: any absent source value, without substitution.

Every identity input must trace to a valid Stage 1 observation receipt. A record
with an unverifiable or mismatched Stage 1 receipt must not support
`SAME_SUBJECT`.

## Live qualification boundary

One explicit live-Docker qualification path must:

1. use one harmless operator-created container that remains present throughout
   capture;
2. make at least two foreground read-only `docker inspect --type container`
   observations through the existing adapter;
3. retain and order both Stage 1 records;
4. verify both Stage 1 receipts;
5. confirm both full observed IDs equal Docker's real full ID;
6. produce `SAME_SUBJECT` and a replay-identical comparison receipt; and
7. compare pre- and post-qualification identity, start time, restart count, and
   running state to confirm Bolt-On performed no mutation.

The operator owns container creation and later cleanup. Qualification must not
stop or remove the container before evidence capture completes.

## Explicit exclusions

Stage 2 must not add or perform:

- container create, start, stop, restart, pause, unpause, kill, rename, remove,
  delete, replace, exec, copy, update, or network mutation;
- automatic polling, background service, watcher, scheduler, or host service
  registration;
- replacement or duplicate detection or classification;
- incident, failure, recovery, remediation, or causality classification;
- operator approve, deny, hold, release, or recovery controls;
- comparison across multiple selected containers;
- identity inference from name, image, timestamps, or state;
- installation, packaging, publication, distribution, production-readiness,
  universal-compatibility, or security-certification claims; or
- any modification under `frozen/`.

## Scope-definition acceptance gates

This Stage 2 definition is qualified only when:

1. the controlling branch is exact and descends from the qualified Stage 1
   commit;
2. this contract defines the record schema, deterministic ordering, finite
   classifications, comparison receipt, provenance, live path, and exclusions;
3. scope-only tests and the independent Stage 2 scope verifier pass;
4. no Stage 2 retention, comparison, Docker, or presentation product module has
   been added;
5. all aggregate frozen-release verification passes;
6. `git diff -- frozen` is empty; and
7. the committed working tree is clean.

## Later implementation acceptance gates

Stage 2 product implementation may begin only after the scope-definition gates
pass. It is qualified only when:

1. deterministic unit tests cover valid ordering, source reordering, duplicate
   and missing indices, insufficient records, missing IDs, differing IDs,
   receipt verification, digest replay, and digest sensitivity;
2. source inspection proves Docker authority remains limited to the existing
   exact read-only inspect call;
3. the Docker-required live qualification path passes with at least two real
   observations and no skipped test;
4. all Control Room tests and the Stage 2 verifier pass;
5. all aggregate frozen-release verification passes;
6. the `frozen/` tree is unchanged; and
7. only intended Stage 2 files are committed and the working tree is clean.

Passing Stage 2 would prove only same-full-ID continuity across a bounded set of
retained observations of one real container. It would not prove replacement or
duplicate detection, incident understanding, recovery correctness, autonomous
operation, persistence durability, security, or production readiness.
