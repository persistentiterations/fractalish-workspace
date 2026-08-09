# --- MANIFEST BEGIN ---
# name: C069_type_checking_dynamic_import
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import os
os = __import__("os")
os.system("echo test")
