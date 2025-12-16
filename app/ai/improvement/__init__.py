"""
Auto-Improvement Pipeline

Weekly automated pipeline for AI system improvement:
1. Sample frozen test cases
2. Generate candidate improvements (prompts, configs)
3. Run side-by-side evaluation
4. Score and compare
5. Promote superior versions (or reject regressions)
6. Maintain full audit trail
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import json
import random


class ImprovementStatus(str, Enum):
    """Status of an improvement candidate"""
    PENDING = "pending"           # Awaiting evaluation
    EVALUATING = "evaluating"     # Currently being evaluated
    PROMOTED = "promoted"         # Passed evaluation, promoted
    REJECTED = "rejected"         # Failed evaluation
    ROLLED_BACK = "rolled_back"   # Was promoted, then rolled back


@dataclass
class FrozenTestCase:
    """
    A frozen test case for consistent evaluation.
    
    These are real examples that serve as benchmarks.
    """
    case_id: str
    
    # Input
    input_content: str  # Resume or other input
    context: Dict[str, Any]
    
    # Expected outputs (golden examples)
    expected_output: Optional[str] = None
    expected_characteristics: List[str] = field(default_factory=list)
    
    # Metadata
    category: str = "general"  # skill_gap, bullet_rewrite, ats, etc.
    difficulty: str = "medium"  # easy, medium, hard
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Historical scores
    baseline_score: Optional[float] = None
    
    def __post_init__(self):
        if not self.case_id:
            self.case_id = hashlib.sha256(
                self.input_content[:100].encode()
            ).hexdigest()[:12]


@dataclass
class ImprovementCandidate:
    """
    A candidate improvement to be evaluated.
    """
    candidate_id: str
    
    # What's being improved
    improvement_type: str  # "prompt", "model", "config"
    target_id: str  # prompt_id, model_id, etc.
    
    # The change
    current_version: str
    proposed_version: str
    change_description: str
    
    # Evaluation results
    status: ImprovementStatus = ImprovementStatus.PENDING
    evaluation_scores: Dict[str, float] = field(default_factory=dict)
    
    # Comparison
    baseline_score: Optional[float] = None
    candidate_score: Optional[float] = None
    improvement_delta: Optional[float] = None
    
    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    evaluated_at: Optional[datetime] = None
    decision_reason: str = ""


@dataclass
class ImprovementCycle:
    """
    A complete improvement cycle (typically weekly).
    """
    cycle_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Test cases used
    test_cases: List[str] = field(default_factory=list)  # case_ids
    
    # Candidates evaluated
    candidates: List[str] = field(default_factory=list)  # candidate_ids
    
    # Results
    promoted_count: int = 0
    rejected_count: int = 0
    rolled_back_count: int = 0
    
    # Metrics
    average_improvement: float = 0
    safety_incidents: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "test_case_count": len(self.test_cases),
            "candidate_count": len(self.candidates),
            "promoted": self.promoted_count,
            "rejected": self.rejected_count,
            "average_improvement": self.average_improvement
        }


class ImprovementPipeline:
    """
    Auto-improvement pipeline for continuous AI enhancement.
    
    Weekly cycle:
    1. Sample test cases from frozen corpus
    2. Generate candidate improvements
    3. Evaluate candidates against baseline
    4. Promote winners, reject regressions
    5. Log everything for audit
    """
    
    # Thresholds
    MIN_IMPROVEMENT_THRESHOLD = 0.05  # 5% improvement required
    SAFETY_SCORE_THRESHOLD = 0.9       # Must maintain safety
    QUALITY_SCORE_THRESHOLD = 0.7      # Minimum quality
    STABILITY_THRESHOLD = 0.8          # Cannot regress more than 20%
    
    def __init__(
        self,
        test_case_store: Optional[Dict[str, FrozenTestCase]] = None,
        ai_orchestrator=None,
        evaluation_engine=None
    ):
        self.test_cases: Dict[str, FrozenTestCase] = test_case_store or {}
        self.candidates: Dict[str, ImprovementCandidate] = {}
        self.cycles: List[ImprovementCycle] = []
        self.ai_orchestrator = ai_orchestrator
        self.evaluation_engine = evaluation_engine
        
        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
    
    def add_test_case(self, test_case: FrozenTestCase) -> None:
        """Add a frozen test case to the corpus"""
        self.test_cases[test_case.case_id] = test_case
        self._log("add_test_case", test_case.case_id)
    
    def sample_test_cases(
        self,
        count: int = 50,
        category: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> List[FrozenTestCase]:
        """
        Sample test cases for evaluation.
        
        Uses stratified sampling to ensure coverage.
        """
        candidates = list(self.test_cases.values())
        
        # Filter by category
        if category:
            candidates = [c for c in candidates if c.category == category]
        
        # Filter by difficulty
        if difficulty:
            candidates = [c for c in candidates if c.difficulty == difficulty]
        
        # Stratified sampling
        if len(candidates) <= count:
            return candidates
        
        # Try to get even distribution across categories
        by_category: Dict[str, List[FrozenTestCase]] = {}
        for case in candidates:
            if case.category not in by_category:
                by_category[case.category] = []
            by_category[case.category].append(case)
        
        samples = []
        per_category = max(1, count // len(by_category))
        
        for cat_cases in by_category.values():
            samples.extend(random.sample(cat_cases, min(per_category, len(cat_cases))))
        
        # Fill remainder randomly
        remaining = [c for c in candidates if c not in samples]
        if len(samples) < count and remaining:
            samples.extend(random.sample(remaining, min(count - len(samples), len(remaining))))
        
        return samples[:count]
    
    async def run_improvement_cycle(
        self,
        candidates: List[ImprovementCandidate],
        test_case_count: int = 50
    ) -> ImprovementCycle:
        """
        Run a complete improvement cycle.
        
        Args:
            candidates: Improvement candidates to evaluate
            test_case_count: Number of test cases to use
            
        Returns:
            Complete cycle results
        """
        cycle = ImprovementCycle(
            cycle_id=self._generate_cycle_id(),
            start_time=datetime.utcnow()
        )
        
        # Sample test cases
        test_cases = self.sample_test_cases(test_case_count)
        cycle.test_cases = [tc.case_id for tc in test_cases]
        
        # Evaluate each candidate
        for candidate in candidates:
            self.candidates[candidate.candidate_id] = candidate
            cycle.candidates.append(candidate.candidate_id)
            
            # Run evaluation
            result = await self._evaluate_candidate(candidate, test_cases)
            
            # Make promotion decision
            if self._should_promote(candidate):
                candidate.status = ImprovementStatus.PROMOTED
                candidate.decision_reason = "Passed all thresholds"
                cycle.promoted_count += 1
            else:
                candidate.status = ImprovementStatus.REJECTED
                candidate.decision_reason = self._get_rejection_reason(candidate)
                cycle.rejected_count += 1
            
            candidate.evaluated_at = datetime.utcnow()
        
        # Calculate cycle metrics
        improvements = [
            c.improvement_delta for c in candidates 
            if c.improvement_delta is not None
        ]
        cycle.average_improvement = sum(improvements) / len(improvements) if improvements else 0
        
        cycle.end_time = datetime.utcnow()
        self.cycles.append(cycle)
        
        self._log("complete_cycle", cycle.cycle_id, {
            "promoted": cycle.promoted_count,
            "rejected": cycle.rejected_count,
            "avg_improvement": cycle.average_improvement
        })
        
        return cycle
    
    async def _evaluate_candidate(
        self,
        candidate: ImprovementCandidate,
        test_cases: List[FrozenTestCase]
    ) -> None:
        """Evaluate a single candidate against test cases"""
        candidate.status = ImprovementStatus.EVALUATING
        
        baseline_scores = []
        candidate_scores = []
        
        for test_case in test_cases:
            # Run baseline
            baseline_output = await self._run_with_version(
                candidate.improvement_type,
                candidate.target_id,
                candidate.current_version,
                test_case
            )
            baseline_score = await self._score_output(baseline_output, test_case)
            baseline_scores.append(baseline_score)
            
            # Run candidate
            candidate_output = await self._run_with_version(
                candidate.improvement_type,
                candidate.target_id,
                candidate.proposed_version,
                test_case
            )
            candidate_score = await self._score_output(candidate_output, test_case)
            candidate_scores.append(candidate_score)
        
        # Aggregate scores
        candidate.baseline_score = sum(baseline_scores) / len(baseline_scores)
        candidate.candidate_score = sum(candidate_scores) / len(candidate_scores)
        candidate.improvement_delta = candidate.candidate_score - candidate.baseline_score
        
        # Store detailed scores
        candidate.evaluation_scores = {
            "baseline_avg": candidate.baseline_score,
            "candidate_avg": candidate.candidate_score,
            "improvement": candidate.improvement_delta,
            "test_case_count": len(test_cases),
            "wins": sum(1 for b, c in zip(baseline_scores, candidate_scores) if c > b),
            "losses": sum(1 for b, c in zip(baseline_scores, candidate_scores) if c < b)
        }
    
    async def _run_with_version(
        self,
        improvement_type: str,
        target_id: str,
        version: str,
        test_case: FrozenTestCase
    ) -> str:
        """Run a specific version on a test case"""
        # This would use the AI orchestrator with specific version
        # Placeholder implementation
        return f"Output for {target_id} v{version}"
    
    async def _score_output(
        self,
        output: str,
        test_case: FrozenTestCase
    ) -> float:
        """Score an output against a test case"""
        if self.evaluation_engine:
            report = self.evaluation_engine.evaluate(output, {
                "original_content": test_case.input_content
            })
            return report.overall_score
        
        # Fallback scoring
        return 0.7  # Neutral score
    
    def _should_promote(self, candidate: ImprovementCandidate) -> bool:
        """Decide if candidate should be promoted"""
        # Must have evaluation results
        if candidate.candidate_score is None or candidate.baseline_score is None:
            return False
        
        # Must show improvement
        if candidate.improvement_delta < self.MIN_IMPROVEMENT_THRESHOLD:
            return False
        
        # Must maintain quality
        if candidate.candidate_score < self.QUALITY_SCORE_THRESHOLD:
            return False
        
        # Must not regress too much on any dimension
        scores = candidate.evaluation_scores
        if scores.get("losses", 0) > scores.get("test_case_count", 1) * 0.3:
            return False  # Too many regressions
        
        return True
    
    def _get_rejection_reason(self, candidate: ImprovementCandidate) -> str:
        """Get human-readable rejection reason"""
        if candidate.improvement_delta is None:
            return "Evaluation incomplete"
        
        if candidate.improvement_delta < self.MIN_IMPROVEMENT_THRESHOLD:
            return f"Insufficient improvement: {candidate.improvement_delta:.2%} (need {self.MIN_IMPROVEMENT_THRESHOLD:.0%})"
        
        if candidate.candidate_score < self.QUALITY_SCORE_THRESHOLD:
            return f"Quality below threshold: {candidate.candidate_score:.2f} (need {self.QUALITY_SCORE_THRESHOLD:.2f})"
        
        scores = candidate.evaluation_scores
        if scores.get("losses", 0) > scores.get("test_case_count", 1) * 0.3:
            return f"Too many regressions: {scores.get('losses')} of {scores.get('test_case_count')}"
        
        return "Unknown reason"
    
    def rollback_candidate(self, candidate_id: str, reason: str) -> bool:
        """Rollback a promoted candidate"""
        if candidate_id not in self.candidates:
            return False
        
        candidate = self.candidates[candidate_id]
        if candidate.status != ImprovementStatus.PROMOTED:
            return False
        
        candidate.status = ImprovementStatus.ROLLED_BACK
        candidate.decision_reason = f"Rolled back: {reason}"
        
        self._log("rollback", candidate_id, {"reason": reason})
        
        return True
    
    def get_audit_trail(
        self,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get audit trail of all actions"""
        if since is None:
            return self._audit_log
        
        return [
            entry for entry in self._audit_log
            if datetime.fromisoformat(entry["timestamp"]) >= since
        ]
    
    def _generate_cycle_id(self) -> str:
        """Generate unique cycle ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"cycle_{timestamp}"
    
    def _log(
        self,
        action: str,
        target_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log action for audit trail"""
        self._audit_log.append({
            "action": action,
            "target_id": target_id,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })


