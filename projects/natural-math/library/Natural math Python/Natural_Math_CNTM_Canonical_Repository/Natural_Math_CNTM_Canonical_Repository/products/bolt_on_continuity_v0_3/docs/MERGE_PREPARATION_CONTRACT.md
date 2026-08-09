# Merge Preparation Contract — Bolt-On Continuity v0.3

## Objective

Prepare deterministic evidence that the frozen v0.3 branch can be fast-forwarded into `main` without altering the approved release.

## Pinned boundaries

- target branch: `main`
- target head before merge: `0558d3e671d854549003b729eb3879059e8658cc`
- frozen branch head: `75e9cd4d7b16558702b393cf2336cffe45a18474`
- relationship: 77 commits ahead, 0 behind
- frozen manifest: `3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb`
- RC2 formal review: `5e1709214599c0bf075e04557952ee5b563461749df71a41d6fe7bbcc4e1adeb`

## Accepted status

`READY_FOR_MERGE_DECISION`

This status permits an explicit human merge decision only.

## Authority boundary

Preparation does not authorize or perform:

- updating `main`;
- creating a tag or release;
- publication or distribution;
- installation;
- production-readiness claims;
- Docker or container mutation.

## Failure behavior

Any mismatched commit, non-fast-forward relationship, failed frozen verification, dirty frozen diff, or expanded authority fails closed.