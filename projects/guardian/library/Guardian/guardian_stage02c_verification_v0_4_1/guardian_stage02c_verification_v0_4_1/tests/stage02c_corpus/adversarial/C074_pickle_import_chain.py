# --- MANIFEST BEGIN ---
# name: C074_pickle_import_chain
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

p = __import__("pickle")
p.loads(b"not-real")
