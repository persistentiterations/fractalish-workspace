# --- MANIFEST BEGIN ---
# name: C042_decorated_function_body
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import functools
import os
@functools.lru_cache
def cached(command):
    return os.system(command)
cached("echo test")
