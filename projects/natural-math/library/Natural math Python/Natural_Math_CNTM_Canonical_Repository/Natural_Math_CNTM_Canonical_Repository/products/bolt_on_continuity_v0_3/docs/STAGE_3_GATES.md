# Stage 3 Gates

- Exact full-ID discovery normalization passes.
- Duplicate, truncated, uppercase, malformed, and ambiguous discovery records fail closed.
- Selection and confirmation require the same exact discovered ID.
- Inspection identity and Linux platform evidence are verified.
- Enrollment digest is canonical and deterministic.
- No persistent state is written.
- No Docker mutation vector is present.
- All v0.3 tests, prior stage verifiers, frozen verification, frozen diff, and clean status pass.
