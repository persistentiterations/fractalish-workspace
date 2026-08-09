# --- MANIFEST BEGIN ---
# name: 30_multiprocessing_process
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import multiprocessing
multiprocessing.Process(target=print).start()
