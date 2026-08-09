# RC1 Preparation Contract — Bolt-On Continuity v0.3

## Objective

Prepare one deterministic release-candidate review record from the locally qualified Stage 0–10 development track.

## Qualified source boundary

The RC1 record pins the Stage 10 qualification head:

```text
6ef5595f4d0d86074fbb53e4a37a9c04d4a62f78
```

This is the final development-stage source reviewed before RC preparation began.

## Required evidence

The record contains exactly:

- product and version;
- candidate identifier `v0.3-rc1`;
- qualified source commit;
- ordered Stage 0–10 manifest hashes;
- test count `66`;
- frozen-regression result;
- clean-frozen-diff result;
- clean-working-tree result;
- authority statements;
- deterministic record digest.

## Readiness status

The only accepted status is:

```text
READY_FOR_RC_REVIEW
```

This status means the candidate evidence is assembled for an explicit release review. It does not mean the release is frozen, tagged, merged, published, installed, or production ready.

## Authority boundary

Every record states:

```text
release_freeze_authorized = false
merge_authorized = false
publication_authorized = false
production_readiness_claim_authorized = false
native_execution_authorized = false
container_mutation_authorized = false
```

## Prohibited behavior

RC1 preparation must not:

- modify any file under `frozen/`;
- create a Git tag or release;
- merge to `main`;
- alter the product version;
- create installation artifacts;
- claim production readiness;
- call Docker or mutate a container.

## Advancement

Passing RC1 preparation authorizes an explicit human release-candidate review. Freeze, tag, merge, and publication each still require separate authorization.