# --- MANIFEST BEGIN ---
# name: B088_dataclass_asdict
# version: 1.0.0
# purpose: Stage 02C adversarial verification case
# dependencies: stdlib
# --- MANIFEST END ---

from dataclasses import dataclass, asdict
@dataclass
class Item:
    value: int
result = asdict(Item(1))
