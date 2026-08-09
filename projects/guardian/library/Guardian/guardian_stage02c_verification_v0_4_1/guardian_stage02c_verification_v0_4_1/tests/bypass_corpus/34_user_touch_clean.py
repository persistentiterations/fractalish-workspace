# --- MANIFEST BEGIN ---
# name: 34_user_touch_clean
# version: 1.0.0
# purpose: Stage 02B adversarial regression case
# dependencies: stdlib
# --- MANIFEST END ---

class Widget:
    def touch(self):
        return 1
Widget().touch()
