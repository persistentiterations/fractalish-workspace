# Guardian v0.6.1 — Release Integrity and Documentation

Status: **PASS**

## Completed

- External release manifest for the frozen engine and packaged policy
- `guardian verify-installation`
- Deliberate engine-tamper detection
- `pipx` recommended as the normal isolated installation path
- Unsigned mode requires both `--unsigned-dev` and `GUARDIAN_DEV_MODE=1`
- Large unsigned-mode warning
- Concrete manifest example and behavior in README
- Pinned PyInstaller 6.10.0 build instructions
- Antivirus, code-signing, notarization, compatibility, and extraction warnings
- Simplified evaluation license language
- Signed sample scans and ledger replay after installed-package testing
- HTML demo boundary and visible limitation checks

## Verification

- Frozen engine unchanged: **True**
- Release-layer tests: **4 passed**
- Installation integrity check: **True**
- Original sample outcomes: **True**
- Signed ledger replay: **True**
- Visual demo sanity checks: **True**

## Remaining platform work

A native Windows executable has not been built or code-signed in this environment. That remains a platform-specific distribution task, not a completed v0.6.1 claim.
