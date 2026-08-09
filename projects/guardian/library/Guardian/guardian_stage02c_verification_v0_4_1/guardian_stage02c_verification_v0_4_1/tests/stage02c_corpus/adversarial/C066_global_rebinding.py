# --- MANIFEST BEGIN ---
# name: C066_global_rebinding
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
p = print
def set_it():
    global p
    p = os.system
set_it()
p("echo test")
