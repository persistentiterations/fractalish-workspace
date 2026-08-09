# --- MANIFEST BEGIN ---
# name: C059_subprocess_shell_true
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import subprocess
subprocess.run("echo test", shell=True)
