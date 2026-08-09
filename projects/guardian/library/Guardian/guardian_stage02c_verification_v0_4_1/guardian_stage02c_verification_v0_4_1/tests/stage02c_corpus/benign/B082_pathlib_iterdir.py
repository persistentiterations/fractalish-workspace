# --- MANIFEST BEGIN ---
# name: B082_pathlib_iterdir
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

from pathlib import Path
entries = Path(".").iterdir()
