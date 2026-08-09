# --- MANIFEST BEGIN ---
# name: C053_importlib_loader
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

from importlib.machinery import SourceFileLoader
loader = SourceFileLoader("module_name", "/tmp/module.py")
loader.load_module()
