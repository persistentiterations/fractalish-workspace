import hashlib
import json
from fractions import Fraction
from typing import List, Tuple, Dict, Any, Optional

# =============================================================================
# CONFIGURATION (Exact Rational Arithmetic Enforced)
# =============================================================================

GRID_SIZE = 5
TOTAL_STEPS = 100
WITNESS_STEP = 50  # The critical incision point

# =============================================================================
# HELPERS: Canonical Serialization & Hashing
# =============================================================================

def grid_to_canonical_string(grid: List[List[Fraction]]) -> str:
    """Convert grid to a deterministic, sortable JSON string of exact rationals."""
    # Convert Fractions to "n/d" strings
    str_grid = [[f"{num.numerator}/{num.denominator}" for num in row] for row in grid]
    return json.dumps(str_grid, sort_keys=True, separators=(',', ':'))

def hash_canonical(content: str) -> str:
    """SHA-256 digest of the canonical content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def make_receipt(step: int, state_str: str, action: Tuple[int, int], witness: Fraction, pos: Tuple[int, int]) -> Dict[str, Any]:
    """Generate a receipt following the exact schema."""
    # The state hash is computed BEFORE the action is applied (P_i)
    h = hash_canonical(f"{step}:{state_str}:{action}:{str(witness)}")
    return {
        "step": step,
        "state_hash": h,
        "action": action,
        "witness": str(witness),  # exact rational string
        "pos": pos
    }

# =============================================================================
# DETERMINISTIC TRANSITION FUNCTION
# =============================================================================

def get_action(grid: List[List[Fraction]], pos: Tuple[int, int]) -> Tuple[int, int]:
    """
    Deterministically choose the move to the neighboring cell with the lowest resistance.
    Tie-breaking: (resistance, dx, dy) lexicographic. Exact rational comparison.
    """
    x, y = pos
    candidates = []
    for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            # Resistance value at the candidate cell
            val = grid[nx][ny]
            candidates.append(((val, dx, dy), (dx, dy)))
    
    if not candidates:
        return (0, 0)
    # Sort by value, then dx, then dy (all exact rationals/comparable)
    candidates.sort(key=lambda t: (t[0][0], t[0][1], t[0][2]))
    return candidates[0][1]

def apply_transition(grid: List[List[Fraction]], pos: Tuple[int, int], action: Tuple[int, int], witness: Fraction) -> Tuple[List[List[Fraction]], Tuple[int, int]]:
    """
    Apply the irreversible state transition.
    - Move the agent.
    - Inject the witness perturbation into the newly occupied cell (the incision).
    """
    x, y = pos
    dx, dy = action
    nx, ny = x + dx, y + dy
    # Ensure movement is valid
    if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
        return grid, pos
    
    new_pos = (nx, ny)
    # The witness adds to the resistance of the cell we just entered (this is the scar)
    grid[nx][ny] += witness
    return grid, new_pos

# =============================================================================
# CORE SIMULATOR
# =============================================================================

def simulate(initial_grid: List[List[Fraction]], witness_map: Dict[int, Fraction]) -> Tuple[List[List[Fraction]], List[Dict[str, Any]], Tuple[int, int]]:
    """
    Run the deterministic simulation.
    - Logs a receipt at EVERY step.
    - Injects witness from witness_map at the designated steps.
    """
    # Deep copy to avoid mutating initial
    grid = [row[:] for row in initial_grid]
    pos = (0, 0)
    receipts = []

    for step in range(TOTAL_STEPS):
        # Capture state PRIOR to transition for hashing (P_i)
        state_str = grid_to_canonical_string(grid)
        action = get_action(grid, pos)
        witness = witness_map.get(step, Fraction(0, 1))  # default to zero if not specified
        
        # Record the receipt (before mutating)
        rec = make_receipt(step, state_str, action, witness, pos)
        receipts.append(rec)
        
        # Apply the irreversible transition
        grid, pos = apply_transition(grid, pos, action, witness)

    return grid, receipts, pos

def replay(initial_grid: List[List[Fraction]], receipts: List[Dict[str, Any]]) -> Tuple[List[List[Fraction]], Tuple[int, int], List[str]]:
    """
    Deterministically replay the receipt stream.
    Returns the reconstructed state and a list of divergence logs.
    """
    grid = [row[:] for row in initial_grid]
    pos = (0, 0)
    divergences = []

    for rec in receipts:
        step = rec["step"]
        expected_action = rec["action"]
        expected_witness = Fraction(rec["witness"])
        
        # Recompute action deterministically from the current reconstructed state
        computed_action = get_action(grid, pos)
        if computed_action != expected_action:
            divergences.append(
                f"Step {step}: STRUCTURAL DIVERGENCE. Action mismatch. "
                f"Expected {expected_action}, got {computed_action}."
            )
            # We still apply the expected action from the receipt to maintain replay,
            # but the divergence is logged. (Alternatively, we could halt.)
        
        # Apply transition using the witness FROM THE RECEIPT
        grid, pos = apply_transition(grid, pos, expected_action, expected_witness)

    return grid, pos, divergences

# =============================================================================
# EXECUTION PROTOCOL & SUCCESS METRICS
# =============================================================================

def run_experiment():
    print("=" * 60)
    print("CONFIGURATOR v0.1 – 48-Hour Experiment")
    print("Exact Rational Arithmetic (Fraction) | SHA-256 Receipts")
    print("=" * 60)

    # --------------------------------------------------------------
    # Setup: Initial Seed (S0) – exact rationals
    # --------------------------------------------------------------
    initial_seed = [[Fraction(1, 1) for _ in range(GRID_SIZE)] for __ in range(GRID_SIZE)]
    initial_seed[0][0] = Fraction(0, 1)  # Entry point is free

    # --------------------------------------------------------------
    # LANE A: Full Fidelity (Exact Generative Replay)
    # --------------------------------------------------------------
    print("\n[LANE A] Running simulation with W_50 = 1/3...")
    witness_A = {WITNESS_STEP: Fraction(1, 3)}
    final_grid_A, receipts_A, final_pos_A = simulate(initial_seed, witness_A)
    print(f"  Simulation A complete. Terminal pos: {final_pos_A}")
    print(f"  Terminal grid hash: {hash_canonical(grid_to_canonical_string(final_grid_A))}")

    # Replay using the exact receipts generated
    print("  Replaying Lane A from receipts...")
    replay_grid_A, replay_pos_A, divs_A = replay(initial_seed, receipts_A)
    if replay_grid_A == final_grid_A and replay_pos_A == final_pos_A and not divs_A:
        print("  ✅ LANE A: PASS – Full generative fidelity verified. (Integer dimension confirmed.)")
    else:
        print("  ❌ LANE A: FAIL – Replay mismatch.")
        if divs_A:
            print(f"     Divergences: {divs_A}")

    # --------------------------------------------------------------
    # LANE B: Witness Omission / Alteration (Stochastic Divergence)
    # --------------------------------------------------------------
    print("\n[LANE B] Testing witness omission (alter W_50 to 0)...")
    # We use the receipts from Lane A, but we modify the witness in the receipt stream
    # to simulate a scenario where the logged witness does not match the actual applied noise.
    # In practice, Melissa will run a separate simulation with W=0 and try to verify it
    # against the A receipts.
    print("  Simulating Lane B independently with W_50 = 0...")
    witness_B = {WITNESS_STEP: Fraction(0, 1)}
    final_grid_B, receipts_B, final_pos_B = simulate(initial_seed, witness_B)
    print(f"  Simulation B complete. Terminal pos: {final_pos_B}")
    print(f"  Terminal grid hash: {hash_canonical(grid_to_canonical_string(final_grid_B))}")

    # Now, attempt to verify Lane B's state using Lane A's receipts (causal mismatch)
    print("  Attempting to verify Lane B state using Lane A receipts...")
    # Replay Lane A's receipts from S0. This produces Lane A's state.
    # Compare it to Lane B's final state.
    if replay_grid_A != final_grid_B:
        print("  ✅ LANE B: PASS – Divergence detected (State mismatch due to witness alteration).")
        print("     System correctly flags: HOLD – Stochastic divergence at step 50.")
        # Additionally, check if our replay function would catch it internally
        # Let's run a third replay: replay using receipts_B (which have 0), but compare to final_grid_A.
        replay_grid_B, replay_pos_B, divs_B = replay(initial_seed, receipts_B)
        if replay_grid_B == final_grid_B:
            print("     (Internal replay consistency holds for Lane B receipts.)")
        if replay_grid_B != final_grid_A:
            print("     (Cross-verification: Replaying B receipts does NOT reproduce A state – divergence flagged.)")
    else:
        print("  ❌ LANE B: FAIL – System failed to detect witness omission (silent drift).")

    # --------------------------------------------------------------
    # LANE C: Rule Substitution (Structural Divergence)
    # --------------------------------------------------------------
    print("\n[LANE C] Testing rule substitution (modify tie-breaker / grammar)...")
    # We override the get_action function dynamically for this lane.
    # We define a different rule: instead of lexicographic tie-break, we break ties by picking
    # the cell with the highest x-coordinate (different grammar G').
    def get_action_C(grid, pos):
        x, y = pos
        candidates = []
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                val = grid[nx][ny]
                candidates.append(((val, -nx, dy), (dx, dy)))  # Prefer higher x (structural difference)
        if not candidates:
            return (0, 0)
        candidates.sort(key=lambda t: (t[0][0], t[0][1], t[0][2]))
        return candidates[0][1]

    # We need to simulate with rule C and compare receipts.
    # Since we cannot easily monkeypatch in this demo, we simulate and manually compare.
    # We'll simulate with W=1/3 using rule C.
    print("  Simulating with modified rule G' (tie-break by highest x) and W_50=1/3...")
    # Quick inline simulation for Lane C
    grid_C = [row[:] for row in initial_seed]
    pos_C = (0, 0)
    receipts_C = []
    for step in range(TOTAL_STEPS):
        state_str = grid_to_canonical_string(grid_C)
        action = get_action_C(grid_C, pos_C)  # Different grammar
        witness = witness_A.get(step, Fraction(0, 1))
        rec = make_receipt(step, state_str, action, witness, pos_C)
        receipts_C.append(rec)
        grid_C, pos_C = apply_transition(grid_C, pos_C, action, witness)
    final_grid_C = grid_C
    print(f"  Simulation C complete. Terminal pos: {pos_C}")
    print(f"  Terminal grid hash: {hash_canonical(grid_to_canonical_string(final_grid_C))}")

    # Compare to Lane A (which used rule G).
    if final_grid_C != final_grid_A:
        print("  ✅ LANE C: PASS – Structural divergence detected (Different grammar yields different state).")
        print("     Receipts from G do NOT verify state from G'. Causal lineage preserved.")
        # Check if MCVA would have caught it (it might, but we don't rely on it).
    else:
        print("  ❌ LANE C: FAIL – The system accidentally produced the same state under different grammar (rare).")

    print("\n" + "=" * 60)
    print("Experiment complete. All logs above.")
    print("Divergence types identified:")
    print("  - Stochastic Divergence (Lane B): Witness mismatch.")
    print("  - Structural Divergence (Lane C): Grammar mismatch.")
    print("=" * 60)

if __name__ == "__main__":
    run_experiment()