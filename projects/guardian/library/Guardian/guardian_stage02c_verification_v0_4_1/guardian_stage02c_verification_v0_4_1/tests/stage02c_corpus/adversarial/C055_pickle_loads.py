# --- MANIFEST BEGIN ---
# name: C055_pickle_loads
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import pickle
pickle.loads(b"not-a-real-pickle")
