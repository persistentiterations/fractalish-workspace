# Stage 6 Contract

Permitted write operations are exactly:

```text
docker pause <full-container-id>
docker unpause <full-container-id>
```

The executor must:

- bind one full 64-character hexadecimal container ID;
- use subprocess argument arrays with `shell=False`;
- inspect before and after each action;
- require pre-state `running=true` and `paused=false`;
- verify HOLD as `running=true` and `paused=true`;
- verify RELEASE/recovery as `running=true` and `paused=false`;
- reject names, prefixes, multiple subjects, extra arguments, or other actions;
- attempt bounded unpause recovery if failure occurs after pause;
- record stdout, stderr, return code, state evidence, and SHA-256 receipts;
- never expose a generic public command method.

A completed qualification must end with the disposable container running and
unpaused. Production containers are outside Stage 6 scope.
