# Installation and Operation

## Requirements

- Windows with PowerShell
- Python 3
- Git
- Docker Desktop with a running Linux container engine
- a local checkout of the canonical repository

## Verification

From the repository root:

```powershell
python .\tools\verify_all_frozen.py
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_10_release_candidate.py
```

## Controlled live qualification

Live qualification must use a deliberately created disposable container. The
operator must capture its full 64-character ID and explicitly acknowledge its
disposable status.

The product itself does not remove containers. Cleanup remains explicit:

```powershell
docker rm -f $ContainerId
```

## Safety boundary

Do not target a production container with the v0.1 qualification tools.
The v0.1 release candidate is qualified only for controlled disposable
container trials.
