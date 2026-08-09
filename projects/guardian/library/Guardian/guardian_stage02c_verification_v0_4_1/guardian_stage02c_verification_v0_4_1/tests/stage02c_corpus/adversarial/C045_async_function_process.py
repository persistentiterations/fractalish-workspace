# --- MANIFEST BEGIN ---
# name: C045_async_function_process
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import os
async def runner():
    p = os.system
    return p("echo test")
