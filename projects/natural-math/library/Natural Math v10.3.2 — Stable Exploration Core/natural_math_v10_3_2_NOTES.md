# Natural Math v10.3.2 — Cache Stabilization

Purpose: complete the v10.3 optimization lane without changing navigation behavior.

## Narrow changes

1. Active targets are rebuilt once, then updated incrementally only around changed cells and passages.
2. Current-position and relay-anchor BFS results use separate cache keys.
3. The known-edge adjacency map is built once per edge-version and reused by both BFS passes.
4. New counters report incremental target updates and each cache type.

No changes were made to maze generation, local signal, keeper rules, relay arbitration, safety reserve, passage-state legality, receipts, replay, audit, follower, or route freezing.

## Default seed 7317 regression

v10.3.2 reproduces the v10.3.1 behavioral result exactly:

- movement: 850
- sorties: 5
- safe returns: 4
- keepers: 62
- relays: 5
- assignments: 105
- route length: 109
- audit/follower/replay: PASS
- live and replay state hashes: identical to v10.3.1

## Default performance receipt

- active-target full rebuilds: 1 (v10.3.1: 36)
- full visited cells scanned: 43 (v10.3.1: 7,688)
- incremental target updates: 35
- target cells rechecked incrementally: 701
- BFS calls: 64 (v10.3.1: 72)
- anchor BFS cache hits: 8
- adjacency cache hits: 36
- BFS nodes expanded: 13,597 (v10.3.1: 15,376)
- measured fallback time: 68.629 ms (v10.3.1 sample: 278.027 ms)

Wall-clock timing depends on the device and online runner. Structural counters and replay hashes are the primary validation evidence.
