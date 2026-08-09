# --- MANIFEST BEGIN ---
# name: C086_with_write
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

with open("/tmp/example", "w") as handle:
    handle.write("data")
