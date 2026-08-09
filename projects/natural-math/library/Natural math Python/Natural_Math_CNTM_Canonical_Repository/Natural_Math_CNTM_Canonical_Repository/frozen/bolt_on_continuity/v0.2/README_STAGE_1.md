# Bolt-On Continuity for Docker v0.2 — Stage 1

## Clean Product Scaffold and Engine Boundary

**Status:** Development stage  
**Stage 0 baseline branch:** `agent/docker-continuity-v0.2-stage-0`  
**Authoritative frozen engine:** `frozen/bolt_on_continuity_v0_1`  
**Authoritative release commit:** `205bee21b279fa63aef510fb23854eab17d44eb7`

Stage 1 creates a separate v0.2 Python product scaffold and a machine-readable boundary describing which frozen v0.1 components may later be considered for reuse.

Stage 1 does not import, copy, execute, or modify the v0.1 operational engine. It does not connect to Docker and does not authorize `inspect`, `pause`, or `unpause`.

## Stage 1 outputs

- isolated package namespace `bolt_on_continuity_v0_2`;
- package metadata with no third-party runtime dependencies;
- frozen-engine boundary manifest with exact source paths and SHA-256 digests;
- boundary loader that validates data only and imports no operational engine code;
- scaffold tests;
- Stage 1 structural verifier;
- advancement contract for Stage 2.

## Verification

From the repository root:

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_stage_1.py
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_2\tests `
  -p "test_*.py" `
  -v
python .\tools\verify_all_frozen.py
git diff -- .\frozen
git status --short
```

Required endings:

```text
BOLT-ON CONTINUITY V0.2 STAGE 1 VERIFICATION: PASS
OK
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty.
