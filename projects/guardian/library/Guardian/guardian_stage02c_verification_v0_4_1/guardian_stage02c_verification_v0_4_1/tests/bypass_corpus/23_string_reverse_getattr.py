# --- MANIFEST BEGIN ---
# name: 23_string_reverse_getattr
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
getattr(os,'metsys'[::-1])('id')
