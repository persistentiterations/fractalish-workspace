# --- MANIFEST BEGIN ---
# name: C043_delete_and_reassign
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
del os
os = __import__("os")
os.system("echo test")
