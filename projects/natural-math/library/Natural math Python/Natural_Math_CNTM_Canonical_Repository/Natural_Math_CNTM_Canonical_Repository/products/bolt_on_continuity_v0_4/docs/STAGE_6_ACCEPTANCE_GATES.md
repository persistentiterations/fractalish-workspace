# Bolt-On Continuity v0.4 — Stage 6 Acceptance Gates

- G6.1: Every qualified Stage 5 file, head, qualification record, and verifier manifest remains unchanged.
- G6.2: Incident and receipt schemas reject missing, extra, malformed, ambiguous, oversized, or noncanonical values.
- G6.3: Receipt sequences are strictly increasing and match incident sequence bounds.
- G6.4: Receipt digests and previous-digest links are recomputed and fail closed on alteration.
- G6.5: Listing order and limits are deterministic.
- G6.6: Explanation clearly separates observation, decision, projected action, and native-execution evidence.
- G6.7: Only `DOCKER_ACCEPTED` evidences native execution.
- G6.8: Replay uses supplied receipts only and is deterministic.
- G6.9: Export is canonical, digest-bound, deterministic, and remains in memory.
- G6.10: Docker, subprocess, filesystem, socket, network, gateway, approval, native-execution, service, thread, recovery, publication, and production authorities remain false.
- G6.11: All Stage 0 through Stage 6 tests and verifiers pass.
- G6.12: Two Stage 6 verifier runs produce identical qualification and manifest hashes.
- G6.13: All frozen release verifiers pass, `frozen/` remains unchanged, and the working tree is clean.
