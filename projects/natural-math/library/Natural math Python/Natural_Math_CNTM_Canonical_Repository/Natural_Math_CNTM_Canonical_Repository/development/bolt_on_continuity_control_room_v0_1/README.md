# Bolt-On Continuity Control Room v0.1 — Development

This development tree begins at the immutable `bolt-on-continuity-v0.4` tag.

The first authorized product slice is a local visual demonstrator that observes
one real, harmless Docker container through Docker's read-only inspection
interface and explains the displayed facts with one deterministic receipt.

Stage 0 defines and verifies the boundary. It contains no product implementation
and grants no container mutation or recovery authority.

Stage 1 implements the first observation-only vertical slice. The operator owns
the harmless demonstration container lifecycle; the Control Room only inspects
one supplied name or ID.

See `docs/STAGE_0_SCOPE.md` and run:

```powershell
python .\development\bolt_on_continuity_control_room_v0_1\tools\verify_stage_0.py
```

## Run the current localhost demonstration

From the repository root, after the operator has launched or identified one
harmless container:

```powershell
New-Item -ItemType Directory -Force ".\development\bolt_on_continuity_control_room_v0_1\runtime"
$env:PYTHONPATH = ".\development\bolt_on_continuity_control_room_v0_1\src"
$evidence = ".\development\bolt_on_continuity_control_room_v0_1\runtime\bolt-on-demo.json"
python -m control_room.server bolt-on-demo --evidence $evidence --observations 2
```

Open `http://127.0.0.1:8765`; stop it with `Ctrl+C`. This creates the local
same-subject evidence file. For the full running-to-stopped demonstration, pass
the retained transition file with `--transition-evidence $evidence`; the normal
`--evidence` path remains required. The main view is written for ordinary
viewers; **View technical evidence** contains the audit record. Delete temporary
runtime evidence after viewing with `Remove-Item -LiteralPath $evidence`; do not
commit it.

Ordinary unit qualification does not require Docker:

```powershell
python .\development\bolt_on_continuity_control_room_v0_1\tools\verify_stage_1.py
```

Final Stage 1 qualification requires a running operator-selected container:

```powershell
$env:CONTROL_ROOM_DOCKER_CONTAINER = "bolt-on-control-room-demo"
python .\development\bolt_on_continuity_control_room_v0_1\tools\verify_stage_1.py --require-docker
```
