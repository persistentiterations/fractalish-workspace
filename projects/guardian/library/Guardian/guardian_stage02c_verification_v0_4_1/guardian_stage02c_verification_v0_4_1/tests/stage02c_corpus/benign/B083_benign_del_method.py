# --- MANIFEST BEGIN ---
# name: B083_benign_del_method
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

class Cleanup:
    def __del__(self):
        self.value = None
