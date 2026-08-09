# --- MANIFEST BEGIN ---
# name: 29_os_fdopen_write
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
os.fdopen(1,'w')
