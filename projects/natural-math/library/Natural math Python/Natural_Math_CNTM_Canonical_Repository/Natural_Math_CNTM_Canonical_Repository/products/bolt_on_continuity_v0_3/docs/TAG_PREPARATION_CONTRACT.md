# Bolt-On Continuity v0.3 Tag Preparation Contract

## Purpose

Prepare a deterministic decision record for an optional Git tag after the qualified v0.3 fast-forward merge into `main`.

This stage does not create a tag or GitHub release.

## Pinned release boundary

- merged branch: `main`
- merged head: `1c95a1ff8ead30675d4d26f7d77720097c5b9129`
- frozen source commit: `67e0da7e41e96870d8dbeafa8031e4de694bb03f`
- frozen release manifest SHA-256: `3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb`
- proposed annotated tag: `bolt-on-continuity-v0.3`

## Required evidence

- 98 product tests passed after merge.
- All frozen release verification passed after merge.
- Local `main` matched `origin/main`.
- The working tree was clean.
- The proposed tag does not already exist, which must be checked again immediately before tag creation.

## Authority boundary

Successful preparation may produce only `READY_FOR_TAG_DECISION`.

It does not authorize:

- creating or moving a Git tag;
- creating a GitHub release;
- uploading release assets;
- publishing or distributing the product;
- installation or Docker mutation;
- production-readiness claims.

Tag creation requires a separate explicit authorization after local qualification of this preparation package.
