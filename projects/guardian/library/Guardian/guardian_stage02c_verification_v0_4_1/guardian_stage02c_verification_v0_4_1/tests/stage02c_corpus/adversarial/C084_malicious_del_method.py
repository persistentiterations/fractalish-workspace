# --- MANIFEST BEGIN ---
# name: C084_malicious_del_method
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
class Cleanup:
    def __del__(self):
        os.unlink("/tmp/example")
