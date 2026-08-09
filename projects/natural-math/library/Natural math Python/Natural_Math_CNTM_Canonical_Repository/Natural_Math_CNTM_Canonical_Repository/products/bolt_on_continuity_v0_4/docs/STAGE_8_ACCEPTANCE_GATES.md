# Bolt-On Continuity v0.4 — Stage 8 Acceptance Gates

1. The branch descends exactly from qualified Stage 7 head `ddb7a2430a709705d91142742bd6ad3b61c24653`.
2. All prior tests and verifiers pass unchanged.
3. Subject, store, duplicate, and uncertain-action classifications are deterministic and fail closed.
4. Same-name replacement never inherits the enrolled subject identity.
5. Only a matched subject, healthy store, and resolved nonterminal evidence may return `RESUME_OBSERVATION_ONLY`.
6. Terminal requests return `SUPPRESS_DUPLICATE`; conflicting reuse returns `FAIL_CLOSED_UNCERTAIN`.
7. All operational, Docker, filesystem, gateway, network, process, and publication authorities remain false.
8. Two verifier runs are byte-identical.
9. Frozen releases and the working tree remain unchanged.
