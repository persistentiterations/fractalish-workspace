class NaturalMathDomain(PatternRunner):
    """Natural Math v5 implementation of the pattern."""
    
    def _generate_differences(self) -> Dict:
        """Generate energy gradients and pressure differences."""
        # Simulate Natural Math gradient computation
        energy = self.rng.randint(0, 1600000)
        pressure = self.rng.randint(0, 12000)
        return {
            "energy": energy,
            "pressure": pressure,
            "neighbors": [
                {"energy": self.rng.randint(0, 1600000)}
                for _ in range(self.rng.randint(0, 6))
            ]
        }
    
    def _apply_contact(self, differences: Dict) -> Dict:
        """Apply contact rules from Natural Math."""
        energy = differences["energy"]
        pressure = differences["pressure"]
        neighbors = differences["neighbors"]
        
        # Contact death if energy < tau
        tau = 5000
        if energy < tau:
            return {"contacts": [], "death": True}
        
        # Contact if unbonded neighbors within iota_sq
        iota_sq = 1
        contacts = [n for n in neighbors if n["energy"] > tau]
        
        return {"contacts": contacts, "death": False}
    
    def _apply_constraints(self, contacts: Dict) -> Dict:
        """Apply Natural Math constraints."""
        if contacts.get("death", False):
            return {"filtered": [], "alive": False}
        
        # Energy threshold constraints
        filtered = [c for c in contacts.get("contacts", []) if c["energy"] > 5000]
        
        return {"filtered": filtered, "alive": True}
    
    def _apply_selection(self, constraints: Dict) -> Dict:
        """Apply Natural Math selection (gradient direction)."""
        if not constraints.get("alive", False):
            return {"selected": None}
        
        filtered = constraints.get("filtered", [])
        if not filtered:
            # Fallback: random direction
            directions = [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]
            return {"selected": self.rng.choice(directions)}
        
        # Select highest energy neighbor
        selected = max(filtered, key=lambda n: n["energy"])
        return {"selected": selected}
    
    def _apply_persistence(self, selections: Dict) -> Dict:
        """Apply Natural Math persistence."""
        selected = selections.get("selected")
        if selected:
            # Persist as a node
            return {"persisted": {"type": "tip", "energy": selected["energy"]}}
        return {"persisted": None}
    
    def _apply_feedback(self, persistences: Dict) -> Dict:
        """Apply Natural Math feedback (pressure, energy costs)."""
        persisted = persistences.get("persisted")
        if persisted:
            # Energy cost for persistence
            persisted["energy"] -= 500  # eps_extend
            return {"feedback": persisted}
        return {"feedback": None}
    
    def _apply_accumulation(self, feedbacks: Dict) -> Dict:
        """Apply Natural Math accumulation."""
        feedback = feedbacks.get("feedback")
        if feedback:
            # Accumulate in node list
            return {"accumulated": [feedback]}
        return {"accumulated": []}
    
    def _extract_form(self, accumulations: Dict) -> Dict:
        """Extract Natural Math form."""
        accumulated = accumulations.get("accumulated", [])
        return {
            "nodes": accumulated,
            "count": len(accumulated),
            "stable": len(accumulated) > 10
        }