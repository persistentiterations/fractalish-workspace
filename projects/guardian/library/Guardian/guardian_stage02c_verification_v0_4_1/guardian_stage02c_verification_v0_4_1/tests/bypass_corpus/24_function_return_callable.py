# --- MANIFEST BEGIN ---
# name: 24_function_return_callable
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
def get_runner():
    return os.system
runner=get_runner()
runner('id')
