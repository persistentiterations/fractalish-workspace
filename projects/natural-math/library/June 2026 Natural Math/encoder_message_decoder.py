import random
import math
from typing import Tuple, Optional, List

class Node:
    def __init__(self, id: int, pos: Tuple[float, float], energy: float, signal_type: int = 0, max_bonds: int = 3):
        self.id = id
        self.pos = pos
        self.energy = energy
        self.signal_type = signal_type
        self.max_bonds = max_bonds
        self.bonds: List[int] = []
        self.received_messages: List[dict] = []

class Params:
    def __init__(self):
        self.tau = 5.0
        self.iota = 1.0
        self.r = 25.0
        self.eps_extend = 0.5
        self.E0 = 1600.0
        self.eta_sq = 0.001
        self.gamma_fallback = 0.0
        self.eps_tol = 1e-9
        self.r_sq = self.r ** 2
        self.iota_sq = self.iota ** 2
        self.deficit_strength = 15.0
        self.signal_speed = 2.0
        self.signal_decay = 0.1
        self.sense_radius = 10.0

def Q(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

def norm(v):
    return math.sqrt(v[0]**2 + v[1]**2)

def normalize(v, eps_tol=1e-9):
    n = norm(v)
    if n < eps_tol:
        return (0.0, 0.0)
    return (v[0]/n, v[1]/n)

def encode_signal(node, params):
    deficit = max(0.0, (params.E0 - node.energy) / params.E0)
    
    if deficit > 0.8:
        return {
            'source_id': node.id,
            'source_pos': node.pos,
            'signal_type': node.signal_type,
            'strength': -100.0 * deficit,
            'energy': node.energy,
            'deficit': deficit,
            'timestamp': 0
        }
    
    if node.signal_type != 0 and deficit <= 0.6:
        return {
            'source_id': node.id,
            'source_pos': node.pos,
            'signal_type': node.signal_type,
            'strength': 60.0,
            'energy': node.energy,
            'deficit': deficit,
            'timestamp': 0
        }
    
    return None

def transmit_message(message, receiver_pos, params, current_time):
    dx = receiver_pos[0] - message['source_pos'][0]
    dy = receiver_pos[1] - message['source_pos'][1]
    distance = math.sqrt(dx*dx + dy*dy)
    
    if distance > params.sense_radius:
        return None
    if distance < 1e-9:
        return None
    
    attenuation = math.exp(-params.signal_decay * distance)
    received_strength = message['strength'] * attenuation
    
    delay = distance / params.signal_speed
    arrival_time = message['timestamp'] + delay
    
    if current_time < arrival_time:
        return None
    
    return {
        'source_id': message['source_id'],
        'source_pos': message['source_pos'],
        'signal_type': message['signal_type'],
        'strength': received_strength,
        'distance': distance,
        'attenuation': attenuation,
        'arrival_time': arrival_time
    }

def decode_and_decide(node, received_messages, params):
    g = (0.0, 0.0)
    weight_sum = 0.0
    
    for msg in received_messages:
        if msg is None:
            continue
        if msg['source_id'] == node.id:
            continue
        
        dx = msg['source_pos'][0] - node.pos[0]
        dy = msg['source_pos'][1] - node.pos[1]
        d2 = dx*dx + dy*dy
        d = math.sqrt(d2)
        
        if d < 1e-9:
            continue
        
        w = 1.0 / d2
        
        if node.signal_type != 0 and msg['signal_type'] == -node.signal_type:
            effective_strength = abs(msg['strength']) * 3.0
        elif msg['strength'] < 0:
            effective_strength = msg['strength']
        else:
            effective_strength = -5.0
        
        g = (g[0] + w * effective_strength * dx,
             g[1] + w * effective_strength * dy)
        weight_sum += w
    
    if weight_sum < 1e-9:
        return (0.0, 0.0)
    
    g = (g[0] / weight_sum, g[1] / weight_sum)
    return normalize(g)

def attempt_bonding(nodes, params):
    bonds_formed = []
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            n1, n2 = nodes[i], nodes[j]
            
            if len(n1.bonds) >= n1.max_bonds or len(n2.bonds) >= n2.max_bonds:
                continue
            if n2.id in n1.bonds or n1.id in n2.bonds:
                continue
            if n1.signal_type == 0 or n2.signal_type == 0:
                continue
            if n1.signal_type != -n2.signal_type:
                continue
            
            dist = Q(n1.pos, n2.pos)
            if 0 < dist <= 4:
                avg = (n1.energy + n2.energy) / 2
                n1.energy = avg
                n2.energy = avg
                n1.pos = n2.pos
                n1.bonds.append(n2.id)
                n2.bonds.append(n1.id)
                bonds_formed.append((n1.id, n2.id))
    
    return bonds_formed

def simulation_step(nodes, params, step_num):
    all_messages = []
    for node in nodes:
        msg = encode_signal(node, params)
        if msg:
            all_messages.append(msg)
    
    for node in nodes:
        node.received_messages = []
        for msg in all_messages:
            if msg['source_id'] == node.id:
                continue
            received = transmit_message(msg, node.pos, params, step_num)
            if received:
                node.received_messages.append(received)
    
    for node in nodes:
        g = decode_and_decide(node, node.received_messages, params)
        
        # NO MOBILITY PENALTY - let the force determine behavior
        new_x = node.pos[0] + g[0] * params.eps_extend
        new_y = node.pos[1] + g[1] * params.eps_extend
        node.pos = (new_x, new_y)
        node.energy = max(node.energy - params.eps_extend, 0.0)
    
    bonds = attempt_bonding(nodes, params)
    return bonds

def test_distress_signal():
    print("=" * 70)
    print("TEST 1: Distress Signal (NO mobility penalty)")
    print("=" * 70)
    
    params = Params()
    nodes = [
        Node(0, (0.0, 0.0), 100.0, signal_type=0),
        Node(1, (3.0, 0.0), 10.0, signal_type=0),
    ]
    
    print("Initial:")
    for n in nodes:
        print(f"  Node {n.id}: pos={n.pos}, energy={n.energy:.1f}, signal={n.signal_type}")
    
    for step in range(5):
        bonds = simulation_step(nodes, params, step)
        print(f"Step {step+1}: Node0={nodes[0].pos}, Node1={nodes[1].pos}")
        if bonds:
            print(f"  Bonds: {bonds}")
    
    print("\nConclusion: Both should repel each other (mutual distress)")
    print("=" * 70)

def test_complementary_bonding():
    print("\n" + "=" * 70)
    print("TEST 2: Complementary Signals")
    print("=" * 70)
    
    params = Params()
    nodes = [
        Node(0, (0.0, 0.0), 800.0, signal_type=1, max_bonds=3),
        Node(1, (3.0, 0.0), 800.0, signal_type=-1, max_bonds=3),
    ]
    
    print("Initial:")
    for n in nodes:
        print(f"  Node {n.id}: pos={n.pos}, energy={n.energy:.1f}, signal={n.signal_type}")
    
    for step in range(8):
        bonds = simulation_step(nodes, params, step)
        print(f"Step {step+1}: Node0={nodes[0].pos}, Node1={nodes[1].pos}")
        if bonds:
            print(f"  BONDS: {bonds}")
    
    print(f"\nFinal bonds: Node0→{nodes[0].bonds}, Node1→{nodes[1].bonds}")
    print("=" * 70)

def test_mixed_signals():
    print("\n" + "=" * 70)
    print("TEST 3: Mixed Environment")
    print("=" * 70)
    
    params = Params()
    nodes = [
        Node(0, (0.0, 0.0), 800.0, signal_type=1, max_bonds=3),
        Node(1, (5.0, 0.0), 800.0, signal_type=-1, max_bonds=3),
        Node(2, (2.5, 3.0), 10.0, signal_type=0, max_bonds=3),
    ]
    
    print("Initial:")
    for n in nodes:
        print(f"  Node {n.id}: pos={n.pos}, energy={n.energy:.1f}, signal={n.signal_type}")
    
    for step in range(10):
        bonds = simulation_step(nodes, params, step)
        print(f"Step {step+1}: Node0={nodes[0].pos}, Node1={nodes[1].pos}, Node2={nodes[2].pos}")
        if bonds:
            print(f"  BONDS: {bonds}")
    
    print(f"\nFinal bonds: N0→{nodes[0].bonds}, N1→{nodes[1].bonds}, N2→{nodes[2].bonds}")
    print("=" * 70)

if __name__ == "__main__":
    test_distress_signal()
    test_complementary_bonding()
    test_mixed_signals()
