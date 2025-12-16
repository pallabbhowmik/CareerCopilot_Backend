"""
AI Evaluation System

Comprehensive evaluation for AI outputs:
- Rule-based validators (fast, deterministic)
- AI-as-judge evaluation (quality assessment)
- Safety checks (tone, overclaims, harmful content)
- Historical comparison (consistency tracking)
"""
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re
import hashlib


class EvaluationResult(str, Enum):
    """Evaluation outcomes"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class EvaluationCategory(str, Enum):
    """Categories of evaluation"""
    SAFETY = "safety"
    QUALITY = "quality"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    TONE = "tone"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    validator_name: str
    category: EvaluationCategory
    result: EvaluationResult
    score: float  # 0-1
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """Complete evaluation report"""
    output_hash: str
    timestamp: datetime
    
    # Results
    validations: List[ValidationResult]
    overall_result: EvaluationResult
    overall_score: float
    
    # Category scores
    safety_score: float
    quality_score: float
    consistency_score: float
    
    # Metadata
    evaluation_time_ms: float
    evaluator_version: str = "1.0.0"
    
    def passes_threshold(self, min_score: float = 0.7) -> bool:
        return self.overall_score >= min_score and self.overall_result != EvaluationResult.FAIL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_hash": self.output_hash,
            "overall_result": self.overall_result.value,
            "overall_score": self.overall_score,
            "safety_score": self.safety_score,
            "quality_score": self.quality_score,
            "consistency_score": self.consistency_score,
            "validation_count": len(self.validations),
            "failed_validations": [
                v.validator_name for v in self.validations 
                if v.result == EvaluationResult.FAIL
            ],
            "evaluation_time_ms": self.evaluation_time_ms
        }


# =============================================================================
# RULE-BASED VALIDATORS
# =============================================================================

class BaseValidator:
    """Base class for validators"""
    name: str = "base_validator"
    category: EvaluationCategory = EvaluationCategory.QUALITY
    weight: float = 1.0
    
    def validate(self, output: str, context: Dict[str, Any]) -> ValidationResult:
        raise NotImplementedError


class ForbiddenPhraseValidator(BaseValidator):
    """Checks for forbidden phrases that AI should never output"""
    name = "forbidden_phrase_check"
    category = EvaluationCategory.SAFETY
    weight = 2.0  # High weight - safety critical
    
    FORBIDDEN_PHRASES = [
        # Guarantees
        ("guaranteed", "Must not guarantee outcomes"),
        ("will definitely", "Must not promise definite results"),
        ("100% success", "Must not claim 100% success"),
        ("you will get", "Must not promise outcomes"),
        ("you'll definitely", "Must not promise outcomes"),
        
        # Overconfidence
        ("perfect resume", "Must not claim perfection"),
        ("no improvements needed", "Should always offer constructive feedback"),
        ("flawless", "Must not claim perfection"),
        
        # Harmful comparisons
        ("better than other candidates", "Must not compare to others"),
        ("worst resume", "Must not be harsh/demeaning"),
        ("terrible", "Must not use harsh language"),
        
        # False authority
        ("as a hiring manager", "Must not claim false roles"),
        ("from my experience hiring", "Must not claim false experience"),
    ]
    
    def validate(self, output: str, context: Dict[str, Any]) -> ValidationResult:
        output_lower = output.lower()
        violations = []
        
        for phrase, reason in self.FORBIDDEN_PHRASES:
            if phrase in output_lower:
                violations.append(f"'{phrase}': {reason}")
        
        if violations:
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.FAIL,
                score=0,
                message=f"Found {len(violations)} forbidden phrase(s)",
                details={"violations": violations}
            )
        
        return ValidationResult(
            validator_name=self.name,
            category=self.category,
            result=EvaluationResult.PASS,
            score=1.0,
            message="No forbidden phrases found"
        )


class UncertaintyExpressionValidator(BaseValidator):
    """Ensures AI expresses appropriate uncertainty"""
    name = "uncertainty_expression"
    category = EvaluationCategory.SAFETY
    weight = 1.5
    
    UNCERTAINTY_PHRASES = [
        "may", "might", "could", "consider", "suggest",
        "typically", "often", "in many cases", "potentially",
        "tends to", "generally", "can help"
    ]
    
    CERTAINTY_PHRASES = [
        "will", "must", "always", "never", "definitely",
        "certainly", "absolutely", "guaranteed"
    ]
    
    def validate(self, output: str, context: Dict[str, Any]) -> ValidationResult:
        output_lower = output.lower()
        
        # Count uncertainty expressions
        uncertainty_count = sum(
            1 for phrase in self.UNCERTAINTY_PHRASES 
            if phrase in output_lower
        )
        
        # Count certainty expressions
        certainty_count = sum(
            1 for phrase in self.CERTAINTY_PHRASES 
            if phrase in output_lower
        )
        
        # Calculate ratio
        total = uncertainty_count + certainty_count
        if total == 0:
            # No strong language either way - neutral
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.PASS,
                score=0.7,
                message="No strong certainty/uncertainty language detected"
            )
        
        uncertainty_ratio = uncertainty_count / total
        
        if uncertainty_ratio < 0.3:
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.WARN,
                score=0.5,
                message="Output may be overconfident - low uncertainty expression",
                details={
                    "uncertainty_count": uncertainty_count,
                    "certainty_count": certainty_count
                }
            )
        
        return ValidationResult(
            validator_name=self.name,
            category=self.category,
            result=EvaluationResult.PASS,
            score=min(1.0, uncertainty_ratio + 0.3),
            message="Appropriate uncertainty expression"
        )


class ToneSafetyValidator(BaseValidator):
    """Validates tone is appropriate and supportive"""
    name = "tone_safety"
    category = EvaluationCategory.TONE
    weight = 1.5
    
    HARSH_PATTERNS = [
        r'\b(terrible|awful|horrible|pathetic|useless)\b',
        r'\b(you failed|you did poorly|you messed up)\b',
        r'\b(nobody would|no one will|never get hired)\b',
        r'\b(waste of time|pointless|hopeless)\b',
    ]
    
    CONDESCENDING_PATTERNS = [
        r'\b(obviously|clearly you|as I said)\b',
        r'\b(you should know|basic mistake|amateur)\b',
        r'\b(even a beginner|any competent)\b',
    ]
    
    def validate(self, output: str, context: Dict[str, Any]) -> ValidationResult:
        issues = []
        
        # Check harsh language
        for pattern in self.HARSH_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"Harsh language: {pattern}")
        
        # Check condescending language  
        for pattern in self.CONDESCENDING_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"Condescending: {pattern}")
        
        if issues:
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.FAIL if len(issues) > 1 else EvaluationResult.WARN,
                score=max(0, 1 - len(issues) * 0.3),
                message=f"Tone issues detected: {len(issues)}",
                details={"issues": issues}
            )
        
        return ValidationResult(
            validator_name=self.name,
            category=self.category,
            result=EvaluationResult.PASS,
            score=1.0,
            message="Tone is appropriate"
        )


class OutputLengthValidator(BaseValidator):
    """Validates output length is reasonable"""
    name = "output_length"
    category = EvaluationCategory.QUALITY
    weight = 0.5
    
    def validate(self, output: str, context: Dict[str, Any]) -> ValidationResult:
        word_count = len(output.split())
        max_length = context.get("max_output_length", 2000)
        min_length = context.get("min_output_length", 20)
        
        if word_count < min_length:
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.WARN,
                score=0.5,
                message=f"Output too short: {word_count} words (min: {min_length})",
                details={"word_count": word_count}
            )
        
        if word_count > max_length:
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.WARN,
                score=0.7,
                message=f"Output too long: {word_count} words (max: {max_length})",
                details={"word_count": word_count}
            )
        
        return ValidationResult(
            validator_name=self.name,
            category=self.category,
            result=EvaluationResult.PASS,
            score=1.0,
            message=f"Output length OK: {word_count} words"
        )


class FactualConsistencyValidator(BaseValidator):
    """Validates output doesn't contradict input facts"""
    name = "factual_consistency"
    category = EvaluationCategory.ACCURACY
    weight = 2.0
    
    def validate(self, output: str, context: Dict[str, Any]) -> ValidationResult:
        original_content = context.get("original_content", "")
        if not original_content:
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.PASS,
                score=0.8,
                message="No original content to compare"
            )
        
        # Extract numbers from original
        original_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', original_content))
        output_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', output))
        
        # Check if output numbers are in original (avoid fabrication)
        new_numbers = output_numbers - original_numbers
        
        # Some new numbers are OK (like counts), but many suggest fabrication
        if len(new_numbers) > 3:
            return ValidationResult(
                validator_name=self.name,
                category=self.category,
                result=EvaluationResult.WARN,
                score=0.6,
                message="Output contains numbers not in original - verify accuracy",
                details={"new_numbers": list(new_numbers)}
            )
        
        return ValidationResult(
            validator_name=self.name,
            category=self.category,
            result=EvaluationResult.PASS,
            score=1.0,
            message="Factual consistency check passed"
        )


