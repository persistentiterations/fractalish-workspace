# Stage 5 Contract

The adapter accepts one verified Stage 4 gateway decision and one immutable
adapter policy.

It returns a canonical dry-run plan only when:

- the gateway decision is `APPROVE`;
- the projected action is exactly `HOLD` or `RELEASE`;
- the container and configuration match;
- the decision digest is valid;
- the gateway sequence is not replayed;
- the decision is not older than policy permits.

Mappings are fixed:

```text
HOLD    -> ["docker", "pause",   "<container-id>"]
RELEASE -> ["docker", "unpause", "<container-id>"]
```

`DENY` and `NO_ACTION` decisions produce no native operation plan.

The plan binds:

- gateway decision digest;
- incident ID;
- immutable container ID;
- configuration digest;
- projected action;
- native operation;
- exact argument vector;
- adapter policy digest;
- adapter sequence;
- integer creation time;
- dry-run flag;
- plan digest.

The adapter exposes no execute, run, submit, pause, or unpause method and does
not invoke subprocess, shell, Docker SDK, Docker socket, or host APIs.
