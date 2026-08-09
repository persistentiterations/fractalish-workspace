# --- MANIFEST BEGIN ---
# name: 11_class_attribute
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
class Runner:
    execute=os.system
Runner.execute('id')
