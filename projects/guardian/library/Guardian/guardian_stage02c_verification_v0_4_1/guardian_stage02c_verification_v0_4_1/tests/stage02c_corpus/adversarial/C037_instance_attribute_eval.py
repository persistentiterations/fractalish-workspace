# --- MANIFEST BEGIN ---
# name: C037_instance_attribute_eval
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

class W:
    def __init__(self):
        self.evil = eval
W().evil("1 + 1")
