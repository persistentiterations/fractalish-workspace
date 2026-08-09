# Stage 0 Advancement Gates — Bolt-On Continuity for Docker v0.2

Stage 0 is complete only when every gate below passes. Passing Stage 0 authorizes work on a clean v0.2 scaffold; it does not authorize live Docker operation or native action execution.

## Gate 1 — Isolated development location

- All Stage 0 files are under `products/bolt_on_continuity_v0_2`.
- No file under `frozen` is changed.
- No v0.1 development file is changed.
- The v0.2 directory contains no copied operational Python implementation from v0.1.

## Gate 2 — Authoritative baseline

The contract names commit:

```text
205bee21b279fa63aef510fb23854eab17d44eb7
```

and frozen snapshot:

```text
frozen/bolt_on_continuity_v0_1
```

as the immutable engine baseline.

## Gate 3 — Specific product and user

The contract defines:

- the Local Operator Edition product;
- one explicitly enrolled Linux Docker container;
- the individual developer or small-service operator as the first qualified user;
- the recurring incident reconstruction problem;
- explicit exclusions for enterprise fleets, remote daemons, Kubernetes, and autonomous production remediation.

## Gate 4 — Installation and configuration flow

The contract requires:

- prerequisite checking;
- local Docker detection without mutation;
- user container selection;
- full 64-character ID resolution and confirmation;
- explicit enrollment;
- canonical local configuration and digest;
- observation-only default;
- explicit gateway enablement;
- safe stop and uninstall.

## Gate 5 — Interface and reporting

The contract defines a bounded local CLI and requires reports to distinguish observation, decision, approval, gateway result, Docker result, and verified resulting state.

A projected action must never be represented as an executed action.

## Gate 6 — Reuse boundary

The reuse matrix:

- names each v0.1 reuse candidate;
- requires source or behavior equivalence proof;
- forbids blanket approval by copying;
- preserves all v0.1 adversarial rejections;
- separates engine reuse from new product-lifecycle qualification.

## Gate 7 — New qualification scope

The matrix covers at least:

- clean install and prerequisites;
- discovery and enrollment;
- configuration and safe defaults;
- CLI lifecycle;
- explanation, replay, and export;
- approval, denial, gateway enablement, and disablement;
- restart and duplicate prevention;
- subject replacement;
- receipt-store failure;
- retention and deletion choice;
- uninstall;
- non-author usability qualification.

## Gate 8 — Authority ceiling

The only possible native Docker command authority remains:

```text
docker inspect <full 64-character container ID>
docker pause <full 64-character container ID>
docker unpause <full 64-character container ID>
```

Stage 0 contains no executable Docker call and grants no authority to run even these commands.

The contract explicitly prohibits stop, kill, restart, remove, exec, run, create, network mutation, volume mutation, image mutation, arbitrary command text, shortened IDs, wildcard targets, and name-only authority.

## Gate 9 — Safety modes

- Observation-only is the mandatory installation default.
- Approval-required mode is explicit.
- No autonomous-action mode exists.
- Missing approval, disabled gateway, uncertainty, corruption, or ambiguity fails closed.

## Gate 10 — Claim boundary

The contract prohibits universal production readiness, autonomous remediation, prevention of all failures, root-cause guarantees, zero drift, perfect continuity, universal compatibility, production security certification, and arbitrary production-container authority.

## Gate 11 — Deterministic Stage 0 verifier

The Stage 0 verifier must:

- use only the Python standard library;
- verify required files and required contract markers;
- reject operational Docker subprocess calls in v0.2 Stage 0 Python files;
- reject files outside the intended Stage 0 structure when they contain copied operational modules;
- print exactly one final PASS or FAIL summary line;
- return a nonzero exit code on failure.

## Gate 12 — Repository verification

Run from the repository root:

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_stage_0.py
python .\tools\verify_all_frozen.py
git diff -- .\frozen
git status --short
```

Required endings:

```text
BOLT-ON CONTINUITY V0.2 STAGE 0 VERIFICATION: PASS
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty. Only reviewed Stage 0 files may be changed.

## Advancement authorization

After all gates pass, Stage 1 may create the clean v0.2 package scaffold and define the explicit import or vendoring boundary for qualified v0.1 engine components.

Stage 1 must not yet create a live installer, daemon, gateway execution path, or expanded Docker authority unless its own contract and gates explicitly qualify that work.
