# Release Review Gates — Bolt-On Continuity v0.4

A review passes only when:

1. The source head is the exact qualified RC1 head.
2. RC1 verification passed.
3. The complete product suite reports exactly 234 passing tests.
4. All previously frozen releases verify successfully.
5. The pre-freeze `frozen/` diff is empty.
6. The working tree is clean.
7. The proposed snapshot manifest is canonical, sorted, unique, and digest-valid.
8. Claims remain bounded to an internally qualified observation-only release candidate.
9. Freeze, merge, tag, publication, installation, distribution, mutation, and production-readiness authorities remain false.

Any missing, malformed, conflicting, tampered, or authority-expanding evidence fails closed.