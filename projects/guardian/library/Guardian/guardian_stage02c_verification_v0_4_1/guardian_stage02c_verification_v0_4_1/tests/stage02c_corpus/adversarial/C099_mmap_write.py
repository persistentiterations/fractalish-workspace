# --- MANIFEST BEGIN ---
# name: C099_mmap_write
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import mmap
mapping = mmap.mmap(-1, 32)
mapping.write(b"data")
