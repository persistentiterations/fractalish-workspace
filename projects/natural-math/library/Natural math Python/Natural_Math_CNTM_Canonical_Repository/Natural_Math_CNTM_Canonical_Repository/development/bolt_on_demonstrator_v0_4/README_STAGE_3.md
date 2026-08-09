# Bolt-On Demonstrator v0.4 — Stage 3

## Read-Only External Observation Adapter

Stage 3 attaches a read-only sidecar observer to the independently implemented
ordinary job service qualified in Stage 2. The adapter consumes only plain host
snapshot and receipt records. It imports no host module and exposes no command,
executor, mutation, authority-token, or action-projection surface.

The stage validates the native hash chain and transition semantics, normalizes
native states into deterministic observation states, emits an independent
observation receipt chain, replays that chain, and removes the sidecar registry
entry without changing the host baseline.

## Files

```text
README_STAGE_3.md
adapters/read_only_job_observer.py
integration/read_only_observation_adapter.py
tests/test_read_only_observation_adapter.py
```

## Qualified boundaries

- Stage 2 remains the required independent-host baseline.
- Frozen v0.3 remains unchanged.
- The adapter uses only Python standard-library modules.
- The adapter public surface is limited to `identity`, `normalise_record`, and
  `observe`.
- The adapter command surface is empty.
- Execution authority is `NONE`.
- One attach and one detach are recorded outside the host.
- The host run digest is identical before, during, and after observation.
- Six native receipts become six deterministic observation events.
- Observation replay reconstructs the same batch digest.
- Forty malformed, missing, duplicated, reordered, stale, or forged observation
  exports fail closed with no host action.

## Run Stage 3

```powershell
python .\development\bolt_on_demonstrator_v0_4\integration\read_only_observation_adapter.py
```

Required final line:

```text
STAGE 3 READ-ONLY EXTERNAL OBSERVATION ADAPTER: PASS
```

## Run the complete v0.4 suite

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_4\tests `
  -p "test_*.py" `
  -v
```

Stage 3 contributes 85 tests. With the existing 145 Stage 1–2 tests, the complete
v0.4 suite must report 230 tests and `OK`.

## Claim boundary

A passing Stage 3 proves that a separately implemented read-only sidecar can
observe the qualified ordinary host, independently validate and normalize its
exported evidence, detect observation corruption, and detach without changing
native behavior or acquiring execution authority.

It does not yet prove that a projected action can cross a host-owned command
gateway. That is Stage 4.

## Expected fixed Stage 3 output

```text
Stage: READ-ONLY EXTERNAL OBSERVATION ADAPTER 0.4.3
Mode: LIVE_READ_ONLY_SIDECAR_OBSERVATION
Bolt-on execution authority: NONE
Host execution boundary: NATIVE_HOST_ONLY
Attachment mode: READ_ONLY_SIDECAR_REGISTRY
Stage 2 commit: ef8ee185eee1fa403b7ec9c24dc9ecd68c725386
Stage 1 source: 8035b10d0e68ec0365f48340366ec3bdd903a4dcc2e7b9b2574b2269c04b4806
Frozen v0.3 manifest: 57f7026ff9dcc69d6dcacb51fda89a40700828e110e74145a0edfaf266c5f6fa
Frozen v0.3 entries: 20
Host: ORDINARY VERSIONED JOB SERVICE 1.0
Host source: 14a3b86d4cabee409d84904f3db4feb416be905c3c54edb3ca5ef4d50e41a797
Adapter: ORDINARY-JOB-READ-ONLY-OBSERVER 1.0
Adapter source: 176232fe8f4a9266fc90259ea82f19e36b36863fb14f328786c8ddb7ebcf6f68
Adapter read-only: True
Adapter command surface entries: 0
Attach registrations: 1
Detach registrations: 1
Registry empty after detach: True
Observed subjects: 1
Observation events: 6
Rejection cases: 40
Rejection cases safely rejected: 40
Host state changes during attach/detach: 0
Baseline native host actions: 6
Observation host actions: 0
Bolt-on executed actions: 0
Deterministic second pass: True
Observation replay: True
Baseline digest: df74c38b6bc7c377bb0fbc175035e03cea46d22c4f48e0109c7ce8ad75508129
Source snapshot digest: 00ede029d8066e193fe5ca93bb5ec71cbc95dba9cc7229bdd01a0346421fc034
Source final receipt digest: 7d3bf1455ef4f607c77b05e193ab45f75f8188bc7785db20cae82fdf954599c9
Final observation digest: b6102ddfcbd33400f17fa74a76e3ba23a110b27413d847964aaa8ecac74f2f3a
Observation batch digest: f633caffac6f989524f9e256f65b8770a4816406fa535039635b37dcf0a05c2c
Observation replay digest: f633caffac6f989524f9e256f65b8770a4816406fa535039635b37dcf0a05c2c
Registry digest: 8c677c43edfcd31c123bb0c6182c1ee9aa74249596de239fda8ab7773c71329a
Qualification receipt digest: 8394989b4f028764b5c9bd5a98357d98a52164d2fe5b5325e0b5254d3265aea3
Qualification replay digest: 8394989b4f028764b5c9bd5a98357d98a52164d2fe5b5325e0b5254d3265aea3
STAGE 3 READ-ONLY EXTERNAL OBSERVATION ADAPTER: PASS
```
