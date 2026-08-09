# --- MANIFEST BEGIN ---
# name: C039_if_else_rebinding
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
flag = True
if flag:
    p = os.system
else:
    p = os.popen
p("echo test")
