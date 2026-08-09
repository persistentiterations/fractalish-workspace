# --- MANIFEST BEGIN ---
# name: C049_compile_then_exec
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

code = compile("value = 1", "<string>", "exec")
exec(code)
