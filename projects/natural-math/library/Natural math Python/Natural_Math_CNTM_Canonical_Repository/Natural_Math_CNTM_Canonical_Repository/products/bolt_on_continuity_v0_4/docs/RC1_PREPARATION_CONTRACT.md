# Bolt-On Continuity v0.4 RC1 Preparation Contract

## Purpose

Prepare a deterministic release-candidate manifest and review report from the qualified Stage 0–10 evidence chain.

## Required evidence

RC1 binds the exact qualified Stage 10 head and the qualification-record and verifier-manifest digests for Stages 0 through 10. Evidence must be complete, uniquely staged, canonically ordered, and exactly match the qualified chain.

## Outcomes

The only accepted outcome is `RC1_REVIEW_READY`. Missing, duplicated, reordered, malformed, mismatched, or authority-expanding evidence produces `FAIL_CLOSED_RC1_NOT_READY`.

## Review scope

The report summarizes the bounded capabilities, excluded capabilities, stage evidence, source head, and deterministic RC1 digest. It authorizes release review only.

## Non-authority

RC1 preparation does not create or modify `frozen/`, merge branches, create tags, publish a release, install or distribute software, mutate Docker or containers, write runtime data, delete receipts, or claim production readiness.

Every accepted report states that release freeze, merge, tag creation, publication, installation, distribution, native execution, container mutation, and production-readiness claims remain unauthorized.
