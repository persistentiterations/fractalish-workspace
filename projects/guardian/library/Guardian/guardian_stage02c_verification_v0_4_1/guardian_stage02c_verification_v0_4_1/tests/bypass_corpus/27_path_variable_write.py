# --- MANIFEST BEGIN ---
# name: 27_path_variable_write
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

from pathlib import Path
p=Path('x.txt')
p.write_text('data')
