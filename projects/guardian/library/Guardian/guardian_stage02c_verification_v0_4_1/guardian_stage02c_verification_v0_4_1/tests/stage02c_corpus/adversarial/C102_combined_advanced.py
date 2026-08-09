# --- MANIFEST BEGIN ---
# name: C102_combined_advanced
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import functools
import importlib
import operator
load = functools.partial(importlib.import_module, "os")
method = operator.attrgetter("system")
method(load())("echo test")
