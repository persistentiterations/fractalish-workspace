
"""
Natural Math v5.1 — MINIMAL EMERGENT CRYSTAL STARTER
=====================================================
Simplest possible emergent crystal for user testing.

HOW TO USE:
1. Copy this file
2. Adjust PARAMETERS section below
3. Run: python crystal_starter.py
4. Watch console output for growth phases
5. Modify parameters to see different behaviors

CORE IDEA:
- Nodes have types {-1, 0, +1}
- +1 and -1 attract and bond (complementary)
- Bonds are flexible springs (not rigid)
- Sun moves in arc, gives energy only when overhead
- Surface nodes (with free bond slots) grow toward sun
- Nodes store excess energy, use it when dark
- Nodes die when energy < threshold

That's it. Crystal structure emerges from these simple rules.
"""

import numpy as np
import matplotlib.pyplot as plt
import random

# ============================================================
# PARAMETERS — ADJUST THESE TO TEST DIFFERENT BEHAVIORS
# ============================================================

N_START = 12          # Starting nodes
MAX_NODES = 200       # Max population cap
STEPS = 500           # Simulation steps

# Energy
E0 = 200              # Starting energy per node
TAU = 3               # Death threshold (energy < TAU = die)
SUN_RATE = 4.0        # Energy per step from sun when directly overhead
STORE_MAX = 80        # Max energy storage per node
BASE_COST = 0.5       # Energy cost per step to stay alive

# Sun movement
SUN_R = 25            # Orbit radius
SUN_H = 15            # Height above ground
SUN_SPEED = 0.03      # Radians per step (0.01 = slow, 0.05 = fast)
DAWN = 20             # Step when sun rises
DUSK = 200            # Step when sun sets

# Bonding
BOND_TARGET = 2.0     # Ideal bond distance
BOND_MIN = 1.0        # Closest allowed
BOND_MAX = 3.5        # Farthest allowed
MAX_BONDS = 4         # Max bonds per node
BOND_ANGLE_MIN = 50   # Minimum angle between bonds (degrees)

# Movement
STEP_SIZE = 0.3       # How fast nodes move
NOISE = 0.05          # Random movement (Brownian)

# Bifurcation (growth)
BIFURC_MIN_E = 30     # Minimum energy to bifurcate
BIFURC_PRESSURE = 2   # Minimum pressure to bifurcate
BIFURC_COOLDOWN = 15  # Steps between bifurcations per node

# ============================================================
# SETUP
# ============================================================

random.seed(42)
np.random.seed(42)

# Node arrays
pos = np.random.uniform(-3, 3, (N_START, 2))
pos[:, 1] -= 3        # Start below "ground"
energy = np.ones(N_START) * E0
stored = np.zeros(N_START)
type_sig = np.random.choice([-1, 0, 1], N_START)
alive = np.ones(N_START, dtype=bool)
pressure = np.zeros(N_START)
last_bifurc = np.full(N_START, -999)

# Bonds: list of sets
bonds = [set() for _ in range(N_START)]

# Sun
sun_angle = -np.pi / 2
sun_pos = np.array([0.0, -SUN_R])

# History for visualization
history = []

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sun_intensity(step, node_pos):
    """Energy rate from sun at node position. 0 if night."""
    if step < DAWN or step > DUSK:
        return 0.0
    height = max(0, np.sin(sun_angle))
    d = np.linalg.norm(node_pos - sun_pos)
    falloff = np.exp(-d / 20)
    return SUN_RATE * height * falloff

def is_surface(i):
    """Surface nodes have room for more bonds or large angular gaps."""
    if len(bonds[i]) < 3:
        return True
    angles = []
    for b in bonds[i]:
        if b < len(pos):
            bd = pos[b] - pos[i]
            angles.append(np.arctan2(bd[1], bd[0]))
    if len(angles) < 2:
        return True
    angles = sorted(angles)
    max_gap = 0
    for k in range(len(angles)):
        gap = angles[(k+1) % len(angles)] - angles[k]
        if gap < 0:
            gap += 2 * np.pi
        max_gap = max(max_gap, gap)
    return max_gap > 2.1  # ~120 degrees

