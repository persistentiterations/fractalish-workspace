# --- MANIFEST BEGIN ---
# name: C054_socket_connection
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

import socket
socket.create_connection(("example.invalid", 443))
