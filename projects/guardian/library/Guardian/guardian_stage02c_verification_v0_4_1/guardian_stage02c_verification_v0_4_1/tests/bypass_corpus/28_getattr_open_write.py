# --- MANIFEST BEGIN ---
# name: 28_getattr_open_write
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import builtins
opener=getattr(builtins,'open')
opener('x.txt','w')
