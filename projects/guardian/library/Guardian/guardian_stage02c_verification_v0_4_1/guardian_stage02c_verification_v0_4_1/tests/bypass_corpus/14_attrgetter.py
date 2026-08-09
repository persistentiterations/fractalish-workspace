# --- MANIFEST BEGIN ---
# name: 14_attrgetter
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
from operator import attrgetter
runner=attrgetter('system')(os)
runner('id')
