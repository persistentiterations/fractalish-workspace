# --- MANIFEST BEGIN ---
# name: C050_dynamic_import_concat
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

module = __import__("o" + "s")
module.system("echo test")
