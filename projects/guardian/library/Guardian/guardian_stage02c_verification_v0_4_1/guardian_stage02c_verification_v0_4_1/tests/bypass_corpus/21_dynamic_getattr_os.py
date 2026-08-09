# --- MANIFEST BEGIN ---
# name: 21_dynamic_getattr_os
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import os
name=input()
getattr(os,name)('id')
