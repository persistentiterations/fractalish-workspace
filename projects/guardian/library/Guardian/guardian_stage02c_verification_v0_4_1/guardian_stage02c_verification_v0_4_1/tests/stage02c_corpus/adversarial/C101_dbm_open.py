# --- MANIFEST BEGIN ---
# name: C101_dbm_open
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import dbm
dbm.open("/tmp/example_db", "c")
