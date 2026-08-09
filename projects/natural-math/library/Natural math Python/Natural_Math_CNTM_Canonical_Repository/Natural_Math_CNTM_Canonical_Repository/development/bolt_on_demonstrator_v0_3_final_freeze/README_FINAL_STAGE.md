# Bolt-On Demonstrator v0.3 — Final Freeze

This package performs the separate final freeze approved by v0.3-RC1. It does
not alter frozen v0.1 or v0.2.

The procedure re-runs every Stage 1–5 qualification, both independent host
self-checks, all 256 v0.3 tests, and the aggregate frozen verifier before copying
or sealing anything.

A successful run creates:

```text
frozen/bolt_on/v0.3/
tools/verify_bolt_on_v0_3.py
```

It also adds the v0.3 verifier to `tools/verify_all_frozen.py`.

Run the package tests:

```powershell
python -m unittest discover `
  -s .\development\bolt_on_demonstrator_v0_3_final_freeze\tests `
  -p "test_*.py" `
  -v
```

Required package-test ending:

```text
Ran 53 tests

OK
```

Run the final freeze:

```powershell
python .\development\bolt_on_demonstrator_v0_3_final_freeze\final_stage\freeze_v0_3.py --repo .
```

Required final line:

```text
BOLT-ON DEMONSTRATOR v0.3 FINAL FREEZE: PASS
```

The operation is transactional. If a post-copy gate fails, the new v0.3 frozen
release and verifier are removed and the aggregate verifier is restored.

Do not commit until the package tests, complete freeze output, final aggregate
verification, and repository status have been reviewed.