# =============================================================================
# EVALUATION ENGINE
# =============================================================================

class EvaluationEngine:
    """
    Comprehensive evaluation engine for AI outputs.
    
    Runs all validators and produces evaluation reports.
    """
    
    def __init__(self):
        self.validators: List[BaseValidator] = [
            ForbiddenPhraseValidator(),
            UncertaintyExpressionValidator(),
            ToneSafetyValidator(),
            OutputLengthValidator(),
            FactualConsistencyValidator(),
        ]
    
    def add_validator(self, validator: BaseValidator) -> None:
        """Add a custom validator"""
        self.validators.append(validator)
    
    def evaluate(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationReport:
        """
        Run full evaluation on an AI output.
        
        Args:
            output: The AI-generated output to evaluate
            context: Additional context (original input, constraints, etc.)
            
        Returns:
            Complete evaluation report
        """
        import time
        start_time = time.time()
        
        context = context or {}
        results = []
        
        # Run all validators
        for validator in self.validators:
            result = validator.validate(output, context)
            results.append(result)
        
        # Calculate scores by category
        category_scores = self._calculate_category_scores(results)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(results)
        
        # Determine overall result
        overall_result = self._determine_overall_result(results)
        
        evaluation_time = (time.time() - start_time) * 1000
        
        return EvaluationReport(
            output_hash=hashlib.sha256(output.encode()).hexdigest()[:16],
            timestamp=datetime.utcnow(),
            validations=results,
            overall_result=overall_result,
            overall_score=overall_score,
            safety_score=category_scores.get(EvaluationCategory.SAFETY, 1.0),
            quality_score=category_scores.get(EvaluationCategory.QUALITY, 1.0),
            consistency_score=category_scores.get(EvaluationCategory.CONSISTENCY, 1.0),
            evaluation_time_ms=evaluation_time
        )
    
    def _calculate_category_scores(
        self,
        results: List[ValidationResult]
    ) -> Dict[EvaluationCategory, float]:
        """Calculate average scores by category"""
        category_scores: Dict[EvaluationCategory, List[float]] = {}
        
        for result in results:
            if result.category not in category_scores:
                category_scores[result.category] = []
            category_scores[result.category].append(result.score)
        
        return {
            cat: sum(scores) / len(scores)
            for cat, scores in category_scores.items()
        }
    
    def _calculate_overall_score(self, results: List[ValidationResult]) -> float:
        """Calculate weighted overall score"""
        total_weight = 0
        weighted_sum = 0
        
        for i, result in enumerate(results):
            validator = self.validators[i] if i < len(self.validators) else None
            weight = validator.weight if validator else 1.0
            
            total_weight += weight
            weighted_sum += result.score * weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def _determine_overall_result(self, results: List[ValidationResult]) -> EvaluationResult:
        """Determine overall pass/warn/fail"""
        # Any safety failure = overall fail
        safety_results = [r for r in results if r.category == EvaluationCategory.SAFETY]
        if any(r.result == EvaluationResult.FAIL for r in safety_results):
            return EvaluationResult.FAIL
        
        # Multiple failures = overall fail
        fail_count = sum(1 for r in results if r.result == EvaluationResult.FAIL)
        if fail_count >= 2:
            return EvaluationResult.FAIL
        
        # Any failure or multiple warnings = warn
        warn_count = sum(1 for r in results if r.result == EvaluationResult.WARN)
        if fail_count >= 1 or warn_count >= 2:
            return EvaluationResult.WARN
        
        return EvaluationResult.PASS
    
    def quick_check(self, output: str) -> bool:
        """
        Quick pass/fail check for real-time validation.
        
        Returns True if output passes basic safety checks.
        """
        # Only run safety validators
        for validator in self.validators:
            if validator.category == EvaluationCategory.SAFETY:
                result = validator.validate(output, {})
                if result.result == EvaluationResult.FAIL:
                    return False
        
        return True


# Global evaluation engine
_evaluation_engine: Optional[EvaluationEngine] = None


def get_evaluation_engine() -> EvaluationEngine:
    """Get the global evaluation engine"""
    global _evaluation_engine
    if _evaluation_engine is None:
        _evaluation_engine = EvaluationEngine()
    return _evaluation_engine
