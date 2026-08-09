# Stage 4 Contract

The host-owned gateway receives one verified Stage 3 projection and one immutable
gateway policy.

It returns exactly one decision:

```text
APPROVE
DENY
NO_ACTION
```

Rules:

```text
Valid, unexpired HOLD projection      -> APPROVE
Valid, unexpired RELEASE projection   -> APPROVE only when release is enabled
Valid NO_ACTION projection            -> NO_ACTION
Expired projection                    -> DENY
Tampered projection                   -> DENY
Wrong subject/configuration/policy    -> DENY
Unsupported action                    -> DENY
Replay or sequence regression         -> DENY
```

The decision binds:

- projection digest;
- incident and container identity;
- configuration digest;
- gateway policy digest;
- gateway sequence;
- previous gateway decision digest;
- integer decision time;
- decision and reason;
- canonical decision digest.

The gateway keeps a deterministic in-memory replay barrier for the configured
subject. It does not call Docker, invoke a shell, open a socket, pause a
container, unpause a container, or own any executor.