# ============================================================
# MAIN LOOP
# ============================================================

print("=" * 60)
print("NATURAL MATH v5.1 — MINIMAL EMERGENT CRYSTAL")
print("=" * 60)
print(f"Nodes: {N_START} start, {MAX_NODES} max")
print(f"Sun: rises step {DAWN}, sets step {DUSK}")
print(f"Bonds: target={BOND_TARGET}, max={MAX_BONDS}, angle>{BOND_ANGLE_MIN}°")
print(f"Growth: E>{BIFURC_MIN_E}, pressure>{BIFURC_PRESSURE}")
print("=" * 60)

for t in range(STEPS):
    n_alive = int(np.sum(alive))
    if n_alive == 0:
        print(f"\n*** EXTINCTION at step {t} ***")
        break

    # Update sun
    if DAWN <= t <= DUSK:
        sun_angle = -np.pi/2 + (t - DAWN) * SUN_SPEED
        sun_pos = np.array([SUN_R * np.cos(sun_angle), SUN_H * np.sin(sun_angle)])

    alive_idx = np.where(alive)[0]

    # === FORCES ===
    forces = np.zeros((len(pos), 2))
    for i in alive_idx:
        for j in alive_idx:
            if i == j:
                continue
            dx = pos[j, 0] - pos[i, 0]
            dy = pos[j, 1] - pos[i, 1]
            d2 = dx*dx + dy*dy
            if d2 > 225 or d2 < 1e-9:  # Sense radius = 15
                continue
            d = np.sqrt(d2)

            # Morse-like force
            if d < 0.8:
                f = -500 * (0.8 - d)  # Strong repulsion
            elif d < 4.0:
                f = 30 * (d - BOND_TARGET)  # Attraction well
            else:
                f = 0

            # Complementarity
            if type_sig[i] != 0 and type_sig[j] != 0 and type_sig[i] == -type_sig[j]:
                f += 15  # Attract
            elif type_sig[i] != 0 and type_sig[j] != 0 and type_sig[i] == type_sig[j]:
                f -= 20  # Repel

            direction = np.array([dx, dy]) / (d + 1e-9)
            forces[i] += f * direction

        # Phototropism (grow toward sun)
        if DAWN <= t <= DUSK:
            to_sun = sun_pos - pos[i]
            d_sun = np.linalg.norm(to_sun)
            if d_sun > 1e-9:
                forces[i] += 0.3 * sun_intensity(t, pos[i]) * to_sun / d_sun

        forces[i] += np.random.normal(0, NOISE, 2)

    # === MOVE ===
    for i in alive_idx:
        fn = np.linalg.norm(forces[i])
        if fn > 0.01 and energy[i] > 0.5:
            pos[i] += STEP_SIZE * forces[i] / fn
            energy[i] -= 0.5

    # === BOND RELAXATION (flexible springs) ===
    for i in alive_idx:
        for j in bonds[i]:
            if j <= i or not alive[j]:
                continue
            dx = pos[j, 0] - pos[i, 0]
            dy = pos[j, 1] - pos[i, 1]
            d = np.sqrt(dx*dx + dy*dy)
            if d > 1e-9:
                stretch = d - BOND_TARGET
                if abs(stretch) > 0.3:  # Slack zone
                    correction = 0.3 * stretch * np.array([dx, dy]) / d
                    pos[i] += correction * 0.5
                    pos[j] -= correction * 0.5

    # === BONDING ===
    for i in alive_idx:
        for j in alive_idx:
            if i >= j:
                continue
            if type_sig[i] == 0 or type_sig[j] == 0 or type_sig[i] != -type_sig[j]:
                continue
            if j in bonds[i]:
                continue
            if len(bonds[i]) >= MAX_BONDS or len(bonds[j]) >= MAX_BONDS:
                continue

            dx = pos[j, 0] - pos[i, 0]
            dy = pos[j, 1] - pos[i, 1]
            d = np.sqrt(dx*dx + dy*dy)
            if d < BOND_MIN or d > BOND_MAX:
                continue

            # Angle check
            new_dir = np.array([dx, dy]) / (d + 1e-9)
            ok = True
            for b in bonds[i]:
                if b < len(pos):
                    bd = pos[b] - pos[i]
                    bd_norm = np.linalg.norm(bd)
                    if bd_norm > 1e-9:
                        angle = np.degrees(np.arccos(max(-1, min(1, np.dot(new_dir, bd/bd_norm)))))
                        if angle < BOND_ANGLE_MIN:
                            ok = False
                            break
            if not ok:
                continue

            for b in bonds[j]:
                if b < len(pos):
                    bd = pos[b] - pos[j]
                    bd_norm = np.linalg.norm(bd)
                    if bd_norm > 1e-9:
                        angle = np.degrees(np.arccos(max(-1, min(1, np.dot(-new_dir, bd/bd_norm)))))
                        if angle < BOND_ANGLE_MIN:
                            ok = False
                            break
            if not ok:
                continue

            # Bond!
            bonds[i].add(j)
            bonds[j].add(i)
            avg_e = 0.5 * (energy[i] + energy[j])
            energy[i] = avg_e
            energy[j] = avg_e

    # === METABOLISM ===
    for i in alive_idx:
        se = sun_intensity(t, pos[i])
        energy[i] += se

        # Store excess
        if energy[i] > E0:
            excess = energy[i] - E0
            stored[i] = min(stored[i] + excess * 0.5, STORE_MAX)
            energy[i] = E0

        # Use stored when dark
        if se < 0.1 and stored[i] > 0:
            use = min(stored[i], 2.0)
            energy[i] += use
            stored[i] -= use

        energy[i] -= BASE_COST

    # === PRESSURE ===
    for i in alive_idx:
        pressure[i] = (pressure[i] + 2.0) * 0.85 + len(bonds[i]) * 0.2

    # === BIFURCATION (surface growth toward sun) ===
    new_count = 0
    for i in alive_idx:
        if len(pos) >= MAX_NODES:
            break
        if t - last_bifurc[i] < BIFURC_COOLDOWN:
            continue
        if not is_surface(i):
            continue
        if len(bonds[i]) < 2:
            continue
        if energy[i] < BIFURC_MIN_E:
            continue
        if pressure[i] < BIFURC_PRESSURE:
            continue
        if sun_intensity(t, pos[i]) < 0.5:
            continue

        # Split energy
        energy[i] *= 0.6

        # Push toward sun
        to_sun = sun_pos - pos[i]
        d_sun = np.linalg.norm(to_sun)
        if d_sun > 1e-9:
            push = to_sun / d_sun
        else:
            push = np.array([0, 1])

        # Create child
        new_pos = pos[i] + 2.0 * push
        pos = np.vstack([pos, new_pos])
        energy = np.append(energy, E0 * 0.4)
        stored = np.append(stored, 0)
        type_sig = np.append(type_sig, -type_sig[i])  # Opposite type
        alive = np.append(alive, True)
        pressure = np.append(pressure, 0)
        last_bifurc = np.append(last_bifurc, t)
        bonds.append(set())
        new_count += 1
        last_bifurc[i] = t
        pressure[i] = 0

    # === DEATH ===
    for i in range(len(energy)):
        if alive[i] and energy[i] < TAU:
            alive[i] = False

    # === RECORD ===
    if t % 20 == 0 or new_count > 0:
        alive_idx = np.where(alive)[0]
        n_bonds = sum(len(bonds[i]) for i in alive_idx) // 2
        ys = pos[alive, 1] if len(alive_idx) > 0 else [0]
        height = max(ys) - min(ys) if len(ys) > 0 else 0

        history.append({
            'step': t,
            'n_alive': int(np.sum(alive)),
            'n_total': len(pos),
            'n_bonds': n_bonds,
            'height': height,
            'avg_E': np.mean(energy[alive]) if len(alive_idx) > 0 else 0,
            'positions': pos[alive].copy(),
            'types': type_sig[alive].copy(),
        })

        phase = "DAY" if DAWN <= t <= DUSK else "NIGHT"
        print(f"[{phase}] S{t:3d}: {int(np.sum(alive))}a/{len(pos)}t bonds={n_bonds} h={height:.1f} avgE={np.mean(energy[alive]):.1f} (+{new_count})")

