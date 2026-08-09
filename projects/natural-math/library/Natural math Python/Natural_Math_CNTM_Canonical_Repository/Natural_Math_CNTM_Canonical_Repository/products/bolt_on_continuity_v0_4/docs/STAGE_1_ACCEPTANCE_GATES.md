# Bolt-On Continuity v0.4 — Stage 1 Acceptance Gates

- G1.1: The Stage 0 qualification record and Stage 0 verifier manifest remain bound to their qualified SHA-256 values.
- G1.2: A qualified Windows or Linux snapshot with Python 3.11 or newer produces `STAGE_1_READY`.
- G1.3: Python below 3.11 produces `NOT_READY`.
- G1.4: Docker CLI absence produces `WARN`, not `FAIL`.
- G1.5: Docker CLI discovery uses `PATH` inspection only and never executes Docker.
- G1.6: Windows and Linux recommended data paths are deterministic.
- G1.7: Canonical JSON contains no timestamp and never serializes the complete environment mapping.
- G1.8: Every operational and release authority remains false.
- G1.9: The Stage 1 verifier contains no subprocess, socket, Docker SDK, installation, filesystem-write, or mutation authority.
- G1.10: All Stage 0 and Stage 1 tests pass.
- G1.11: Two Stage 1 verifier runs produce identical qualification and manifest hashes.
- G1.12: All frozen release verifiers pass and `frozen/` remains unchanged.
