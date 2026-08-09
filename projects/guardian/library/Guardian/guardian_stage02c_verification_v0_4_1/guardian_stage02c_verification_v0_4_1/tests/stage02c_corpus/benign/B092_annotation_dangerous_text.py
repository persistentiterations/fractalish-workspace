# --- MANIFEST BEGIN ---
# name: B092_annotation_dangerous_text
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

def function(value: "__import__('os').system('x')"):
    return value
