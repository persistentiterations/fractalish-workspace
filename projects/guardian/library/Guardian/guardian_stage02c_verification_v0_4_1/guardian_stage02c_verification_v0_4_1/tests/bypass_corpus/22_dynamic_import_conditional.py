# --- MANIFEST BEGIN ---
# name: 22_dynamic_import_conditional
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import importlib
m=importlib.import_module('subprocess' if True else 'os')
