# Bolt-On Continuity v0.3 GitHub Release Preparation Contract

## Purpose
Prepare a deterministic GitHub release decision package for the existing annotated tag without publishing a release.

## Pinned release identity
- Repository: `BonAcqui-LLC/cntm-natural-math-canonical-library`
- Tag: `bolt-on-continuity-v0.3`
- Annotated tag object: `fc3e27567e38a94322b437a4285c52ee38ac8407`
- Target commit: `1c95a1ff8ead30675d4d26f7d77720097c5b9129`
- Frozen manifest: `3ce662d9be77735a9de53086160a3b2589f1b0feabcebba1551b080702f821bb`

## Proposed release
- Title: `Bolt-On Continuity v0.3`
- Draft: true during creation unless separately authorized otherwise
- Prerelease: true
- Assets: none

## Required gates
1. The annotated tag exists remotely.
2. The tag resolves to the pinned target commit.
3. The frozen v0.3 verifier passes.
4. The full product test suite passes.
5. All frozen-release verifiers pass.
6. The release notes preserve the observation-only authority boundary.
7. No executable, package, installer, image, binary, or archive is attached.

## Authority boundary
This preparation does not authorize:
- creating or publishing a GitHub release;
- attaching release assets;
- package, binary, image, or installer distribution;
- installation or activation;
- native execution or Docker mutation;
- production-readiness, security, reliability, or zero-drift claims.

Successful verification may report only `READY_FOR_RELEASE_DECISION`.
