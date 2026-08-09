# --- MANIFEST BEGIN ---
# name: 18_zipimport_loader
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import zipimport
loader=zipimport.zipimporter('x.zip')
