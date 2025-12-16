"""
Bullet Quality Analyzer Skill

Analyzes resume bullet points for:
- Impact/achievement clarity
- Metric inclusion
- Action verb strength
- Length appropriateness
- Specificity vs vagueness
"""
from typing import Dict, Any, List
from dataclasses import dataclass
import time
import re

from . import AISkill, SkillInput, SkillOutput, SkillCategory, ToneConstraint


@dataclass
class BulletAnalysis:
    """Analysis result for a single bullet"""
    text: str
    score: float  # 0-100
    
    # Component scores
    action_verb_score: float
    metric_score: float
    impact_score: float
    specificity_score: float
    length_score: float
    
    # Issues found
    issues: List[str]
    strengths: List[str]
    
    # Suggestion (if improvements needed)
    suggestion: str


# Strong action verbs by category
ACTION_VERBS = {
    "leadership": ["Led", "Directed", "Managed", "Supervised", "Coordinated", "Orchestrated"],
    "achievement": ["Achieved", "Accomplished", "Exceeded", "Delivered", "Attained", "Surpassed"],
    "creation": ["Created", "Developed", "Designed", "Built", "Established", "Launched"],
    "improvement": ["Improved", "Enhanced", "Optimized", "Streamlined", "Transformed", "Revamped"],
    "analysis": ["Analyzed", "Evaluated", "Assessed", "Researched", "Investigated", "Examined"],
    "communication": ["Presented", "Communicated", "Negotiated", "Collaborated", "Facilitated", "Influenced"]
}

# Weak/vague verbs to avoid
WEAK_VERBS = [
    "Helped", "Assisted", "Worked on", "Was responsible for",
    "Participated in", "Handled", "Dealt with", "Involved in"
]

# Metric patterns
METRIC_PATTERNS = [
    r'\d+%',           # Percentages
    r'\$[\d,]+',       # Dollar amounts
    r'\d+x',           # Multipliers
    r'\d+\+',          # Numbers with plus
    r'\d+\s*(?:million|billion|thousand|k|M|B)',  # Large numbers
    r'(?:increased|decreased|reduced|grew|improved)\s+(?:by\s+)?\d+',  # Change metrics
]


