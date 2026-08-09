# --- MANIFEST BEGIN ---
# name: C046_match_case_rebinding
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
key = 0
match key:
    case 0:
        p = os.system
    case _:
        p = eval
p("echo test")
