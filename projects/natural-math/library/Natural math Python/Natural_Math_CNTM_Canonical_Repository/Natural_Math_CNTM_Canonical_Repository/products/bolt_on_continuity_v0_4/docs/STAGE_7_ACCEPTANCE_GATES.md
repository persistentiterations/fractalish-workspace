# Bolt-On Continuity v0.4 — Stage 7 Acceptance Gates

- G7.1: Stage 7 is bound to the exact qualified Stage 6 head, record hash, and verifier manifest.
- G7.2: Requests require exact fields, full identities, HOLD or RELEASE, bounded sequences, and a valid canonical digest.
- G7.3: Expired requests, NO_ACTION, aliases, command text, extra fields, and altered digests fail closed.
- G7.4: Gateway state starts DISABLED and only real alternating transitions with increasing sequences are accepted.
- G7.5: Approval requires an enabled gateway; denial is allowed in either gateway state.
- G7.6: Decision records bind the request ID and digest, decision, reason, sequence, and canonical digest.
- G7.7: Duplicate, conflicting, and request-ID-reuse cases fail closed.
- G7.8: Every result states native_execution_authorized false.
- G7.9: No Docker, command construction, filesystem, subprocess, socket, network, credential, autonomous, service, thread, recovery, publication, installation, or distribution capability is added.
- G7.10: All Stage 0 through Stage 7 tests and verifiers pass twice deterministically.
- G7.11: Frozen releases remain unchanged and the working tree is clean.
