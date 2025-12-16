"""
3-Layer Intelligence System

The core architecture for AI feedback generation.

Layer 1 — Deterministic Signal Engine
  Pure logic, no AI. Rules, thresholds, pattern matching.
  Output: Concrete signals (facts)
  
Layer 2 — Constrained AI Interpretation  
  AI translates signals into human-readable explanations.
  Strictly bounded by Layer 1 outputs.
  
Layer 3 — Limited AI Judgment
  AI provides suggestions, alternatives, reasoning.
  Must cite Layer 1/2 signals. Cannot contradict.

INVARIANT: LLMs may NEVER bypass Layer 1.
"""
from .layer1_signals import SignalEngine, Signal, SignalType, SignalSeverity
from .layer2_interpretation import InterpretationEngine, Interpretation
from .layer3_judgment import JudgmentEngine, Judgment
from .pipeline import IntelligencePipeline

__all__ = [
    "SignalEngine",
    "Signal",
    "SignalType", 
    "SignalSeverity",
    "InterpretationEngine",
    "Interpretation",
    "JudgmentEngine",
    "Judgment",
    "IntelligencePipeline"
]
