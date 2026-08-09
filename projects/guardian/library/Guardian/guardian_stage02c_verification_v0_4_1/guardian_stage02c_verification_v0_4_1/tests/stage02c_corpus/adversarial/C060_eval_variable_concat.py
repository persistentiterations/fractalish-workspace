# --- MANIFEST BEGIN ---
# name: C060_eval_variable_concat
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

x = "1"
y = " + 1"
eval(x + y)
