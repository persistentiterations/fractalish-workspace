# Common-mode evidence findings

Run date: 2026-08-09

Sixteen deterministic constructed cases tested counting behavior after
provenance and dependency labels were supplied.

| Policy | Decision correct | Root counts correct | False establishments | Missed establishments |
|---|---:|---:|---:|---:|
| Raw message count | 6/16 | 4/16 | 9 | 0 |
| Relay-ID count | 5/16 | 3/16 | 9 | 1 |
| Declared provenance root | 9/16 | 9/16 | 6 | 0 |
| Supplied causal dependency root | 16/16 | 16/16 | 0 | 0 |

Five executable acceptance tests passed. Deterministic replay and the causal
acceptance gate passed.

Replay hash:
`e884b75c637f4dc7c17125cbf71a49ff4f8c76ac03ef5c5162902b43f5ebb996`

## Corrections made after review

- Values are now stored as a set per counted root. The same causal root
  producing both `YES` and `NO` becomes one conflicted root and causes `HOLD`;
  neither value can silently overwrite the other.
- Results now report `total_independent_roots`, `supporting_roots`,
  `opposing_roots`, and `conflicted_roots` separately.
- Exact duplicate witness records are deduplicated. A duplicate witness ID with
  different content becomes `UNRESOLVED`.
- Duplicate relay IDs do not collapse genuinely different causal roots.
- Known provenance with unknown dependency becomes `UNRESOLVED`.
- Dependency paths that converge on one final dependency count once.
- A dependency path containing a cycle becomes `UNRESOLVED`.
- A contradicted causal root invalidates all copies assigned to that root.
- The program now exits unsuccessfully if the causal policy misses any expected
  decision, root count, establishment, or rejection.

## Constructed cases

The fixture bank now includes shared clocks, calibration sources, owners,
training datasets, differently worded summaries of one document, transitive
service paths sharing one database, root-local value conflict, duplicate
witnesses, duplicate relays, unknown dependencies, a contradicted root with
two opposed valid roots, and a dependency cycle.

## Defensible claim

> On 16 deterministic constructed cases, counting supplied causal dependency
> roots avoided the false establishments produced by message, relay, and
> declared-provenance counting.

The dependency roots remain supplied labels. This experiment does not infer
them from real evidence and is not evidence that Natural Math itself is
correct. See `CLAIM_BOUNDARY.md`.

