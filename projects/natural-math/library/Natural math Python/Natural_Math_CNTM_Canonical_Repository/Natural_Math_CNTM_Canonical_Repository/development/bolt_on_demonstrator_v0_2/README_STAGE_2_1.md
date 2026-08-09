# Bolt-On Demonstrator v0.2 — Stage 2.1 Digest Correction

## Scope

This package changes one regression-test constant only.

Changed file:

- `tests/test_mediated_hold_host.py`

No executable mediation, authority, host, governance, memory, or frozen-release
source is included or modified.

## Correction

Obsolete expected mediation digest:

`c8b6a06290db738ffb514d1fb27d9cfd579fcbd54d6e3886cb8c896e632827ec`

Canonical digest produced by the user's Stage 2 qualification:

`3b90f8f8230e3dfe7791ece89649aa019f641025a8588050d5cc2b7bb5157ac9`

The qualification itself passed and all other assertions passed. The previous
test package retained the obsolete expected constant, causing exactly one
failure in `test_fixed_release_digests_match`.

## Corrected test SHA-256

`b7af65d80934bc9e18570e13feb0494f0ec4e9c19d9fefea070bb7192c0f0321`

## Expected result

After replacing the test file and rerunning the complete v0.2 suite:

```text
Ran 54 tests

OK
```
