# --- MANIFEST BEGIN ---
# name: C041_starargs_eval
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

evil = eval
evil(*["1 + 1"])
