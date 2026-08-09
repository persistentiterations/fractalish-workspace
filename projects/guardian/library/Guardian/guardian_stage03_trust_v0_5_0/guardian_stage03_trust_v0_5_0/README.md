# Guardian 0.5 — Trust Infrastructure Prototype

Guardian is a manifest-first static intake checkpoint for Python source files.
It reads incoming code as data, applies a validated policy, produces a
versioned result slip, and appends the slip to a locked, hash-chained,
optionally HMAC-authenticated ledger.

Guardian does not execute submitted code.

## This release adds

- strict policy schema validation;
- canonical policy fingerprints;
- result-slip schema 1.0;
- policy and engine provenance in every slip;
- atomic locked ledger append transactions;
- `fsync` persistence;
- explicit unsigned developer mode;
- HMAC verification when a key is supplied;
- explanation output and a visible safety limitation;
- formal threat model;
- policy, receipt, ledger, tamper, concurrency, and regression tests.

## Important limitation

A LET IN result means only that the file passed the implemented checks under the
recorded policy. It is not proof that the file is safe.

See `QUICKSTART.md`, `THREAT_MODEL.md`, `STAGE_03_FREEZE_RECORD.md`, and
`STAGE_02C_COVERAGE_REPORT.md`.
