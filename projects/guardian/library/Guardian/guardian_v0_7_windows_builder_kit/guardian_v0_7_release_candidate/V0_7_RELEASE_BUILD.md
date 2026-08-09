# Guardian v0.7 — Real Release Build and Usability Validation

Status: **RELEASE CANDIDATE PREPARED; WINDOWS EXECUTABLE VALIDATION PENDING**

## Completed in this package

- Frozen Guardian engine preserved.
- Package version advanced to 0.7.0.
- PyInstaller specification corrected to include the packaged policy and
  release-integrity manifest.
- Reproducible Windows build script with pinned build tools.
- Windows release-folder structure.
- Four known sample artifacts.
- One-click validation and demo launchers.
- Signed sample scan and ledger replay validation.
- External release checksum generation and verification.
- Clean-machine validation record template.
- Documentation for Python-free end-user validation.

## Frozen engine

`src/guardian_intake/guardian.py`

SHA-256:

`db269d956eaa39fdba9c1e19840590da378c6c30ac24511bc82687d138212bd8`

## Remaining release gate

This Linux environment cannot create or truthfully test a native Windows
PyInstaller executable. Stage v0.7 becomes complete only after, on Windows:

1. `BUILD_WINDOWS.ps1` produces `Guardian.exe`;
2. the release folder is copied to a machine without usable Python;
3. `VALIDATE_GUARDIAN.cmd` reports PASS;
4. `WINDOWS_VALIDATION_RESULTS.json` is preserved;
5. `Guardian.exe` SHA-256 is recorded;
6. any Defender or SmartScreen behavior is documented.

No analyzer changes are included in v0.7.
