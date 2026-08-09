# Frozen-file policy

1. Never edit a file inside `frozen/`.
2. Before and after copying or publishing the repository, run `python tools/verify_frozen.py`.
3. All new work must use a new version and live under `development/` until separately qualified.
4. A frozen release may be copied into a new development file, but the original remains unchanged.
5. Any hash mismatch means the release is no longer the qualified artifact until restored from a verified backup.
6. Keep at least three copies: local computer, private cloud or private Git remote, and offline storage.
7. Git tags should identify frozen releases. Do not move or reuse a release tag.
8. Do not claim morphology-specific superiority for CNTM v3.0F; it freezes deterministic local-memory infrastructure only.
