# Bolt-On Continuity v0.4 RC1 Review Checklist

RC1 review passes only when all items below are proven from deterministic evidence:

- Stage 0 through Stage 10 qualification records are present exactly once and in order.
- Every qualification-record digest and verifier-manifest digest matches the qualified chain.
- The source head equals the qualified Stage 10 head.
- The complete product test suite passes.
- Stage 0 through Stage 10 verifiers pass.
- RC1 verification is deterministic across repeated runs.
- All frozen release verifiers pass.
- `git diff -- frozen` is empty.
- The working tree is clean.
- No authority expansion is present.
- No freeze, merge, tag, publication, installation, distribution, deletion, Docker mutation, container mutation, or native execution has occurred.

Successful review preparation yields `RC1_REVIEW_READY`. This is not release approval and does not authorize any release mutation.
