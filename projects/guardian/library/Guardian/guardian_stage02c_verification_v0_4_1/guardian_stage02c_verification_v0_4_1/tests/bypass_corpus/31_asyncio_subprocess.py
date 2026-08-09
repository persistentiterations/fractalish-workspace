# --- MANIFEST BEGIN ---
# name: 31_asyncio_subprocess
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import asyncio
asyncio.create_subprocess_shell('id')
