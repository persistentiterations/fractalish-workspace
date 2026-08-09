# --- MANIFEST BEGIN ---
# name: B077_ast_literal_eval
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import ast
result = ast.literal_eval("[1, 2, 3]")
