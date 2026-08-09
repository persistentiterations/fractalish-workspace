# --- MANIFEST BEGIN ---
# name: C062_eval_function_parameter
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

def go(command):
    return eval(command)
go("1 + 1")
