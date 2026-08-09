import random
from natural_math_authority_switching_v0_27 import *

# Run one case with debug
params = DEFAULT_PARAMS.copy()
result, receipts = run_authority_switching("fixed4", 3, cycles=6, params=params, variant=0)
print(f"Result: {result}")
print(f"Receipts: {len(receipts)}")
for r in receipts[:10]:
    print(f"  {r}")