# --- MANIFEST BEGIN ---
# name: C061_dynamic_pickle_import
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

module = __import__("pickle")
module.loads(b"not-real")
