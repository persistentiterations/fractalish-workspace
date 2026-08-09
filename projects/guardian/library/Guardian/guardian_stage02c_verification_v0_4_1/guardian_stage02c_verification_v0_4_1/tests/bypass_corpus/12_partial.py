# --- MANIFEST BEGIN ---
# name: 12_partial
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
from functools import partial
runner=partial(os.system)
runner('id')
