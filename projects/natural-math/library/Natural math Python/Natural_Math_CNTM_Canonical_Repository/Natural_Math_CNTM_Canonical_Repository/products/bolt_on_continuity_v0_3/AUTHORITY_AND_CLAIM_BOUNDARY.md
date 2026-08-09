# Authority and Claim Boundary — v0.3 Stage 0

Default authority class: `OBSERVATION_ONLY`.

Stage 0 permits no native Docker command execution and no Docker SDK calls. The scaffold may define typed interfaces for later read operations, but ships only deterministic fake implementations.

Prohibited operations include start, stop, restart, pause, unpause, kill, remove, create, exec, image mutation, network mutation, volume mutation, update, restore, and arbitrary command construction.

The separately qualified v0.1 pause/unpause authority is not inherited or activated.

No production-readiness, universal compatibility, zero-drift, autonomous-safety, perfect-recovery, or replacement-product claim is authorized.
