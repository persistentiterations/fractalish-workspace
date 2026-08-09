# Authority Boundary — Stage 0

## Components

```text
Docker Engine / configured container
        |
        | read-only evidence
        v
Observer
        |
        | canonical normalized evidence
        v
Decision and receipt core
        |
        | bounded HOLD/RELEASE request
        v
Host-owned gateway
        |
        | independently validated native request
        v
Docker Engine
```

## Authority matrix

| Capability | Observer | Decision core | Viewer | Gateway | Docker/host |
|---|---:|---:|---:|---:|---:|
| Read configured status | Yes | No | Receipts only | Minimal validation read | Yes |
| Read bounded events/logs | Yes | No | Receipts only | No | Yes |
| Normalize evidence | No | Yes | No | No | No |
| Create decision receipts | No | Yes | No | Gateway receipts only | No |
| Project HOLD/RELEASE | No | Yes | No | No | No |
| Validate action request | No | No | No | Yes | Independent final validation |
| Pause/unpause container | No | No | No | Submit exact operation | Execute/reject |
| Arbitrary Docker command | No | No | No | No | Host operator only |
| Shell or exec in container | No | No | No | No | Outside product scope |
| Modify frozen releases | No | No | No | No | No |

## Mandatory separations

1. Observer credentials or process access must not permit Docker writes.
2. Decision code must not import or call a Docker command client.
3. Viewer code must not invoke the gateway.
4. Gateway request input must be a strict data object, never command text.
5. Gateway must not accept arbitrary target identifiers.
6. The configured immutable container ID must be checked again by the gateway.
7. A name match alone must never authorize execution.
8. A projected action is evidence, not authority.
9. No failure fallback may broaden permissions.
10. Disabling or removing the product must leave the container independently operable.

## Fail-closed conditions

No host action may result from:

- malformed JSON;
- schema mismatch;
- unknown contract version;
- missing required field;
- extra forbidden field;
- wrong container identifier;
- name-only target;
- stale or future evidence;
- expired request;
- duplicate request;
- conflicting request identifier reuse;
- tampered receipt or request digest;
- unsupported action;
- unsupported current state;
- unavailable validation evidence;
- ambiguous state;
- missing local authorization;
- gateway recovery uncertainty.

When safe execution cannot be proven under the contract, the gateway rejects.
