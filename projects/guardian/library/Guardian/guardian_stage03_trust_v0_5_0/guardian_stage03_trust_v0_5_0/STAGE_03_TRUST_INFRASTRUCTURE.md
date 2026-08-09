# Guardian Stage 03 — Trust Infrastructure

Version: 0.5.0

## Frozen analyzer

The `ManifestParser` and `StaticAnalyzer` source block was copied byte-for-byte
from the Stage 02C package.

Frozen block SHA-256:

`f47b9a570b75fea839207182b989f02e99212c5d99c09575537bf491f248d4ab`

## Implemented

- strict policy schema validation;
- rejection of unknown checker types and severities;
- duplicate rule-ID rejection;
- canonical policy SHA-256 fingerprint;
- versioned result-slip schema 1.0;
- engine, policy schema, policy version, and policy fingerprint fields;
- canonical receipt serialization;
- human-readable explanation mode;
- visible security limitation notice;
- cross-platform lock abstraction;
- verify/read/build/sign/append/fsync transaction under one exclusive lock;
- explicit unsigned developer mode;
- HMAC verification when a key is available;
- formal threat model.

## Explicit deferrals

- analyzer corrections for Stage 02C confirmed mismatches;
- ledger rotation;
- APIs, dashboards, packaging, licensing, quarantine, execution, and CI;
- external anchoring of ledger deletion/truncation.
