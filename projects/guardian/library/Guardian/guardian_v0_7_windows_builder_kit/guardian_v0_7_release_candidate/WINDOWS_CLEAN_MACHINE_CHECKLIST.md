# Windows Clean-Machine Validation Checklist

## Before running Guardian

Record:

- Windows edition and version
- CPU architecture
- whether `python --version` works
- whether `py --version` works
- whether `python3 --version` works
- whether Defender or SmartScreen displays a warning

Do not install Python on the validation machine.

## Validation

1. Extract the complete `Guardian-v0.7-Windows` folder.
2. Run `CHECK_RELEASE_CHECKSUMS.cmd`.
3. Run `VALIDATE_GUARDIAN.cmd`.
4. Confirm all four sample outcomes.
5. Confirm signed ledger replay passes.
6. Save `validation-output/WINDOWS_VALIDATION_RESULTS.json`.
7. Run `RUN_GUARDIAN_DEMO.cmd`.
8. Confirm the HTML explanation opens and the real executable tests run.

## Pass condition

The release passes only when:

- Guardian.exe starts without Python;
- version and embedded integrity checks pass;
- policy validation passes;
- sample outcomes are LET IN, HOLD, REJECT, HOLD;
- every receipt has a file hash, policy hash, and HMAC signature;
- ledger replay passes;
- the executable checksum matches the release checksum file.

## Failure handling

Do not dismiss a warning or failure as “probably Windows.” Record the exact
message, screenshot it when useful, and preserve the validation output.
