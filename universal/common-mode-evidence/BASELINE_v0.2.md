# Common-mode evidence constructed-fixture baseline v0.2

Preserved: 2026-08-09

Status: accepted constructed-fixture baseline.

## Claim

> In 16 deterministic constructed fixtures, causal-dependency-root counting
> correctly handled all expected decisions and root counts, while message,
> relay, and declared-provenance counting produced false establishments.

## Acceptance record

- causal decisions: 16/16;
- causal root counts: 16/16;
- causal false establishments: 0;
- causal missed establishments: 0;
- executable acceptance tests: 5/5;
- deterministic replay: pass;
- replay hash:
  `e884b75c637f4dc7c17125cbf71a49ff4f8c76ac03ef5c5162902b43f5ebb996`.

## Boundary

Dependency paths are supplied by the fixtures. This baseline validates decision
behavior after dependencies are identified. It does not discover dependencies
from real documents, sensors, or AI outputs. `CLAIM_BOUNDARY.md` is normative.

## Next experiment

Use a small real evidence bundle with dependency graphs labeled independently
by human reviewers. Compare human labels, machine-generated labels, and final
`HOLD`/`ESTABLISH` decisions. Keep that work separate from this baseline.

File integrity is recorded in `SHA256SUMS_v0.2.txt`.

