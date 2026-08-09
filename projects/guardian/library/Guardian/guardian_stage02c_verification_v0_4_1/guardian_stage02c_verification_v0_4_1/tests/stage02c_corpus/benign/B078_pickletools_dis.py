# --- MANIFEST BEGIN ---
# name: B078_pickletools_dis
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import pickletools
data = b"N."
pickletools.dis(data)
