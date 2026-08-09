# Bolt-On Continuity for Docker v0.2 — Freeze Execution

This directory contains the explicit one-time freeze tooling for the qualified v0.2 release.

Qualified release-review head:

```text
3574021a3b6735696c759579651abbb2ed9f2b2c
```

Frozen destination:

```text
frozen/bolt_on_continuity/v0.2
```

The freeze builder:

- requires a clean Git working tree;
- requires the qualified release-review commit to be an ancestor of `HEAD`;
- permits only declared freeze-preparation changes after that review commit;
- refuses to overwrite an existing frozen destination;
- copies the approved product tree while excluding freeze-execution tooling and cache files;
- writes `RELEASE_RECORD.json`;
- writes `MANIFEST.json` containing exact byte counts and SHA-256 digests;
- performs no merge, tag, push, publication, Docker command, gateway execution, or native action.

Run the builder only after the freeze-preparation verifier passes:

```powershell
python .\products\bolt_on_continuity_v0_2\tools\verify_freeze_preparation.py
python .\products\bolt_on_continuity_v0_2\tools\build_frozen_v0_2.py
```

After creation, run:

```powershell
python .\tools\verify_all_frozen.py
git status --short
```

The new frozen files will intentionally appear as untracked until they are reviewed and committed. Do not edit the generated snapshot after creation.
