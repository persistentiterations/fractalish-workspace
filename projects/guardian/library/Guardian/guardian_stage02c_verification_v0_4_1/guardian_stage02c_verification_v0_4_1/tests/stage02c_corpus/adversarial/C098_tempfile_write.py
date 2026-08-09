# --- MANIFEST BEGIN ---
# name: C098_tempfile_write
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import tempfile
with tempfile.NamedTemporaryFile(mode="w") as handle:
    handle.write("data")
