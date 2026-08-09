# Natural Math / CNTM Canonical Repository

This repository separates immutable qualified releases from release history, research archives, and future development.

## Protected frozen releases

- `frozen/natural_math/v10.3.2/` — preserved standalone exploration baseline.
- `frozen/natural_math/v12.0/` — complete RC21 qualification chain. RC21 requires RC20 beside it and verifies RC3, RC16, RC17, RC18, RC19, and RC20 source hashes.
- `frozen/cntm/v1.3F/` — finite integer/ternary substrate.
- `frozen/cntm/v2.4/` — qualified application-layer execution record.
- `frozen/cntm/v3.0F/` — qualified deterministic local-memory infrastructure.

Do not edit files under `frozen/`. New Natural Math work starts in `development/natural_math_v12_1/` or a later version. New CNTM association work starts in `development/cntm_v3_1/`.

## Other folders

- `release_history/` contains important predecessors retained for provenance but not treated as the current frozen release.
- `research_archive/` contains the original CNTM morphology-memory experimental line.
- `manifests/SHA256SUMS.txt` records the exact hashes of all protected frozen files.
- `tools/verify_frozen.py` verifies that no frozen file has changed.
- `tools/protect_frozen_windows.ps1` marks frozen files read-only on Windows.

Keep the original 83-file ZIP unchanged and backed up separately. It is the recovery archive, not the working repository.
