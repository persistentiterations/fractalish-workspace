# Bolt-On Continuity v0.4 — Stage 10 Acceptance Gates

Stage 10 passes only when:

1. The Stage 9 head and qualification hashes are bound exactly.
2. All nine required evidence identifiers are present exactly once.
3. Every evidence record has the exact field set and a valid lowercase SHA-256 digest.
4. Every status is `PASS`.
5. Every frozen regression flag is true.
6. Every authority-expanded flag is false.
7. Evidence ordering in the report is deterministic.
8. Repeated qualification produces identical canonical bytes and report digest.
9. The report states observation-only true and all execution, mutation, merge, freeze, tag, publication, installation, and production claims false.
10. The verifier covers exactly the six Stage 10 files and the full frozen tree remains unchanged.