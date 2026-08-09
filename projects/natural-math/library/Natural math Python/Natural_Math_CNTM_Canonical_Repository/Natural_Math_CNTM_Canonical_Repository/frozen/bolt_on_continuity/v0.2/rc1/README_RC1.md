# Bolt-On Continuity for Docker v0.2 RC1

RC1 packages the qualified Stage 1 through Stage 10 development track for release review.

RC1 is an internal release candidate. It is not a frozen release, is not merged to `main`, is not published, and is not a production-readiness claim.

The qualified source commit is:

```text
31dc5ad0740bf1b262de362f334ed64893a027c2
```

RC1 preparation must:

- inventory every file under `products/bolt_on_continuity_v0_2` except generated cache files;
- compute deterministic SHA-256 digests;
- preserve the 127-test qualification result;
- preserve frozen-regression success;
- disclose excluded authority and claims;
- fail closed on missing, extra, changed, duplicated, or malformed manifest entries;
- leave `frozen` unchanged.

RC1 does not authorize real installation, daemon execution, gateway execution, Docker mutation, release freeze, merge, publication, or production-readiness claims.
