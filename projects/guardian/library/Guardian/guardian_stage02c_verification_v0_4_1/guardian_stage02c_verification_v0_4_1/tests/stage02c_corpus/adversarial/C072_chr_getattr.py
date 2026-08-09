# --- MANIFEST BEGIN ---
# name: C072_chr_getattr
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

attr = chr(115) + chr(121) + chr(115) + chr(116) + chr(101) + chr(109)
getattr(__import__("os"), attr)("echo test")
