# Bolt-On Demonstrator v0.3 — Stage 4

## Live Host Substitution

Stage 4 moves one bounded portable campaign between two materially different
live host fixtures without adding an execution method to either adapter.

The source host is an independent deterministic lease-queue host. The target
host is the independent versioned workflow host qualified in Stage 2.

Qualified sequence:

1. attach the queue adapter;
2. observe an active queue item;
3. project portable `HOLD` to host-native `SUSPEND`;
4. let a one-use queue-owned boundary consume the exact execution permit;
5. freeze a portable `HELD` checkpoint;
6. detach the queue host;
7. bind a substitution ticket to the checkpoint, detach receipt, and prepared
   target-host digest;
8. attach the workflow adapter;
9. project portable `RELEASE` to host-native `RESUME`;
10. let a one-use workflow-owned boundary consume the exact execution permit;
11. detach the workflow adapter;
12. allow the workflow host to complete under its ordinary rules;
13. independently replay the complete attachment and campaign receipt streams.

The adapters remain read/project-only. Actual host actions occur only in the
separate host-owned boundary functions. The qualified campaign records two host
executions and zero bolt-on executions.

## Files

```text
hosts/queue_state_host.py
portability/live_host_substitution.py
tests/test_live_host_substitution.py
README_STAGE_4.md
```

## Run the independent queue host

```powershell
python .\development\bolt_on_demonstrator_v0_3\hosts\queue_state_host.py
```

Required final line:

```text
LEASE QUEUE HOST SELF-QUALIFICATION: PASS
```

## Run Stage 4

```powershell
python .\development\bolt_on_demonstrator_v0_3\portability\live_host_substitution.py
```

Required final line:

```text
STAGE 4 LIVE HOST SUBSTITUTION QUALIFICATION: PASS
```

The campaign and replay digests must match. Expected host sequence:

```text
QUEUE-HOST-A -> WORKFLOW-HOST-B
```

Expected authority counts:

```text
Executed host actions: 2
Bolt-on executed actions: 0
```

## Run the complete v0.3 suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_3\tests `
  -p "test_*.py" `
  -v
```

## Verify prior frozen releases

```powershell
python .\tools\verify_all_frozen.py
```

## Claim boundary

A passing Stage 4 proves that this deterministic demonstrator can detach from
one qualified host, preserve a portable governed checkpoint, attach to a
materially different prepared host, and complete the bounded HOLD/RELEASE
lifecycle through host-owned execution boundaries with exact receipts and
independent replay.

It does not prove arbitrary production-host compatibility, distributed
migration, crash-safe network failover, production authentication, or safe
operation against an uncontrolled external service. Stage 5 will attack the
adapter, permit, checkpoint, substitution, attachment, and replay boundaries.
