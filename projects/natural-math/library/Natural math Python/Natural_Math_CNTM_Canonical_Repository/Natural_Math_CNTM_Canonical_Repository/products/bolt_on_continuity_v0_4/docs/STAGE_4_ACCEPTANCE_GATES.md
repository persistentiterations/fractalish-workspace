# Bolt-On Continuity v0.4 — Stage 4 Acceptance Gates

- G4.1: Every qualified Stage 3 file, the Stage 3 head, qualification record, and verifier manifest remain unchanged.
- G4.2: Only an exact, digest-valid `STAGE_3_ENROLLED` receipt is accepted.
- G4.3: Subject identity, Linux platform, observed state, and the complete Stage 3 authority map are validated.
- G4.4: Canonical configuration output is deterministic, sorted, compact, NaN-free, and newline terminated.
- G4.5: Observation-only, approval-required, gateway-disabled, autonomous-action-disabled defaults are immutable.
- G4.6: The symbolic vocabulary is exactly `NO_ACTION`, `HOLD`, `RELEASE` and grants no execution authority.
- G4.7: Storage paths, incident counts, receipt byte bounds, and retention modes fail closed outside declared limits.
- G4.8: Persistence, Docker contact, Docker mutation, container operations, installation, networking, recovery, publication, and production authority remain false.
- G4.9: Stage 4 source imports no subprocess, Docker SDK, socket, or filesystem-mutation capability.
- G4.10: All Stage 0 through Stage 4 tests and verifiers pass.
- G4.11: Two Stage 4 verifier runs produce identical qualification and manifest hashes.
- G4.12: A disposable operator-created container can be discovered, exactly confirmed, enrolled, converted to a Stage 4 configuration, and then removed.
- G4.13: All frozen release verifiers pass, `frozen/` remains unchanged, and the working tree is clean.
