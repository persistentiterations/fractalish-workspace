# Bolt-On Continuity for Docker v0.2 — Stage 4

## Canonical Configuration and Validation

**Status:** Development stage  
**Stage 3 baseline:** qualified container discovery and explicit enrollment  
**Authority:** configuration data only

Stage 4 converts a qualified enrollment record into a canonical local product configuration. The configuration is deterministic, digest-bound, observation-only by default, and rejected if malformed, tampered, ambiguous, or authority-expanding.

Stage 4 does not start monitoring, install a service, activate the gateway, project an action, or execute Docker commands.

## Outputs

- canonical configuration builder;
- strict configuration validator;
- SHA-256 configuration digest;
- explicit retention and storage bounds;
- safe defaults with `observation_only = true` and `gateway_enabled = false`;
- Stage 4 tests and structural verifier.

## Verification

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_stage_4.py
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
BOLT-ON CONTINUITY V0.2 STAGE 4 VERIFICATION: PASS
OK
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty.
