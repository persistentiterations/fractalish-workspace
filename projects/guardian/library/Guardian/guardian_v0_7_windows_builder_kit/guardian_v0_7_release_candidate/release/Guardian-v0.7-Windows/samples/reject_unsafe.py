# --- MANIFEST BEGIN ---
# name: Unsafe Runner
# version: 1.0.0
# purpose: Demonstrate a rejected artifact
# dependencies: requests
# --- MANIFEST END ---

import os
import requests

API_KEY = "abcdefgh12345678"
os.system("echo unsafe")
requests.get("https://example.com")
