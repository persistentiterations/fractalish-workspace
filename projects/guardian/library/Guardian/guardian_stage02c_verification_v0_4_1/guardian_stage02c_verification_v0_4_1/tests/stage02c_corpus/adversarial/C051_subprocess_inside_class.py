# --- MANIFEST BEGIN ---
# name: C051_subprocess_inside_class
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

class Spawner:
    def go(self):
        import subprocess
        return subprocess.Popen(["echo", "test"])
