# --- MANIFEST BEGIN ---
# name: B087_logging_getlogger
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import logging
class Service:
    def __init__(self):
        self.log = logging.getLogger(__name__)
