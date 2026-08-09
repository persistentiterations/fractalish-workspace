# Stage 4 Qualification Gates

1. Stage 3 enrollment input is revalidated, including its digest.
2. Configuration fields and safe defaults are exact and closed.
3. Subject identity is the exact full container ID.
4. Storage path and retention bounds fail closed.
5. Configuration digest and storage bytes are deterministic.
6. No Docker, subprocess, socket, filesystem write, or installation authority exists.
7. Unit and adversarial tests pass.
8. Stage 4 verifier passes before and after tests with the same manifest.
9. All earlier stage verifiers and all frozen verifications pass.
10. Frozen diff and working tree remain clean.
