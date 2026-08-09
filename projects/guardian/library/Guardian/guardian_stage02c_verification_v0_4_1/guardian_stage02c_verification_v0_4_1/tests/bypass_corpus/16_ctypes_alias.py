# --- MANIFEST BEGIN ---
# name: 16_ctypes_alias
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import ctypes as c
lib=c.CDLL('libc.so.6')
lib.system(b'id')
