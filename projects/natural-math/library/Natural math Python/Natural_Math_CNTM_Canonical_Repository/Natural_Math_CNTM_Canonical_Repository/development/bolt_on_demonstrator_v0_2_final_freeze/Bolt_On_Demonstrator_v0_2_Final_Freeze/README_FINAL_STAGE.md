# Bolt-On Demonstrator v0.2 Final Freeze

Run package tests:

```powershell
python -m unittest discover -s .\development\bolt_on_demonstrator_v0_2_final_freeze\tests -p "test_*.py" -v
```

Expected: `Ran 10 tests` and `OK`.

Run the final freeze:

```powershell
python .\development\bolt_on_demonstrator_v0_2_final_freeze\final_stage\freeze_v0_2.py --repo .
```

Expected final line:

`BOLT-ON DEMONSTRATOR v0.2 FINAL FREEZE: PASS`

Do not commit until the full freeze output has been reviewed.
