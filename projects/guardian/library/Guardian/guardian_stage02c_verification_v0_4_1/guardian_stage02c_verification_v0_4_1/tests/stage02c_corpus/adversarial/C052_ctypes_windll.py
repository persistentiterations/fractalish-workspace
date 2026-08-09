# --- MANIFEST BEGIN ---
# name: C052_ctypes_windll
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import ctypes
ctypes.windll.kernel32.WinExec("calc.exe", 1)
