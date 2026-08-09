# --- MANIFEST BEGIN ---
# name: C058_os_environ_read
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
value = os.environ.get("AWS_SECRET_ACCESS_KEY")
