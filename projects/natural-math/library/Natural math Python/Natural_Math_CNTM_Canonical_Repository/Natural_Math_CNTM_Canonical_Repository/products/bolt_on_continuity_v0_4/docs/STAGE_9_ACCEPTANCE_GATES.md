# Bolt-On Continuity v0.4 — Stage 9 Acceptance Gates

Stage 9 passes only when:

1. The complete Stage 0–9 test suite passes.
2. The Stage 9 verifier is deterministic across two runs.
3. Stage 9 binds exactly to the qualified Stage 8 head, record, and manifest.
4. Only the six Stage 9 files are added relative to the qualified Stage 8 head.
5. Valid installation states produce the exact bounded outcomes.
6. Uninstall defaults to `RETAIN_DATA`.
7. `DELETE_DATA` fails closed without the exact confirmation token.
8. The monitored container is never included in operation targets.
9. Every plan denies filesystem mutation, Docker contact, container mutation, deletion, and native execution.
10. All frozen releases verify and the working tree remains clean.
