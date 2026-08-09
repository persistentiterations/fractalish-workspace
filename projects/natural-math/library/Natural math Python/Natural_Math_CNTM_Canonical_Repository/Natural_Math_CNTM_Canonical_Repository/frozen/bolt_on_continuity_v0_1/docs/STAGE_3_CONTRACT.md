# Stage 3 Contract

The projection engine accepts one validated incident export and one immutable
projection policy.

The first policy is intentionally narrow:

```text
RUNNING + UNHEALTHY + incident open     -> HOLD
PAUSED + HEALTHY + recovery approved    -> RELEASE
all other qualified combinations        -> NO_ACTION
```

Fail-closed inputs also produce `NO_ACTION` with a reason code.

The output is canonical and contains:

- contract and schema version;
- incident ID;
- immutable container ID;
- configuration digest;
- incident export digest;
- policy digest;
- projected action;
- expected state;
- reason code;
- integer projection sequence;
- integer issuance and expiry values;
- projection digest.

The engine must reject malformed, stale, expired, tampered, unsupported,
cross-subject, cross-configuration, ambiguous, or closed-incident action inputs.

Stage 3 has no gateway, Docker client, shell runner, command executor, socket,
pause call, unpause call, or host authority.
