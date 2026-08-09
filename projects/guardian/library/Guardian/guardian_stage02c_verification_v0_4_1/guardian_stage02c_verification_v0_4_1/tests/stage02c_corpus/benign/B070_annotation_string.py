# --- MANIFEST BEGIN ---
# name: B070_annotation_string
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

def function(value: "os.system") -> "subprocess.Popen":
    return value
