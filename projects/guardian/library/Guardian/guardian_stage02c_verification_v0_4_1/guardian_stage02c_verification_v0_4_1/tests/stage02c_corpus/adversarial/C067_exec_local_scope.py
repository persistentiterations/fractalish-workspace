# --- MANIFEST BEGIN ---
# name: C067_exec_local_scope
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

def go():
    exec("p = print")
    p("test")
go()
