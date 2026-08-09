# --- MANIFEST BEGIN ---
# name: B079_subprocess_list2cmdline
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import subprocess
text = subprocess.list2cmdline(["echo", "test"])
