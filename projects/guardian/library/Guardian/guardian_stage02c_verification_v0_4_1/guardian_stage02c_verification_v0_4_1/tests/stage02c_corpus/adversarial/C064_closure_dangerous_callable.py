# --- MANIFEST BEGIN ---
# name: C064_closure_dangerous_callable
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
def outer():
    p = os.system
    def inner():
        return p("echo test")
    return inner
outer()()