class ShadowModeRunner:
    """
    Run new versions in shadow mode before promotion.
    
    Shadow mode runs the new version alongside production,
    comparing results without affecting users.
    """
    
    def __init__(
        self,
        ai_orchestrator=None,
        evaluation_engine=None,
        log_results: bool = True
    ):
        self.ai_orchestrator = ai_orchestrator
        self.evaluation_engine = evaluation_engine
        self.log_results = log_results
        
        self.shadow_results: List[Dict[str, Any]] = []
    
    async def run_shadow(
        self,
        production_version: str,
        shadow_version: str,
        input_content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run both versions and compare.
        
        Only production result is returned to user.
        Shadow result is logged for comparison.
        """
        # Run production
        production_output = await self._run_version(
            production_version, input_content, context
        )
        
        # Run shadow (async, don't block)
        shadow_output = await self._run_version(
            shadow_version, input_content, context
        )
        
        # Compare
        comparison = await self._compare_outputs(
            production_output, shadow_output, input_content
        )
        
        # Log
        if self.log_results:
            self.shadow_results.append({
                "timestamp": datetime.utcnow().isoformat(),
                "production_version": production_version,
                "shadow_version": shadow_version,
                "comparison": comparison
            })
        
        return {
            "production_output": production_output,
            "shadow_comparison": comparison
        }
    
    async def _run_version(
        self,
        version: str,
        input_content: str,
        context: Dict[str, Any]
    ) -> str:
        """Run a specific version"""
        # Would use AI orchestrator
        return f"Output from version {version}"
    
    async def _compare_outputs(
        self,
        production: str,
        shadow: str,
        input_content: str
    ) -> Dict[str, Any]:
        """Compare production and shadow outputs"""
        if self.evaluation_engine:
            prod_report = self.evaluation_engine.evaluate(production, {"original_content": input_content})
            shadow_report = self.evaluation_engine.evaluate(shadow, {"original_content": input_content})
            
            return {
                "production_score": prod_report.overall_score,
                "shadow_score": shadow_report.overall_score,
                "shadow_improvement": shadow_report.overall_score - prod_report.overall_score,
                "shadow_better": shadow_report.overall_score > prod_report.overall_score
            }
        
        return {
            "production_score": None,
            "shadow_score": None,
            "note": "Evaluation engine not available"
        }
    
    def get_shadow_stats(self) -> Dict[str, Any]:
        """Get statistics from shadow runs"""
        if not self.shadow_results:
            return {"runs": 0}
        
        improvements = [
            r["comparison"]["shadow_improvement"]
            for r in self.shadow_results
            if r["comparison"].get("shadow_improvement") is not None
        ]
        
        shadow_wins = sum(
            1 for r in self.shadow_results
            if r["comparison"].get("shadow_better", False)
        )
        
        return {
            "runs": len(self.shadow_results),
            "shadow_wins": shadow_wins,
            "shadow_win_rate": shadow_wins / len(self.shadow_results) if self.shadow_results else 0,
            "average_improvement": sum(improvements) / len(improvements) if improvements else 0
        }
