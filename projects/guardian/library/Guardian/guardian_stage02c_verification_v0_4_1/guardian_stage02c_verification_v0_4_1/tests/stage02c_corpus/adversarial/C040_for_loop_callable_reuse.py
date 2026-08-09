# --- MANIFEST BEGIN ---
# name: C040_for_loop_callable_reuse
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
for p in [os.system, os.popen]:
    pass
p("echo test")
