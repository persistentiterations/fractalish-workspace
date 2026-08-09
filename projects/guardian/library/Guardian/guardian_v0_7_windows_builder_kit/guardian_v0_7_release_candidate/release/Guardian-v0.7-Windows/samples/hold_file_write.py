# --- MANIFEST BEGIN ---
# name: Report Writer
# version: 1.0.0
# purpose: Write a local report
# dependencies: stdlib
# --- MANIFEST END ---

with open("report.txt", "w", encoding="utf-8") as handle:
    handle.write("example")
