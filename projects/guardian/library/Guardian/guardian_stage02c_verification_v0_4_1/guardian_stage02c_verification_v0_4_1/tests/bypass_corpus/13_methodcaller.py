# --- MANIFEST BEGIN ---
# name: 13_methodcaller
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
from operator import methodcaller
runner=methodcaller('system','id')
runner(os)
