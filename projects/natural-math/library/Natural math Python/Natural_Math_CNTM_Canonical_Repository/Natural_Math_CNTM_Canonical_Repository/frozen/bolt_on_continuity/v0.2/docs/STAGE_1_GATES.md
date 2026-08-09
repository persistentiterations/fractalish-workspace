# Stage 1 Gates — Clean Scaffold and Frozen Engine Boundary

Stage 1 passes only when every gate below is satisfied.

## Gate 1 — Isolated namespace

- The package namespace is `bolt_on_continuity_v0_2`.
- No v0.1 package file is copied into v0.2.
- No file under `frozen` or `products/bolt_on_continuity_v0_1` is modified.

## Gate 2 — Data-only boundary

- `config/frozen_engine_boundary.json` exists.
- Every component is marked `candidate_only`.
- Every source path remains under `frozen/bolt_on_continuity_v0_1`.
- Every expected digest is lowercase SHA-256.
- The allowed actions are exactly `NO_ACTION`, `HOLD`, and `RELEASE`.

## Gate 3 — Frozen digest verification

The Stage 1 verifier calculates SHA-256 for every declared frozen source and requires exact equality with the manifest.

## Gate 4 — No operational imports

Stage 1 v0.2 Python files must not import:

- `bolt_on_continuity`;
- `docker`;
- `subprocess`;
- Docker SDK modules;
- gateway, observer, execution, or adapter modules from v0.1.

## Gate 5 — No command execution

No Stage 1 v0.2 file may contain `os.system`, `Popen`, `subprocess.run`, shell execution, Docker socket access, or executable Docker command construction.

## Gate 6 — Strict validation

The boundary loader rejects malformed structures, path escape, duplicate identifiers, action expansion, unknown proof types, and unexpected fields.

## Gate 7 — Tests

The scaffold tests pass using the Python standard library only.

## Gate 8 — Frozen regression

Run:

```powershell
python .\tools\verify_all_frozen.py
git diff -- .\frozen
```

Required result:

```text
ALL FROZEN RELEASE VERIFICATIONS PASSED
```

The frozen diff must be empty.

## Advancement authorization

Passing Stage 1 authorizes Stage 2 prerequisite and supported-environment detection. It does not authorize Docker mutation, operational v0.1 imports, installation changes, or gateway execution.
