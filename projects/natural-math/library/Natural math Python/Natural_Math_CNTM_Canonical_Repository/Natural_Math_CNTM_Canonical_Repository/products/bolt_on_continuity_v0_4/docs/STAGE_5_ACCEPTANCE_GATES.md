# Bolt-On Continuity v0.4 — Stage 5 Acceptance Gates

- G5.1: Every qualified Stage 4 file, Stage 4 head, qualification record, and verifier manifest remain unchanged.
- G5.2: Only exact Stage 4 canonical configuration input is accepted; malformed, altered, extra-field, digest-invalid, or authority-expanded input fails closed.
- G5.3: Commands are exactly `config-check`, `status`, `start`, and `stop`.
- G5.4: Lifecycle states are exactly `NOT_STARTED`, `OBSERVATION_PLAN_READY`, and `STOP_PLAN_READY`.
- G5.5: Every result states that execution was not performed and the container was not mutated.
- G5.6: Start and stop create plans only; they do not contact Docker or manipulate a runtime.
- G5.7: Accepted and rejected outputs are canonical and deterministically digested.
- G5.8: No subprocess, Docker SDK, socket, filesystem mutation, persistence, installer, service, thread, recovery, gateway, publication, or production authority exists.
- G5.9: All Stage 0 through Stage 5 tests and verifiers pass.
- G5.10: Two Stage 5 verifier runs produce identical qualification and manifest hashes.
- G5.11: Live CLI checks consume a Stage 4 configuration and return all four bounded results without Docker contact.
- G5.12: All frozen release verifiers pass, `frozen/` remains unchanged, and the working tree is clean.
