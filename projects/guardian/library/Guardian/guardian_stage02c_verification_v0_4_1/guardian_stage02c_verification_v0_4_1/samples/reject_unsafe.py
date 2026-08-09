# --- MANIFEST BEGIN ---
# name: Unsafe Runner
# version: 1.0.0
# purpose: Demonstrate a rejected file
# dependencies: requests
# --- MANIFEST END ---

import os
import requests

API_KEY = "abcdefgh12345678"

def run() -> None:
    os.system("echo unsafe")
    requests.get("https://example.com")
