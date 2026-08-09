# --- MANIFEST BEGIN ---
# name: C075_popen_list_args
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import subprocess
subprocess.Popen(["echo", "test"])
