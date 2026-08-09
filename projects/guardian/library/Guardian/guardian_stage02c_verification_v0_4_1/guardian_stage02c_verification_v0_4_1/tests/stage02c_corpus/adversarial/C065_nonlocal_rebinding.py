# --- MANIFEST BEGIN ---
# name: C065_nonlocal_rebinding
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
def outer():
    p = print
    def inner():
        nonlocal p
        p = os.system
    inner()
    p("echo test")
outer()
