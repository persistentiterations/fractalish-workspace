# Bolt-On Continuity for Docker v0.3

Bolt-On Continuity v0.3 is an observation-first, deterministic Docker continuity foundation. The qualified development track covers Stages 0–10 and remains deliberately bounded: it can inspect Docker through fixed read-only probes, create exact enrollment and configuration records, produce observation-only lifecycle plans, review supplied incidents, record operator approval or denial, classify recovery evidence, and prepare install or uninstall plans. It does not run a background observer, install services, activate a native gateway, or mutate a container.

## Current authority boundary

The development candidate remains:

- observation-only by default;
- gateway disabled;
- native execution unauthorized;
- container mutation unauthorized;
- release freeze, merge, publication, and production-readiness claims unauthorized until separately approved.

`HOLD`, `RELEASE`, approval, recovery, installation, and uninstall outputs are data-only records or plans. They do not execute Docker actions.

## Operator command surface

From an installed development environment, the `bolt` command currently provides:

```text
bolt version
bolt doctor [--json]
bolt prerequisites [--json]
bolt discover [--json]
bolt enroll <full-container-id> <repeat-full-container-id> [--json]
bolt config-check <configuration.json>
bolt status <configuration.json>
bolt start <configuration.json>
bolt stop <configuration.json>
```

`doctor` does not contact Docker. `prerequisites`, `discover`, and `enroll` use only the fixed read-only probes qualified by Stages 2 and 3. The Stage 5 `start` and `stop` commands return plans only; they do not start or stop a service or container.

Stages 6–10 are deterministic library and qualification functions rather than additional end-user CLI commands.

## Development qualification

Run the full test suite:

```powershell
python -m pytest .\products\bolt_on_continuity_v0_3\tests
```

Run all development-stage verifiers:

```powershell
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_0.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_1.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_2.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_3.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_4.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_5.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_6.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_7.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_8.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_9.py
python .\products\bolt_on_continuity_v0_3\tools\verify_stage_10.py
```

Then verify all previously frozen releases and confirm no frozen or working-tree changes:

```powershell
python .\tools\verify_all_frozen.py
git diff -- .\frozen
git status --short
```

## Release status

The Stage 0–10 development track reached `RELEASE_CANDIDATE_READY`, and RC1 preparation reached `READY_FOR_RC_REVIEW`. Formal RC review subsequently identified documentation and complete-tree manifest gaps. RC1 is therefore not approved for freezing. A corrected candidate must be requalified and explicitly approved before any freeze, tag, merge, publication, installation, distribution, or production-readiness claim.