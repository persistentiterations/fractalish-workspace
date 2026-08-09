# Stage 10 Release Candidate Contract

The release candidate is rooted at:

```text
products/bolt_on_continuity_v0_1
```

It must preserve these authority limits:

- observation may use Docker inspect, events, logs, and version only as defined
  by the earlier read-only stage;
- controlled mutation is restricted to pause and unpause;
- native mutation requires a full 64-character hexadecimal container ID;
- subprocess execution uses argument arrays and `shell=False`;
- stop, kill, remove, restart, exec, run, create, network mutation, volume
  mutation, and image mutation are outside product authority;
- disposable-container removal remains an operator-owned cleanup command.

The release candidate must contain qualification evidence and documentation for
Stages 0 through 10. It must not modify any repository path under `frozen/`.

The Stage 10 verifier is read-only. It emits a deterministic qualification
record to standard output and writes no file.
