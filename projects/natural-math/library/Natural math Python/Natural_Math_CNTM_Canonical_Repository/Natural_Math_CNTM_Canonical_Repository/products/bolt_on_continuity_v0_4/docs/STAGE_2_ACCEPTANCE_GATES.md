# Bolt-On Continuity v0.4 — Stage 2 Acceptance Gates

- G2.1: The qualified Stage 1 head, qualification record, verifier manifest, and seven-file Stage 1 authority set remain unchanged.
- G2.2: Only the fixed context, version, and information vectors are executable.
- G2.3: Remote Docker environment overrides prevent every Docker subprocess from running.
- G2.4: Context inspection occurs first; version and information probes run only for a local `npipe://` or `unix://` endpoint.
- G2.5: Every subprocess uses a direct argument list, `shell=False`, a five-second timeout, `capture_output=True`, `text=True`, and `check=False`.
- G2.6: Missing, timed-out, malformed, nonzero, remote, ambiguous, and non-Linux evidence fails closed.
- G2.7: Canonical receipts omit executable paths, environment values, endpoint addresses, root directories, stderr, timestamps, and Docker object data.
- G2.8: Only `docker_prerequisite_probe` and `local_docker_daemon_contact` are true; every mutation, inspection, installation, publication, distribution, recovery, and production authority remains false.
- G2.9: All Stage 0, Stage 1, and Stage 2 tests pass.
- G2.10: Two Stage 2 verifier runs produce identical qualification and manifest hashes.
- G2.11: The real prerequisite probe produces `STAGE_2_ELIGIBLE` only for a qualifying local Linux Docker engine.
- G2.12: All frozen release verifiers pass, `frozen/` remains unchanged, and the working tree is clean.
