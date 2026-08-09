# Stage 7 Qualification Gates

1. Projected request schema and digest are deterministic.
2. Exact full subject identity and bounded sequence window are enforced.
3. Gateway transitions are explicit, binary, and fail closed.
4. Approval requires enabled gateway state; denial does not.
5. Duplicate, conflict, and request-identifier reuse are rejected.
6. No Docker, subprocess, socket, filesystem, credential, or execution authority exists.
7. Tests, verifier, frozen verification, frozen diff, and clean status pass.