# --- MANIFEST BEGIN ---
# name: 25_lambda_dynamic_import
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

runner=lambda: __import__('subprocess').check_output(['id'])
runner()
