# Bolt-On Continuity for Docker v0.1

## Stage 0 — Product Contract

**Status:** Development contract only  
**Operational Docker code:** Not present  
**Frozen technical foundation:** `frozen/bolt_on/v0.4`  
**Frozen release commit:** `0d6de321ccac75bf8d634663396a0a4279b72261`

This product track is separate from the frozen Bolt-On Demonstrator releases.

Stage 0 defines:

- the first customer problem;
- the supported environment;
- the authority boundary;
- the evidence, action-request, gateway-decision, and receipt schemas;
- the product claim boundary;
- deterministic serialization rules;
- failure behavior;
- advancement gates for Stage 1.

Stage 0 does not observe Docker, connect to Docker, pause a container, unpause a
container, execute a command, install a service, or expose a network listener.

## Product

**Product name:** Bolt-On Continuity for Docker v0.1

**Customer problem:** Operators of a local containerized service often reconstruct
recurring incidents manually from scattered container status, events, logs, and
remembered interventions. The product will preserve a deterministic incident
record and may later project a bounded `HOLD` or `RELEASE` request while Docker
and a separate host-owned gateway retain execution authority.

## Supported v0.1 target

- one local Docker Engine;
- one explicitly configured Linux container;
- Docker Desktop with Linux containers or a native Linux Docker Engine;
- local deployment only;
- one configured container identity at a time;
- no Kubernetes, Swarm, remote daemon, multi-host, or public-network support;
- no Windows-container compatibility claim;
- no production-readiness claim.

## Portable actions

```text
HOLD
RELEASE
```

Planned native mapping:

```text
HOLD    -> Docker pause
RELEASE -> Docker unpause
```

The mapping is contractual only in Stage 0. No executable mapping exists yet.

## Authority rule

The bolt-on may observe, normalize, reason, create receipts, and project a
bounded request. It must not directly execute Docker operations.

Only a separately packaged host-owned gateway may later validate and submit the
exact allowlisted native operation. Docker remains the final execution authority.

## Stage 0 verification

From the repository root:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\verify_stage_0.py
```

Expected ending:

```text
STAGE 0 PRODUCT CONTRACT VERIFICATION: PASS
```

Run the tests:

```powershell
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_1\tests `
  -p "test_*.py" `
  -v
```

Expected ending:

```text
Ran 12 tests

OK
```

Verify all frozen releases:

```powershell
python .\tools\verify_all_frozen.py
```

Required final line:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

Do not commit until all outputs and `git status --short` have been reviewed.
