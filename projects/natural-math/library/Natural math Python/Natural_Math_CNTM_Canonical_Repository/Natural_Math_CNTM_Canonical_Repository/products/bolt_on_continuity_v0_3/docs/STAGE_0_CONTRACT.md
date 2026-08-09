# Stage 0 Contract — Runnable Product Contract and Packaging Architecture

## Deliverables

1. Product and authority contracts.
2. Installable package metadata and `bolt` entry point.
3. Safe `bolt version` implementation.
4. Configuration, storage, receipt, Docker adapter, and module contracts.
5. Deterministic tests and verifier.

## Mandatory defaults

- observation only;
- telemetry disabled;
- no enabled modules;
- no Docker connection;
- no filesystem writes on import or version display.

## Failure behavior

Unknown commands return non-zero through argparse. Invalid configuration and identity values raise typed validation errors. Unsupported authority fails closed.

## Exit gate

All Stage 0 tests and verifier checks pass, aggregate frozen verification passes, frozen diff is empty, and the user confirms local results.
