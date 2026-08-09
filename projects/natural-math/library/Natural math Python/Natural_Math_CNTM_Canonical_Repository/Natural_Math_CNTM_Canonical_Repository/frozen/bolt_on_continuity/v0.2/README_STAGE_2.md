# Bolt-On Continuity for Docker v0.2 — Stage 2

## Prerequisite and Supported-Environment Checker

**Status:** Development stage  
**Prior stage:** Stage 1 clean scaffold and frozen-engine boundary

Stage 2 adds a read-only prerequisite checker for the first supported local environments. It reports whether the host can advance to later installation and enrollment work. It makes no host changes, installs nothing, enrolls no container, and grants no Docker action authority.

## Qualified checks

The checker determines:

- supported host family: Windows or Linux;
- supported Python runtime: CPython 3.11 or newer;
- Docker CLI presence;
- Docker client responsiveness;
- local Docker Engine responsiveness;
- Linux-container engine mode;
- observation-only default and disabled gateway state.

The only Docker probes permitted in Stage 2 are:

```text
docker version --format <fixed template>
docker info --format <fixed template>
```

No user-provided command text is accepted.

## Verification

From the repository root:

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_stage_2.py
python -m unittest discover `
  -s .\products\bolt_on_continuity_v0_2\tests `
  -p "test_*.py" `
  -v
python .\tools\verify_all_frozen.py
git diff -- .\frozen
git status --short
```

Optional live local check:

```powershell
$env:PYTHONPATH = ".\products\bolt_on_continuity_v0_2\src"
python -m bolt_on_continuity_v0_2.prerequisite_checker
```

Required endings:

```text
BOLT-ON CONTINUITY V0.2 STAGE 2 VERIFICATION: PASS
OK
ALL FROZEN RELEASE VERIFICATIONS PASSED
```