# ============================================================
# VISUALIZATION
# ============================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 12))
fig.suptitle('Natural Math v5.1 — Minimal Emergent Crystal', fontsize=14, fontweight='bold')

# Plot 1: Final structure
ax = axes[0, 0]
if len(history) > 0:
    final = history[-1]
    pos_final = final['positions']
    types_final = final['types']
    colors = {-1: '#3498db', 0: '#95a5a6', 1: '#e74c3c'}

    # Draw bonds
    alive_mask = alive[:len(pos_final)] if len(alive) >= len(pos_final) else alive
    for i in range(len(bonds)):
        if i >= len(pos_final) or not alive[i]:
            continue
        for j in bonds[i]:
            if j > i and j < len(pos_final) and alive[j]:
                ax.plot([pos[i,0], pos[j,0]], [pos[i,1], pos[j,1]], 'k-', lw=0.5, alpha=0.3)

    # Draw nodes
    for i in range(len(pos_final)):
        c = colors.get(types_final[i], '#95a5a6')
        ax.scatter(pos_final[i,0], pos_final[i,1], c=c, s=40, edgecolors='k', linewidths=0.5)

    ax.set_aspect('equal')
    ax.set_xlim(-15, 15)
    ax.set_ylim(-10, 15)
    ax.set_title(f'Final (step {final["step"]}, {final["n_alive"]} alive)')
    ax.grid(True, alpha=0.3)

