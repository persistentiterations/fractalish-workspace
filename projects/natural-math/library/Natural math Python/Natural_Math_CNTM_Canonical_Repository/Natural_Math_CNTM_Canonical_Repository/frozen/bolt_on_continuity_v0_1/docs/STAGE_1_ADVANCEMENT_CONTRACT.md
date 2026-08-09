# Stage 1 Advancement Contract

Stage 1 is limited to a read-only Docker observer.

It may add:

- a Docker evidence fixture;
- a read-only observation adapter;
- deterministic normalization;
- bounded collection configuration;
- evidence receipts;
- replay fixtures;
- unit, integration, malformed-input, stale-input, and tamper tests;
- Stage 1 documentation.

It must not add:

- `HOLD` or `RELEASE` projection;
- a gateway;
- Docker pause or unpause calls;
- any Docker write operation;
- container exec;
- arbitrary shell execution;
- a network listener;
- an installer requiring production privileges;
- multi-container support.

Stage 1 must independently prove that its Docker access surface cannot issue a
write operation under the qualified adapter contract.
