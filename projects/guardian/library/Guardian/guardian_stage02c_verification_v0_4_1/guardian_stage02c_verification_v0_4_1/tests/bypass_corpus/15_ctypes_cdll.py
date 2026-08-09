# --- MANIFEST BEGIN ---
# name: 15_ctypes_cdll
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import ctypes
ctypes.CDLL('libc.so.6').system(b'id')