# Plot 2: Growth
ax = axes[0, 1]
steps = [h['step'] for h in history]
alive_c = [h['n_alive'] for h in history]
total_c = [h['n_total'] for h in history]
bond_c = [h['n_bonds'] for h in history]
ax.plot(steps, alive_c, 'b-', lw=2, label='Alive', marker='o', markersize=3)
ax.plot(steps, total_c, 'g-', lw=2, label='Total', marker='s', markersize=3)
ax.plot(steps, bond_c, 'r-', lw=2, label='Bonds', marker='^', markersize=3)
ax.axvline(x=DAWN, color='orange', linestyle='--', alpha=0.5, label='Dawn')
ax.axvline(x=DUSK, color='purple', linestyle='--', alpha=0.5, label='Dusk')
ax.set_xlabel('Step')
ax.set_ylabel('Count')
ax.set_title('Growth')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Plot 3: Height
ax = axes[1, 0]
heights = [h['height'] for h in history]
ax.plot(steps, heights, 'g-', lw=2, marker='o', markersize=3)
ax.axvline(x=DAWN, color='orange', linestyle='--', alpha=0.5)
ax.axvline(x=DUSK, color='purple', linestyle='--', alpha=0.5)
ax.set_xlabel('Step')
ax.set_ylabel('Height')
ax.set_title('Vertical Growth')
ax.grid(True, alpha=0.3)

# Plot 4: Energy
ax = axes[1, 1]
avg_E = [h['avg_E'] for h in history]
ax.plot(steps, avg_E, 'purple', lw=2, marker='D', markersize=3)
ax.axhline(y=TAU, color='red', linestyle='--', alpha=0.5, label=f'Death ({TAU})')
ax.axvline(x=DAWN, color='orange', linestyle='--', alpha=0.5)
ax.axvline(x=DUSK, color='purple', linestyle='--', alpha=0.5)
ax.set_xlabel('Step')
ax.set_ylabel('Avg Energy')
ax.set_title('Energy')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('crystal_starter_output.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nSaved: crystal_starter_output.png")
