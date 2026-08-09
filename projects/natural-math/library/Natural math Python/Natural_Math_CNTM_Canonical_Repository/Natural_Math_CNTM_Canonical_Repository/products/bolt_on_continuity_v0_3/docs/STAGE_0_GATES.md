# Stage 0 Gates

- G0.1: package imports without side effects.
- G0.2: `bolt version` emits one stable version line.
- G0.3: defaults are observation-only, telemetry-off, and modules-disabled.
- G0.4: canonical JSON is byte-stable and hash-verifiable.
- G0.5: storage interface cannot mutate without an explicit implementation.
- G0.6: Docker adapter exposes no mutation methods.
- G0.7: fake adapter is deterministic.
- G0.8: module registration cannot grant authority.
- G0.9: verifier rejects forbidden Docker/subprocess imports in active source.
- G0.10: no frozen path is part of Stage 0 output.
