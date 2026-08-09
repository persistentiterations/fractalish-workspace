# RC1 Formal Review Contract — Bolt-On Continuity v0.3

## Objective

Perform a deterministic formal review of the complete release-candidate tree after RC1 preparation.

## Review scope

The review covers every regular file under `products/bolt_on_continuity_v0_3` except generated caches and compiled Python artifacts. It includes development source, tests, contracts, verifiers, operator documentation, and RC preparation material.

## Required checks

The review must establish:

1. the complete candidate tree has a deterministic manifest;
2. no generated cache or compiled artifact is included;
3. operator documentation describes the Stage 0–10 capability and authority boundary;
4. all stage and RC preparation verifiers remain present;
5. no file under `frozen/` is modified;
6. release freeze, merge, tag, publication, installation, and production claims remain unauthorized.

## RC1 disposition

RC1 is not approved because formal review found:

- incomplete Stage 0-only operator documentation;
- no complete candidate-tree manifest.

The documentation defect is corrected after the RC1 pinned source head. The complete-tree manifest is added by the formal review verifier. These corrections require a new candidate source head and local requalification before approval.

## Authority boundary

Formal review does not freeze, tag, merge, publish, install, distribute, invoke Docker, activate a gateway, or mutate a container.

## Advancement

A passing formal review verifier produces evidence for a corrected release candidate. It does not itself approve or freeze that candidate.