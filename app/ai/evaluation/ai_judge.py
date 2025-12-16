"""
AI-as-Judge Evaluation

Uses a separate AI model to evaluate AI outputs.
This provides nuanced quality assessment beyond rule-based checks.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class JudgeEvaluation:
    """Result from AI judge evaluation"""
    # Scores (0-10)
    helpfulness_score: float
    accuracy_score: float
    clarity_score: float
    actionability_score: float
    tone_score: float
    
    # Overall
    overall_score: float
    
    # Feedback
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    
    # Metadata
    judge_model: str
    evaluation_time_ms: float
    reasoning: str
    
    def passes_threshold(self, min_score: float = 7.0) -> bool:
        return self.overall_score >= min_score


# Judge prompt for evaluating AI outputs
JUDGE_SYSTEM_PROMPT = """You are an expert AI evaluator assessing the quality of resume feedback.

Your task is to evaluate the AI-generated feedback based on these criteria:

1. HELPFULNESS (0-10): Does the feedback help the user improve their resume?
2. ACCURACY (0-10): Is the feedback factually correct and grounded in the resume content?
3. CLARITY (0-10): Is the feedback easy to understand and follow?
4. ACTIONABILITY (0-10): Can the user take specific actions based on this feedback?
5. TONE (0-10): Is the tone supportive, professional, and encouraging?

RED FLAGS (automatic score reduction):
- Guarantees or promises about hiring outcomes
- Fabricated information not in the original resume
- Harsh, condescending, or discouraging language
- Overly generic advice that doesn't address specific content
- Contradictions within the feedback

You MUST respond in this exact JSON format:
{
    "helpfulness_score": <0-10>,
    "accuracy_score": <0-10>,
    "clarity_score": <0-10>,
    "actionability_score": <0-10>,
    "tone_score": <0-10>,
    "overall_score": <0-10>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "reasoning": "Brief explanation of scores"
}"""


JUDGE_USER_TEMPLATE = """Evaluate this AI-generated resume feedback:

=== ORIGINAL RESUME ===
{resume_content}

=== AI-GENERATED FEEDBACK ===
{ai_feedback}

=== CONTEXT ===
Target Role: {target_role}
User Request: {user_request}