class BulletQualityAnalyzer(AISkill):
    """
    Analyzes resume bullet points for quality and impact.
    
    Single responsibility: Score and analyze individual bullet points.
    """
    
    name = "bullet_quality_analyzer"
    version = "1.0.0"
    category = SkillCategory.ANALYSIS
    requires_ai = False  # Can work without AI
    
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start_time = time.time()
        
        # Validate
        errors = self.validate_input(input_data)
        if errors:
            return SkillOutput(
                result={"error": errors},
                confidence=0,
                reasoning_trace="Input validation failed",
                skill_name=self.name,
                skill_version=self.version,
                execution_time_ms=0,
                warnings=errors
            )
        
        # Parse bullets from content
        bullets = self._extract_bullets(input_data.primary_content)
        
        # Analyze each bullet
        analyses = []
        for bullet in bullets:
            analysis = self._analyze_bullet(bullet, input_data.context)
            analyses.append(analysis)
        
        # Calculate overall score
        if analyses:
            overall_score = sum(a.score for a in analyses) / len(analyses)
        else:
            overall_score = 0
        
        # Determine confidence based on analysis quality
        confidence = self._calculate_confidence(analyses)
        
        # Build reasoning trace
        reasoning = self._build_reasoning(analyses)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SkillOutput(
            result={
                "overall_score": overall_score,
                "bullet_count": len(analyses),
                "bullets": [self._analysis_to_dict(a) for a in analyses],
                "summary": self._generate_summary(analyses, input_data.tone)
            },
            confidence=confidence,
            reasoning_trace=reasoning,
            skill_name=self.name,
            skill_version=self.version,
            execution_time_ms=execution_time,
            input_hash=self._hash_input(input_data)
        )
    
    def _extract_bullets(self, content: str) -> List[str]:
        """Extract bullet points from content"""
        lines = content.split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            # Match bullet patterns
            if line.startswith(('•', '-', '*', '·')) or re.match(r'^\d+\.', line):
                # Remove bullet marker
                bullet = re.sub(r'^[•\-*·]\s*|\d+\.\s*', '', line).strip()
                if bullet and len(bullet) > 10:  # Meaningful content
                    bullets.append(bullet)
            elif len(line) > 20 and not line.endswith(':'):
                # May be a bullet without marker
                bullets.append(line)
        
        return bullets
    
    def _analyze_bullet(self, bullet: str, context: Dict[str, Any]) -> BulletAnalysis:
        """Analyze a single bullet point"""
        issues = []
        strengths = []
        
        # 1. Action verb analysis
        action_score = self._score_action_verb(bullet)
        if action_score >= 80:
            strengths.append("Strong action verb")
        elif action_score < 50:
            issues.append("Consider starting with a stronger action verb")
        
        # 2. Metric analysis
        metric_score = self._score_metrics(bullet)
        if metric_score >= 80:
            strengths.append("Good use of quantifiable metrics")
        elif metric_score < 30:
            issues.append("Add quantifiable results (numbers, percentages, dollar amounts)")
        
        # 3. Impact analysis
        impact_score = self._score_impact(bullet)
        if impact_score >= 70:
            strengths.append("Clear impact/outcome")
        elif impact_score < 40:
            issues.append("Clarify the impact or outcome of this achievement")
        
        # 4. Specificity analysis
        specificity_score = self._score_specificity(bullet)
        if specificity_score >= 70:
            strengths.append("Specific and concrete")
        elif specificity_score < 40:
            issues.append("Be more specific about what you did")
        
        # 5. Length analysis
        length_score = self._score_length(bullet)
        if length_score >= 70:
            strengths.append("Appropriate length")
        elif length_score < 50:
            if len(bullet) < 50:
                issues.append("Bullet is too short - add more detail")
            else:
                issues.append("Bullet is too long - consider splitting or condensing")
        
        # Calculate overall score (weighted)
        overall_score = (
            action_score * 0.25 +
            metric_score * 0.25 +
            impact_score * 0.2 +
            specificity_score * 0.15 +
            length_score * 0.15
        )
        
        # Generate suggestion if needed
        suggestion = ""
        if overall_score < 70:
            suggestion = self._generate_suggestion(bullet, issues)
        
        return BulletAnalysis(
            text=bullet,
            score=overall_score,
            action_verb_score=action_score,
            metric_score=metric_score,
            impact_score=impact_score,
            specificity_score=specificity_score,
            length_score=length_score,
            issues=issues,
            strengths=strengths,
            suggestion=suggestion
        )
    
    def _score_action_verb(self, bullet: str) -> float:
        """Score the action verb usage"""
        first_word = bullet.split()[0] if bullet.split() else ""
        
        # Check strong verbs
        for category, verbs in ACTION_VERBS.items():
            if first_word in verbs:
                return 100
        
        # Check weak verbs
        for weak in WEAK_VERBS:
            if bullet.lower().startswith(weak.lower()):
                return 30
        
        # Check if starts with verb-like word
        if first_word and first_word[0].isupper() and first_word.endswith(('ed', 'ing')):
            return 60
        
        return 50  # Neutral
    
    def _score_metrics(self, bullet: str) -> float:
        """Score the presence of metrics"""
        metrics_found = 0
        
        for pattern in METRIC_PATTERNS:
            if re.search(pattern, bullet, re.IGNORECASE):
                metrics_found += 1
        
        if metrics_found >= 2:
            return 100
        elif metrics_found == 1:
            return 70
        else:
            # Check for any numbers
            if re.search(r'\d', bullet):
                return 40
            return 20
    
    def _score_impact(self, bullet: str) -> float:
        """Score impact clarity"""
        impact_words = [
            "resulted in", "leading to", "which", "enabling",
            "increased", "decreased", "improved", "reduced",
            "saved", "generated", "achieved", "delivered"
        ]
        
        bullet_lower = bullet.lower()
        impact_count = sum(1 for word in impact_words if word in bullet_lower)
        
        if impact_count >= 2:
            return 90
        elif impact_count == 1:
            return 65
        else:
            # Check for result structure (action -> result)
            if " by " in bullet_lower or " to " in bullet_lower:
                return 50
            return 30
    
    def _score_specificity(self, bullet: str) -> float:
        """Score how specific vs vague the bullet is"""
        vague_words = [
            "various", "multiple", "several", "many", "some",
            "things", "stuff", "etc", "tasks", "duties"
        ]
        
        specific_indicators = [
            "specifically", "including", "such as",
            "using", "with", "through", "via"
        ]
        
        bullet_lower = bullet.lower()
        
        vague_count = sum(1 for word in vague_words if word in bullet_lower)
        specific_count = sum(1 for word in specific_indicators if word in bullet_lower)
        
        # Named technologies/tools add specificity
        if re.search(r'[A-Z][a-z]+(?:[A-Z][a-z]+)+', bullet):  # CamelCase
            specific_count += 1
        
        score = 60  # Base
        score += specific_count * 15
        score -= vague_count * 20
        
        return max(0, min(100, score))
    
    def _score_length(self, bullet: str) -> float:
        """Score bullet length"""
        char_count = len(bullet)
        word_count = len(bullet.split())
        
        # Ideal: 75-150 characters, 15-25 words
        if 75 <= char_count <= 150 and 15 <= word_count <= 25:
            return 100
        elif 50 <= char_count <= 200 and 10 <= word_count <= 35:
            return 70
        elif char_count < 40:
            return 30  # Too short
        elif char_count > 250:
            return 40  # Too long
        else:
            return 55
    
    def _generate_suggestion(self, bullet: str, issues: List[str]) -> str:
        """Generate improvement suggestion"""
        suggestions = []
        
        if "stronger action verb" in str(issues):
            suggestions.append("Start with a verb like 'Led', 'Developed', or 'Achieved'")
        
        if "quantifiable" in str(issues):
            suggestions.append("Include numbers (e.g., '20%', '$50K', '100+ users')")
        
        if "impact" in str(issues):
            suggestions.append("Add the outcome (e.g., 'resulting in X')")
        
        if "specific" in str(issues):
            suggestions.append("Name specific tools, technologies, or methods used")
        
        return " | ".join(suggestions) if suggestions else ""
    
    def _calculate_confidence(self, analyses: List[BulletAnalysis]) -> float:
        """Calculate confidence in the analysis"""
        if not analyses:
            return 0.5
        
        # Higher confidence with more bullets and consistent scoring
        bullet_count_factor = min(1.0, len(analyses) / 5)
        
        # Score variance factor
        scores = [a.score for a in analyses]
        if len(scores) > 1:
            variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            variance_factor = max(0.5, 1 - variance/1000)
        else:
            variance_factor = 0.7
        
        return 0.6 + (bullet_count_factor * 0.2) + (variance_factor * 0.2)
    
    def _build_reasoning(self, analyses: List[BulletAnalysis]) -> str:
        """Build reasoning trace"""
        if not analyses:
            return "No bullets found to analyze"
        
        parts = [
            f"Analyzed {len(analyses)} bullet points.",
            f"Average score: {sum(a.score for a in analyses)/len(analyses):.1f}/100.",
        ]
        
        # Component summaries
        avg_action = sum(a.action_verb_score for a in analyses) / len(analyses)
        avg_metric = sum(a.metric_score for a in analyses) / len(analyses)
        
        parts.append(f"Action verb avg: {avg_action:.1f}, Metric avg: {avg_metric:.1f}")
        
        return " ".join(parts)
    
    def _generate_summary(self, analyses: List[BulletAnalysis], tone: ToneConstraint) -> str:
        """Generate human-readable summary"""
        if not analyses:
            return "No bullet points found to analyze."
        
        avg_score = sum(a.score for a in analyses) / len(analyses)
        high_scoring = sum(1 for a in analyses if a.score >= 70)
        needs_work = sum(1 for a in analyses if a.score < 50)
        
        if tone == ToneConstraint.SUPPORTIVE:
            if avg_score >= 70:
                return f"Great work! {high_scoring} of {len(analyses)} bullets are strong. " \
                       f"Your bullets effectively communicate your achievements."
            else:
                return f"{high_scoring} bullets are strong, and {needs_work} could use improvement. " \
                       f"Consider adding metrics and stronger action verbs to boost impact."
        else:  # DIRECT
            return f"Score: {avg_score:.0f}/100. Strong: {high_scoring}. Needs work: {needs_work}."
    
    def _analysis_to_dict(self, analysis: BulletAnalysis) -> Dict[str, Any]:
        return {
            "text": analysis.text[:100] + "..." if len(analysis.text) > 100 else analysis.text,
            "score": round(analysis.score, 1),
            "components": {
                "action_verb": round(analysis.action_verb_score, 1),
                "metrics": round(analysis.metric_score, 1),
                "impact": round(analysis.impact_score, 1),
                "specificity": round(analysis.specificity_score, 1),
                "length": round(analysis.length_score, 1)
            },
            "issues": analysis.issues,
            "strengths": analysis.strengths,
            "suggestion": analysis.suggestion
        }
