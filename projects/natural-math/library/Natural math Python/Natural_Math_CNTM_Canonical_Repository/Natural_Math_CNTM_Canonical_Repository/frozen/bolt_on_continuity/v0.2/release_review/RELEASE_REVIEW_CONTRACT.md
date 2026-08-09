# Release Review Contract — Bolt-On Continuity for Docker v0.2

## Candidate identity

```text
product = Bolt-On Continuity for Docker
version = 0.2
candidate = v0.2-rc1
qualified_rc1_head = e183ddb6b4fd245229e1e466304e87c9e3cb762f
proposed_frozen_destination = frozen/bolt_on_continuity/v0.2
```

## Required evidence

The review requires:

- RC1 verification pass;
- exactly 142 passing product tests;
- complete frozen regression pass;
- empty diff under `frozen` before snapshot creation;
- clean working tree;
- deterministic proposed-snapshot manifest;
- explicit claims-boundary approval;
- explicit authority-boundary approval.

## Review outcomes

```text
PROPOSED_FREEZE_READY_FOR_APPROVAL
FAIL_CLOSED_RELEASE_REVIEW
```

## Authority boundary

Every accepted review record states:

```text
observation_only = true
gateway_enabled = false
native_execution_authorized = false
container_mutation_authorized = false
release_freeze_authorized = false
merge_authorized = false
tag_authorized = false
publication_authorized = false
production_readiness_claim_authorized = false
```

A passing review authorizes only a later, explicit freeze decision. It does not perform or authorize that freeze automatically.
