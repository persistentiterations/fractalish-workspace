# RC2 Preparation Contract — Bolt-On Continuity v0.3

## Objective

Prepare a corrected release-candidate record after RC1 formal review identified and corrected incomplete operator documentation and incomplete candidate-tree pinning.

## Corrected candidate boundary

RC2 pins:

- corrected review source commit `67e0da7e41e96870d8dbeafa8031e4de694bb03f`;
- corrected candidate tree file count `76`;
- corrected candidate tree SHA-256 `203d43b5e3f7330c47f7cc72916540b887dccb67d039e1348989a6a8a2ea2376`;
- RC1 disposition `NEEDS_CORRECTION`;
- all Stage 0–10 manifest hashes;
- local test count `78`;
- clean frozen regression, clean frozen diff, and clean working tree evidence.

## Status

The only accepted status is `READY_FOR_RC2_REVIEW`.

This status means the corrected candidate is assembled for explicit human RC2 review. It does not authorize freezing, tagging, merging, publishing, installation, native execution, container mutation, or production-readiness claims.

## Authority boundary

Every record states all of the following as false:

- `release_freeze_authorized`;
- `merge_authorized`;
- `publication_authorized`;
- `production_readiness_claim_authorized`;
- `native_execution_authorized`;
- `container_mutation_authorized`.

## Advancement

Passing RC2 preparation authorizes formal RC2 review only. Every later release action remains separately gated.
