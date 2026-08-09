"""
Universal Pattern Test Harness
Tests whether the sequence produces form across domains
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import random
import json
from enum import Enum

# ============================================================
# STEP 1: Define the Pattern as Measurable Variables
# ============================================================

@dataclass
class PatternState:
    """The state of the system at any point in the pattern."""
    differences: List[float]           # What varies
    contacts: List[tuple]              # What interacts
    constraints: List[Dict]            # What filters
    selections: List[Dict]             # What was chosen
    persistences: List[Dict]           # What remained
    feedbacks: List[Dict]              # What changed future options
    accumulations: List[Dict]          # What built up
    forms: List[Dict]                  # What emerged

@dataclass
class PatternMetrics:
    """Measure how well the pattern produced form."""
    form_stability: float              # 0-1, how stable the form is
    form_complexity: float             # 0-1, how complex the form is
    persistence_efficiency: float      # 0-1, how much persisted per interaction
    constraint_effectiveness: float    # 0-1, how well constraints filtered
    feedback_utility: float            # 0-1, how useful feedback was
    accumulation_rate: float           # 0-1, how well accumulation built

@dataclass
class PatternResult:
    """The result of running the pattern."""
    domain: str
    seed: int
    steps: int
    metrics: PatternMetrics
    final_form: Dict[str, Any]
    pattern_state: PatternState
    receipt: Dict[str, Any]           # Specificity-style receipt

# ============================================================
# STEP 2: Define the Pattern Runner
# ============================================================

class PatternRunner:
    """Runs the pattern sequence on a given domain."""
    
    def __init__(self, domain_config: Dict[str, Any], seed: int):
        self.domain = domain_config["name"]
        self.config = domain_config
        self.rng = random.Random(seed)
        self.state = PatternState(
            differences=[],
            contacts=[],
            constraints=[],
            selections=[],
            persistences=[],
            feedbacks=[],
            accumulations=[],
            forms=[]
        )
        self.step_count = 0
    
    def run(self, steps: int) -> PatternResult:
        """Run the pattern sequence for N steps."""
        
        for step in range(steps):
            self.step_count += 1
            
            # Step 1: Generate differences
            differences = self._generate_differences()
            self.state.differences.append(differences)
            
            # Step 2: Contact
            contacts = self._apply_contact(differences)
            self.state.contacts.append(contacts)
            
            # Step 3: Constraint
            constraints = self._apply_constraints(contacts)
            self.state.constraints.append(constraints)
            
            # Step 4: Selection
            selections = self._apply_selection(constraints)
            self.state.selections.append(selections)
            
            # Step 5: Persistence
            persistences = self._apply_persistence(selections)
            self.state.persistences.append(persistences)
            
            # Step 6: Feedback
            feedbacks = self._apply_feedback(persistences)
            self.state.feedbacks.append(feedbacks)
            
            # Step 7: Accumulation
            accumulations = self._apply_accumulation(feedbacks)
            self.state.accumulations.append(accumulations)
            
            # Step 8: Form
            form = self._extract_form(accumulations)
            self.state.forms.append(form)
        
        metrics = self._compute_metrics()
        receipt = self._generate_receipt(metrics)
        
        return PatternResult(
            domain=self.domain,
            seed=self.config.get("seed", 0),
            steps=steps,
            metrics=metrics,
            final_form=self.state.forms[-1],
            pattern_state=self.state,
            receipt=receipt
        )
    
    # ============================================================
    # Domain-specific implementations (override these)
    # ============================================================
    
    def _generate_differences(self) -> Dict:
        """Generate differences based on domain."""
        # Default: random differences
        return {"energy": self.rng.random()}
    
    def _apply_contact(self, differences: Dict) -> Dict:
        """Apply contact based on differences."""
        # Default: contact if differences are large enough
        return {"contacts": [("A", "B")] if differences.get("energy", 0) > 0.5 else []}
    
    def _apply_constraints(self, contacts: Dict) -> Dict:
        """Apply constraints to contacts."""
        # Default: filter by a threshold
        return {"filtered": [c for c in contacts.get("contacts", []) if self.rng.random() > 0.3]}
    
    def _apply_selection(self, constraints: Dict) -> Dict:
        """Select among constrained options."""
        # Default: choose the first
        filtered = constraints.get("filtered", [])
        return {"selected": filtered[0] if filtered else None}
    
    def _apply_persistence(self, selections: Dict) -> Dict:
        """Apply persistence to selections."""
        # Default: keep what was selected
        return {"persisted": selections.get("selected")}
    
    def _apply_feedback(self, persistences: Dict) -> Dict:
        """Apply feedback from persistences."""
        # Default: feedback modifies future differences
        persisted = persistences.get("persisted")
        return {"feedback": persisted}
    
    def _apply_accumulation(self, feedbacks: Dict) -> Dict:
        """Apply accumulation from feedback."""
        # Default: accumulate feedback
        return {"accumulated": feedbacks}
    
    def _extract_form(self, accumulations: Dict) -> Dict:
        """Extract form from accumulation."""
        # Default: form is the accumulated state
        return {"form": accumulations}
    
    # ============================================================
    # Metrics
    # ============================================================
    
    def _compute_metrics(self) -> PatternMetrics:
        """Compute metrics from the pattern state."""
        # Stability: how consistent the forms are
        forms = self.state.forms
        if len(forms) > 1:
            stability = self._compute_stability(forms)
        else:
            stability = 0.0
        
        # Complexity: how rich the forms are
        complexity = self._compute_complexity(forms[-1]) if forms else 0.0
        
        # Efficiency: persistence per interaction
        total_persistences = len(self.state.persistences)
        total_contacts = len(self.state.contacts)
        efficiency = total_persistences / max(total_contacts, 1)
        
        # Effectiveness: constraints that actually filtered
        total_constraints = len(self.state.constraints)
        effective_constraints = sum(1 for c in self.state.constraints if c.get("filtered"))
        effectiveness = effective_constraints / max(total_constraints, 1)
        
        # Utility: feedback that changed behavior
        total_feedbacks = len(self.state.feedbacks)
        useful_feedbacks = sum(1 for f in self.state.feedbacks if f.get("feedback"))
        utility = useful_feedbacks / max(total_feedbacks, 1)
        
        # Accumulation rate
        accumulation_rate = len(self.state.accumulations) / max(self.step_count, 1)
        
        return PatternMetrics(
            form_stability=stability,
            form_complexity=complexity,
            persistence_efficiency=efficiency,
            constraint_effectiveness=effectiveness,
            feedback_utility=utility,
            accumulation_rate=accumulation_rate
        )
    
    def _compute_stability(self, forms: List[Dict]) -> float:
        """Compute stability of forms over time."""
        # Simplified: compare last form to average of previous
        if len(forms) < 2:
            return 0.0
        # In a real implementation, this would compare structures
        return 0.8  # Placeholder
    
    def _compute_complexity(self, form: Dict) -> float:
        """Compute complexity of a form."""
        # Simplified: count unique elements
        if not form:
            return 0.0
        # In a real implementation, this would measure structure
        return 0.6  # Placeholder
    
    # ============================================================
    # Receipt
    # ============================================================
    
    def _generate_receipt(self, metrics: PatternMetrics) -> Dict:
        """Generate a Specificity-style receipt."""
        return {
            "domain": self.domain,
            "steps": self.step_count,
            "metrics": {
                "stability": metrics.form_stability,
                "complexity": metrics.form_complexity,
                "efficiency": metrics.persistence_efficiency,
                "effectiveness": metrics.constraint_effectiveness,
                "utility": metrics.feedback_utility,
                "accumulation": metrics.accumulation_rate
            },
            "pattern_complete": (
                metrics.form_stability > 0.5 and
                metrics.form_complexity > 0.3 and
                metrics.persistence_efficiency > 0.5 and
                metrics.accumulation_rate > 0.5
            ),
            "debt": self._classify_debt(metrics)
        }
    
    def _classify_debt(self, metrics: PatternMetrics) -> str:
        """Classify structural debt based on metrics."""
        score = (
            metrics.form_stability * 0.3 +
            metrics.form_complexity * 0.2 +
            metrics.persistence_efficiency * 0.2 +
            metrics.constraint_effectiveness * 0.15 +
            metrics.feedback_utility * 0.15
        )
        if score > 0.8:
            return "OPERATIONAL"
        elif score > 0.6:
            return "CAUTION"
        elif score > 0.4:
            return "CONSTRAINED"
        elif score > 0.2:
            return "CRITICAL"
        else:
            return "EXCEEDED"