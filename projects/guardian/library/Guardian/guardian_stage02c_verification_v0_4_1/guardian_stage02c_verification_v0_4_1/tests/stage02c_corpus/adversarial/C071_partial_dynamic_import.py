# --- MANIFEST BEGIN ---
# name: C071_partial_dynamic_import
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import functools
import importlib
load = functools.partial(importlib.import_module, "os")
load().system("echo test")
