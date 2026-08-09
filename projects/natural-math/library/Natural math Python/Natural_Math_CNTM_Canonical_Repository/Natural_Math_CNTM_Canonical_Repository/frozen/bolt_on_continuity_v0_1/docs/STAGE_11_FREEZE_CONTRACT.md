# Stage 11 Freeze Contract

## New frozen target

```text
frozen/bolt_on_continuity_v0_1
```

Existing contents under `frozen/` are immutable and must remain unchanged.

## Included material

The frozen snapshot contains the complete
`products/bolt_on_continuity_v0_1` tree, including Stage 11 tooling and release
documentation, except:

- `__pycache__` directories;
- `.pyc` files;
- temporary files ending in `.tmp`.

The frozen directory additionally contains:

- `FROZEN_MANIFEST.json`
- `FREEZE_APPROVAL_RECORD.json`

These two records are excluded from the source-tree equivalence list because
they exist only in the frozen snapshot.

## Refusal conditions

The freeze tool must refuse when:

- the release-candidate qualifier does not pass;
- the target frozen directory already exists;
- the repository layout is not recognized;
- a source file changes during snapshot creation;
- source and frozen file lists differ;
- any copied file hash differs;
- any existing frozen path is modified by the tool.

The tool is intentionally one-shot. It never overwrites or repairs an existing
frozen snapshot.
