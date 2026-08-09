# --- MANIFEST BEGIN ---
# name: C056_marshal_loads
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import marshal
marshal.loads(b"not-real")
