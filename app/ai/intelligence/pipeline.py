"""
Intelligence Pipeline

Orchestrates all 3 layers of the intelligence system.
This is the main entry point for AI feedback generation.

Flow:
1. Layer 1: Extract deterministic signals (pure logic)
2. Layer 2: Interpret signals with constrained AI
3. Layer 3: Generate AI judgments within guardrails
4. Package everything into traceable output
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json

from .layer1_signals import SignalEngine, Signal, SignalType, SignalSeverity
from .layer2_interpretation import InterpretationEngine, Interpretation
from .layer3_judgment import JudgmentEngine, Judgment, JudgmentType


@dataclass
class IntelligenceOutput:
    """
    Complete output from the intelligence pipeline.
    
    Contains signals, interpretations, and judgments with full traceability.
    """
    # Layer 1 outputs
    signals: List[Signal]
    signal_summary: Dict[str, Any]
    
    # Layer 2 outputs
    interpretations: List[Interpretation]
    
    # Layer 3 outputs
    judgments: List[Judgment]
    
    # Metadata
    run_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    input_hash: str = ""
    
    # Performance metrics
    processing_time_ms: float = 0
    layer1_time_ms: float = 0
    layer2_time_ms: float = 0
    layer3_time_ms: float = 0
    
    def __post_init__(self):
        if not self.run_id:
            self.run_id = self._generate_run_id()
    
    def _generate_run_id(self) -> str:
        content = f"{self.timestamp.isoformat()}-{len(self.signals)}-{len(self.judgments)}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def get_priority_feedback(self) -> List[Dict[str, Any]]:
        """Get high-priority feedback items"""
        feedback = []
        
        # Add critical signals
        for sig in self.signals:
            if sig.severity in [SignalSeverity.CRITICAL, SignalSeverity.HIGH]:
                feedback.append({
                    "type": "signal",
                    "severity": sig.severity.value,
                    "description": sig.description,
                    "source": sig.source_location
                })
        
        # Add interpretations
        for interp in self.interpretations:
            if interp.priority in ["critical", "high"]:
                feedback.append({
                    "type": "interpretation",
                    "priority": interp.priority,
                    "explanation": interp.explanation,
                    "action": interp.suggested_action
                })
        
        # Add top judgments
        for j in self.judgments[:3]:
            feedback.append({
                "type": "judgment",
                "content": j.content,
                "confidence": j.confidence,
                "caveats": j.caveats
            })
        
        return feedback
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "signal_count": len(self.signals),
            "interpretation_count": len(self.interpretations),
            "judgment_count": len(self.judgments),
            "signal_summary": self.signal_summary,
            "priority_feedback": self.get_priority_feedback(),
            "timing": {
                "total_ms": self.processing_time_ms,
                "layer1_ms": self.layer1_time_ms,
                "layer2_ms": self.layer2_time_ms,
                "layer3_ms": self.layer3_time_ms
            }
        }


class IntelligencePipeline:
    """
    Main intelligence pipeline orchestrator.
    
    Coordinates all 3 layers and ensures data flows correctly through the system.
    """
    
    def __init__(
        self,
        signal_engine: Optional[SignalEngine] = None,
        interpretation_engine: Optional[InterpretationEngine] = None,
        judgment_engine: Optional[JudgmentEngine] = None
    ):
        self.signal_engine = signal_engine or SignalEngine()
        self.interpretation_engine = interpretation_engine or InterpretationEngine()
        self.judgment_engine = judgment_engine or JudgmentEngine()
    
    async def analyze(
        self,
        resume_data: Dict[str, Any],
        job_data: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> IntelligenceOutput:
        """
        Run full intelligence pipeline.
        
        Args:
            resume_data: Parsed resume content
            job_data: Optional job description for comparison
            options: Pipeline options (which layers to run, etc.)
        
        Returns:
            Complete intelligence output with all 3 layers
        """
        import time
        start_time = time.time()
        options = options or {}
        
        # Input hash for caching/deduplication
        input_hash = self._hash_input(resume_data, job_data)
        
        # === LAYER 1: Deterministic Signals ===
        layer1_start = time.time()
        signals = self.signal_engine.extract_signals(resume_data, job_data)
        signal_summary = self.signal_engine.get_signal_summary(signals)
        layer1_time = (time.time() - layer1_start) * 1000
        
        # === LAYER 2: Constrained Interpretation ===
        layer2_start = time.time()
        interpretations = self.interpretation_engine.interpret_signals(signals)
        layer2_time = (time.time() - layer2_start) * 1000
        
        # === LAYER 3: Limited AI Judgment ===
        layer3_start = time.time()
        
        # Determine which judgment types to generate
        judgment_types = self._determine_judgment_types(signal_summary, options)
        
        context = {
            "job_data": job_data,
            "user_preferences": options.get("user_preferences", {})
        }
        
        judgments = self.judgment_engine.generate_judgments(
            signals=signals,
            interpretations=interpretations,
            judgment_types=judgment_types,
            context=context
        )
        layer3_time = (time.time() - layer3_start) * 1000
        
        # Total time
        total_time = (time.time() - start_time) * 1000
        
        return IntelligenceOutput(
            signals=signals,
            signal_summary=signal_summary,
            interpretations=interpretations,
            judgments=judgments,
            input_hash=input_hash,
            processing_time_ms=total_time,
            layer1_time_ms=layer1_time,
            layer2_time_ms=layer2_time,
            layer3_time_ms=layer3_time
        )
    
    def _hash_input(
        self,
        resume_data: Dict[str, Any],
        job_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate hash of inputs for caching"""
        content = json.dumps({
            "resume": resume_data,
            "job": job_data
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _determine_judgment_types(
        self,
        signal_summary: Dict[str, Any],
        options: Dict[str, Any]
    ) -> List[JudgmentType]:
        """Determine which judgment types to generate based on signals"""
        types = []
        
        # Always include priority and strengths
        types.append(JudgmentType.IMPROVEMENT_PRIORITY)
        types.append(JudgmentType.STRENGTH_HIGHLIGHT)
        
        # Add rewrites if there are bullet issues
        if signal_summary.get("by_severity", {}).get("high", 0) > 0:
            types.append(JudgmentType.REWRITE_SUGGESTION)
        
        # Add skill recommendations if there's a job description
        if options.get("job_data") or signal_summary.get("total_signals", 0) > 10:
            types.append(JudgmentType.SKILL_RECOMMENDATION)
        
        # User can request specific types
        requested = options.get("judgment_types", [])
        for jtype in requested:
            if isinstance(jtype, str):
                jtype = JudgmentType(jtype)
            if jtype not in types:
                types.append(jtype)
        
        return types
    
    def analyze_sync(
        self,
        resume_data: Dict[str, Any],
        job_data: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> IntelligenceOutput:
        """Synchronous version of analyze"""
        import asyncio
        return asyncio.run(self.analyze(resume_data, job_data, options))
    
    def get_quick_feedback(
        self,
        resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get quick, lightweight feedback (Layer 1 + simplified Layer 2).
        
        For real-time feedback during editing.
        """
        # Only Layer 1
        signals = self.signal_engine.extract_signals(resume_data)
        
        # Simplified summary
        critical_issues = [s for s in signals if s.severity == SignalSeverity.CRITICAL]
        high_issues = [s for s in signals if s.severity == SignalSeverity.HIGH]
        
        return {
            "status": "critical" if critical_issues else "warning" if high_issues else "good",
            "critical_count": len(critical_issues),
            "high_count": len(high_issues),
            "top_issues": [
                {"description": s.description, "severity": s.severity.value}
                for s in (critical_issues + high_issues)[:5]
            ]
        }
