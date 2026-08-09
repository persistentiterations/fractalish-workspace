# Stage 1 Gates

- G1.1: `bolt doctor` runs without contacting Docker.
- G1.2: `bolt doctor --json` is canonical and deterministic.
- G1.3: Python versions below 3.11 fail the prerequisite check.
- G1.4: Windows and Linux receive stable recommended data paths.
- G1.5: Docker CLI discovery uses path inspection only.
- G1.6: no Docker SDK, subprocess, shell, socket, or filesystem-write authority is added.
- G1.7: all Stage 0 tests continue to pass.
- G1.8: Stage 0 manifest remains stable when Stage 1 files exist.
