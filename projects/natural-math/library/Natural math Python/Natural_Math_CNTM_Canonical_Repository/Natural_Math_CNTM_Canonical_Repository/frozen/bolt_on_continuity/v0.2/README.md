# Bolt-On Continuity for Docker v0.2

## Stage 0 — Usable Product Contract

**Status:** Development contract only  
**Authoritative baseline:** commit `205bee21b279fa63aef510fb23854eab17d44eb7`  
**Frozen engine snapshot:** `frozen/bolt_on_continuity_v0_1`  
**Retained v0.1 development source:** `products/bolt_on_continuity_v0_1`

Stage 0 defines the first usable product built around the frozen v0.1 engine baseline. It does not copy, modify, or replace the frozen release and does not expand Docker command authority.

## Product

**Product name:** Bolt-On Continuity for Docker v0.2 — Local Operator Edition

The product is a removable local continuity monitor for one explicitly enrolled Linux Docker container. It preserves a deterministic incident history, explains bounded `NO_ACTION`, `HOLD`, and `RELEASE` decisions, supports offline replay and export, and keeps all native Docker execution behind the separately validated host-owned gateway.

The safe installation default is observation-only mode. Gateway execution and native Docker actions remain disabled until the operator separately enables the qualified approval-required flow.

## Intended user

The first qualified operator is an individual developer or small-service operator using a local Docker Engine or Docker Desktop Linux containers. The operator is technically capable of installing local software but should not need to understand internal receipt schemas or manually construct action requests.

## Stage 0 outputs

- `PRODUCT_CONTRACT.md` — product, user, problem, workflow, interface, lifecycle, and safety contract;
- `AUTHORITY_AND_CLAIM_BOUNDARY.md` — exact authority and prohibited claims;
- `REUSE_AND_QUALIFICATION_MATRIX.md` — v0.1 reuse candidates and newly required qualification;
- `STAGE_0_GATES.md` — advancement gates for implementation work;
- `tools/verify_stage_0.py` — deterministic structural verifier for this contract stage.

## Stage 0 does not

- execute Docker commands;
- observe a live Docker Engine;
- copy v0.1 implementation code;
- create an installer or service;
- expose a network listener;
- authorize production use;
- add Docker command authority.

## Verification

From the repository root:

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_stage_0.py
python .\tools\verify_all_frozen.py
git diff -- .\frozen
```

Required endings:

```text
BOLT-ON CONTINUITY V0.2 STAGE 0 VERIFICATION: PASS
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty.
