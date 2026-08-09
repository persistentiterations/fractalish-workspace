# --- MANIFEST BEGIN ---
# name: C038_try_except_rebinding
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
try:
    p = os.system
except Exception:
    p = eval
p("echo test")
