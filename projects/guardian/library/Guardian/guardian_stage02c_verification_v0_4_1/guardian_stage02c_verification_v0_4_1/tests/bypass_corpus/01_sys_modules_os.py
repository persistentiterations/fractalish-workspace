# --- MANIFEST BEGIN ---
# name: 01_sys_modules_os
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

import sys
sys.modules['os'].system('id')