Provide your evaluation in JSON format:"""


class AIJudge:
    """
    AI-as-judge evaluator for quality assessment.
    
    Uses a separate AI model to evaluate AI outputs for quality,
    providing nuanced feedback beyond rule-based checks.
    """
    
    def __init__(self, ai_orchestrator=None, judge_model: str = "gpt-4o"):
        """
        Args:
            ai_orchestrator: AI orchestrator for making judge calls
            judge_model: Model to use for judging (should be capable model)
        """
        self.ai_orchestrator = ai_orchestrator
        self.judge_model = judge_model
    
    async def evaluate(
        self,
        ai_output: str,
        original_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> JudgeEvaluation:
        """
        Evaluate an AI output using AI-as-judge.
        
        Args:
            ai_output: The AI-generated feedback to evaluate
            original_input: The original resume/content
            context: Additional context (target role, user request)
            
        Returns:
            JudgeEvaluation with scores and feedback
        """
        import time
        start_time = time.time()
        
        context = context or {}
        
        # Build judge prompt
        user_prompt = JUDGE_USER_TEMPLATE.format(
            resume_content=original_input[:3000],  # Truncate if needed
            ai_feedback=ai_output,
            target_role=context.get("target_role", "Not specified"),
            user_request=context.get("user_request", "General feedback")
        )
        
        # Call judge model
        if self.ai_orchestrator:
            response = await self._call_judge(user_prompt)
        else:
            # Fallback to rule-based scoring
            response = self._fallback_evaluation(ai_output)
        
        evaluation_time = (time.time() - start_time) * 1000
        
        # Parse response
        try:
            scores = json.loads(response)
        except json.JSONDecodeError:
            scores = self._extract_scores_from_text(response)
        
        return JudgeEvaluation(
            helpfulness_score=scores.get("helpfulness_score", 5),
            accuracy_score=scores.get("accuracy_score", 5),
            clarity_score=scores.get("clarity_score", 5),
            actionability_score=scores.get("actionability_score", 5),
            tone_score=scores.get("tone_score", 5),
            overall_score=scores.get("overall_score", 5),
            strengths=scores.get("strengths", []),
            weaknesses=scores.get("weaknesses", []),
            suggestions=scores.get("suggestions", []),
            judge_model=self.judge_model,
            evaluation_time_ms=evaluation_time,
            reasoning=scores.get("reasoning", "")
        )
    
    async def _call_judge(self, user_prompt: str) -> str:
        """Call the judge model"""
        # This would use the AI orchestrator
        # Placeholder implementation
        return self._fallback_evaluation_json("")
    
    def _fallback_evaluation(self, ai_output: str) -> str:
        """Rule-based fallback when AI judge unavailable"""
        return self._fallback_evaluation_json(ai_output)
    
    def _fallback_evaluation_json(self, ai_output: str) -> str:
        """Generate fallback evaluation JSON"""
        # Simple heuristics
        word_count = len(ai_output.split())
        has_bullets = "•" in ai_output or "-" in ai_output
        has_specifics = any(char.isdigit() for char in ai_output)
        
        base_score = 6
        if word_count > 50:
            base_score += 0.5
        if has_bullets:
            base_score += 0.5
        if has_specifics:
            base_score += 0.5
        
        return json.dumps({
            "helpfulness_score": base_score,
            "accuracy_score": base_score,
            "clarity_score": base_score + 0.5 if has_bullets else base_score,
            "actionability_score": base_score,
            "tone_score": 7,  # Assume OK if passed other validators
            "overall_score": base_score,
            "strengths": ["Provides structured feedback"],
            "weaknesses": ["AI judge unavailable - scores are estimates"],
            "suggestions": [],
            "reasoning": "Fallback evaluation using rule-based heuristics"
        })
    
    def _extract_scores_from_text(self, response: str) -> Dict[str, Any]:
        """Extract scores from non-JSON response"""
        import re
        
        scores = {
            "helpfulness_score": 5,
            "accuracy_score": 5,
            "clarity_score": 5,
            "actionability_score": 5,
            "tone_score": 5,
            "overall_score": 5,
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "reasoning": response[:500]
        }
        
        # Try to extract numbers
        for key in ["helpfulness", "accuracy", "clarity", "actionability", "tone", "overall"]:
            pattern = rf'{key}[:\s]+(\d+(?:\.\d+)?)'
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                scores[f"{key}_score"] = float(match.group(1))
        
        return scores


class ComparativeJudge:
    """
    Compares two AI outputs to determine which is better.
    
    Used for A/B testing and improvement pipeline.
    """
    
    def __init__(self, ai_orchestrator=None, judge_model: str = "gpt-4o"):
        self.ai_orchestrator = ai_orchestrator
        self.judge_model = judge_model
    
    async def compare(
        self,
        output_a: str,
        output_b: str,
        original_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare two AI outputs and determine winner.
        
        Args:
            output_a: First AI output
            output_b: Second AI output
            original_input: Original input they were responding to
            context: Additional context
            
        Returns:
            Comparison result with winner and reasoning
        """
        # Evaluate both
        judge = AIJudge(self.ai_orchestrator, self.judge_model)
        
        eval_a = await judge.evaluate(output_a, original_input, context)
        eval_b = await judge.evaluate(output_b, original_input, context)
        
        # Determine winner
        score_a = eval_a.overall_score
        score_b = eval_b.overall_score
        
        if abs(score_a - score_b) < 0.5:
            winner = "tie"
            margin = 0
        elif score_a > score_b:
            winner = "A"
            margin = score_a - score_b
        else:
            winner = "B"
            margin = score_b - score_a
        
        return {
            "winner": winner,
            "margin": margin,
            "score_a": score_a,
            "score_b": score_b,
            "eval_a": {
                "helpfulness": eval_a.helpfulness_score,
                "accuracy": eval_a.accuracy_score,
                "clarity": eval_a.clarity_score,
                "strengths": eval_a.strengths,
                "weaknesses": eval_a.weaknesses
            },
            "eval_b": {
                "helpfulness": eval_b.helpfulness_score,
                "accuracy": eval_b.accuracy_score,
                "clarity": eval_b.clarity_score,
                "strengths": eval_b.strengths,
                "weaknesses": eval_b.weaknesses
            },
            "recommendation": self._generate_recommendation(winner, eval_a, eval_b)
        }
    
    def _generate_recommendation(
        self,
        winner: str,
        eval_a: JudgeEvaluation,
        eval_b: JudgeEvaluation
    ) -> str:
        """Generate recommendation based on comparison"""
        if winner == "tie":
            return "Both outputs are similar in quality. Consider other factors."
        elif winner == "A":
            return f"Output A is stronger. Key advantages: {', '.join(eval_a.strengths[:2])}"
        else:
            return f"Output B is stronger. Key advantages: {', '.join(eval_b.strengths[:2])}"
