# Stage 8 Contract

Stage 8 adds no new execution authority.

It coordinates existing qualified components:

1. Stage 6 `ControlledNativeExecutor`
2. Stage 7 `ContinuityPipelineBinder`

The live harness:

- requires one full 64-character hexadecimal container ID;
- requires explicit acknowledgement that the target is disposable;
- inspects and verifies an initial running/unpaused state;
- creates deterministic incident, projection, gateway, and dry-run-plan records;
- performs HOLD through the Stage 6 executor;
- verifies the container is running/paused;
- performs RELEASE through the same executor;
- verifies the container is running/unpaused;
- binds all records through the Stage 7 binder;
- independently verifies the terminal qualification receipt;
- attempts bounded RELEASE recovery if an exception occurs after a successful HOLD.

The harness never removes the container. Removal remains an explicit
operator-owned cleanup step after final-state verification.
