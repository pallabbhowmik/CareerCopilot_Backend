"""
ATS Simulation Engine

Deterministic, explainable ATS readiness evaluation.

Key principles:
- NO single score
- Every signal is explained
- Confidence bands for each check
- Recruiter-friendly recommendations
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re

from app.domain.entities.resume import ResumeEntity, ResumeBullet, BulletStrength
from app.domain.entities.analysis import (
    ATSEvaluation, CheckResult, Explanation,
    SignalStrength, ConfidenceLevel, ActionPriority, ExplanationType
)


class CheckStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


# =============================================================================
# ATS CHECK CONSTANTS
# =============================================================================

# Minimum requirements for ATS parsing
MIN_SKILLS_COUNT = 5
MIN_EXPERIENCE_BULLETS = 3
MAX_BULLET_LENGTH = 200  # Characters

# Section importance weights (for internal scoring only)
SECTION_WEIGHTS = {
    "personal_info": 0.20,
    "experience": 0.35,
    "education": 0.15,
    "skills": 0.20,
    "summary": 0.10
}

# Strong action verbs for bullets
ACTION_VERBS = [
    "achieved", "administered", "analyzed", "built", "collaborated",
    "conducted", "coordinated", "created", "decreased", "delivered",
    "designed", "developed", "directed", "established", "executed",
    "expanded", "generated", "implemented", "improved", "increased",
    "initiated", "launched", "led", "managed", "mentored",
    "optimized", "orchestrated", "organized", "pioneered", "planned",
    "produced", "reduced", "resolved", "scaled", "spearheaded",
    "streamlined", "supervised", "transformed", "upgraded"
]

# Formatting red flags
FORMATTING_RED_FLAGS = [
    "tables",
    "images",
    "graphics",
    "columns",
    "text boxes",
    "headers/footers with key info"
]


class ATSSimulationEngine:
    """
    Deterministic ATS readiness evaluation engine.
    
    Simulates how ATS systems parse and evaluate resumes.
    All outputs include explanations - never just a score.
    """
    
    def evaluate(
        self,
        resume: ResumeEntity,
        job_skills: Optional[List[str]] = None
    ) -> ATSEvaluation:
        """
        Run full ATS evaluation on a resume.
        
        Args:
            resume: Parsed resume entity
            job_skills: Optional list of skills from target job
            
        Returns:
            ATSEvaluation with detailed checks and explanations
        """
        evaluation = ATSEvaluation()
        
        # Run all checks
        evaluation.parsing_check = self._check_parsing(resume)
        evaluation.formatting_check = self._check_formatting(resume)
        evaluation.keyword_check = self._check_keywords(resume, job_skills)
        evaluation.section_check = self._check_sections(resume)
        evaluation.readability_check = self._check_readability(resume)
        
        # Determine overall readiness level
        evaluation.readiness_level = self._determine_readiness_level(evaluation)
        
        # Collect primary issues
        evaluation.primary_issues = self._collect_primary_issues(evaluation)
        
        # Generate summary explanation
        evaluation.summary_explanation = self._generate_summary(evaluation)
        
        # Generate detailed explanations
        evaluation.detailed_explanations = self._generate_detailed_explanations(evaluation)
        
        # Internal score (not shown to users)
        evaluation._internal_score = self._calculate_internal_score(evaluation)
        
        return evaluation
    
    # =========================================================================
    # INDIVIDUAL CHECKS
    # =========================================================================
    
    def _check_parsing(self, resume: ResumeEntity) -> CheckResult:
        """Check if ATS can successfully parse the resume"""
        result = CheckResult(
            check_name="Parsing Success",
            category="parsing"
        )
        
        detected_sections = []
        issues = []
        
        # Check each critical section
        if resume.personal_info.name:
            detected_sections.append("Contact Information")
        else:
            issues.append("Name not detected")
        
        if resume.personal_info.email:
            detected_sections.append("Email")
        else:
            issues.append("Email not detected")
        
        if resume.experience:
            detected_sections.append("Experience")
        else:
            issues.append("Experience section not found")
        
        if resume.skills:
            detected_sections.append("Skills")
        else:
            issues.append("Skills section not found")
        
        if resume.education:
            detected_sections.append("Education")
        
        if resume.summary:
            detected_sections.append("Summary")
        
        # Determine status
        critical_missing = [i for i in issues if "Email" in i or "Experience" in i]
        
        if not critical_missing and len(detected_sections) >= 4:
            result.status = "pass"
            result.passed = True
        elif critical_missing:
            result.status = "fail"
            result.passed = False
        else:
            result.status = "warning"
            result.passed = True
        
        result.evidence_items = detected_sections
        
        # Create explanation
        result.explanation = Explanation(
            explanation_type=ExplanationType.WHAT_WE_FOUND,
            title="Section Detection",
            summary=f"ATS detected {len(detected_sections)} out of 6 standard sections.",
            detail=f"Detected: {', '.join(detected_sections)}" if detected_sections else "No sections clearly detected.",
            signal_name="section_detection",
            signal_value=len(detected_sections),
            signal_strength=SignalStrength.STRONG if len(detected_sections) >= 4 else SignalStrength.MODERATE,
            confidence=ConfidenceLevel.HIGH,
            is_actionable=bool(issues),
            action_text=f"Add or clarify: {', '.join(issues)}" if issues else None,
            action_priority=ActionPriority.HIGH if critical_missing else ActionPriority.MEDIUM
        )
        
        return result
    
    def _check_formatting(self, resume: ResumeEntity) -> CheckResult:
        """Check for ATS-safe formatting"""
        result = CheckResult(
            check_name="Formatting Safety",
            category="formatting"
        )
        
        issues = []
        warnings = []
        
        # Check contact info completeness
        if not resume.personal_info.email:
            issues.append("Email address is required")
        
        if not resume.personal_info.phone:
            warnings.append("Consider adding a phone number")
        
        # Check for special characters in text that might indicate formatting issues
        raw_text = resume.raw_text or ""
        
        # Check for potential table markers
        if "│" in raw_text or "┌" in raw_text or "─" in raw_text:
            warnings.append("Possible table formatting detected - some ATS may not parse correctly")
        
        # Check for unusual characters
        unusual_chars = re.findall(r'[^\x00-\x7F]+', raw_text)
        if len(unusual_chars) > 50:
            warnings.append("Many special characters detected - ensure compatibility")
        
        # Determine status
        if issues:
            result.status = "fail"
            result.passed = False
        elif warnings:
            result.status = "warning"
            result.passed = True
        else:
            result.status = "pass"
            result.passed = True
        
        result.evidence_items = issues + warnings
        
        # Create explanation
        status_text = {
            "pass": "Your resume uses ATS-friendly formatting.",
            "warning": "Minor formatting improvements recommended.",
            "fail": "Formatting issues may prevent ATS parsing."
        }
        
        result.explanation = Explanation(
            explanation_type=ExplanationType.WHAT_WE_FOUND,
            title="Format Compatibility",
            summary=status_text[result.status],
            detail="ATS systems work best with clean, single-column layouts without tables, images, or complex formatting.",
            signal_name="formatting_safety",
            signal_strength=SignalStrength.STRONG if result.status == "pass" else SignalStrength.WEAK,
            confidence=ConfidenceLevel.MEDIUM,  # Can't fully verify without original file
            confidence_reason="Analysis based on parsed text; original file formatting may differ.",
            is_actionable=bool(issues or warnings),
            action_text=issues[0] if issues else (warnings[0] if warnings else None),
            action_priority=ActionPriority.HIGH if issues else ActionPriority.LOW
        )
        
        return result
    
    def _check_keywords(
        self, 
        resume: ResumeEntity,
        job_skills: Optional[List[str]] = None
    ) -> CheckResult:
        """Check keyword usage and action verb strength"""
        result = CheckResult(
            check_name="Keyword & Action Verb Analysis",
            category="keywords"
        )
        
        # Analyze bullet points
        total_bullets = 0
        bullets_with_verbs = 0
        bullets_with_metrics = 0
        
        for exp in resume.experience:
            for bullet in exp.bullets:
                total_bullets += 1
                text_lower = bullet.text.lower()
                
                # Check for action verbs
                if any(verb in text_lower for verb in ACTION_VERBS):
                    bullets_with_verbs += 1
                
                # Check for metrics (numbers)
                if re.search(r'\d+', bullet.text):
                    bullets_with_metrics += 1
        
        verb_percentage = (bullets_with_verbs / total_bullets * 100) if total_bullets > 0 else 0
        metric_percentage = (bullets_with_metrics / total_bullets * 100) if total_bullets > 0 else 0
        
        # Skill coverage if job skills provided
        skill_coverage = None
        if job_skills:
            user_skills_lower = {s.lower() for s in resume.skills}
            matched_skills = [s for s in job_skills if s.lower() in user_skills_lower]
            skill_coverage = (len(matched_skills) / len(job_skills) * 100) if job_skills else 0
        
        # Determine status
        if verb_percentage >= 70 and metric_percentage >= 40:
            result.status = "pass"
            result.passed = True
        elif verb_percentage >= 50 or metric_percentage >= 25:
            result.status = "warning"
            result.passed = True
        else:
            result.status = "fail"
            result.passed = False
        
        result.score = int((verb_percentage + metric_percentage) / 2)
        
        evidence = [
            f"{int(verb_percentage)}% of bullets use strong action verbs",
            f"{int(metric_percentage)}% of bullets include metrics"
        ]
        if skill_coverage is not None:
            evidence.append(f"{int(skill_coverage)}% skill match with job")
        
        result.evidence_items = evidence
        
        # Create explanation
        result.explanation = Explanation(
            explanation_type=ExplanationType.WHAT_WE_FOUND,
            title="Impact Language",
            summary=f"Your resume uses action verbs in {int(verb_percentage)}% of bullets and includes metrics in {int(metric_percentage)}%.",
            detail="Strong resumes start bullets with action verbs (Led, Developed, Achieved) and include specific numbers to quantify impact. This helps both ATS keyword matching and recruiter engagement.",
            signal_name="keyword_strength",
            signal_value={"verb_pct": verb_percentage, "metric_pct": metric_percentage},
            signal_strength=SignalStrength.STRONG if verb_percentage >= 70 else SignalStrength.MODERATE,
            confidence=ConfidenceLevel.HIGH,
            is_actionable=verb_percentage < 70 or metric_percentage < 40,
            action_text="Strengthen bullets by starting with action verbs and adding specific metrics" if verb_percentage < 70 else None,
            action_priority=ActionPriority.MEDIUM
        )
        
        return result
    
    def _check_sections(self, resume: ResumeEntity) -> CheckResult:
        """Check section completeness and quality"""
        result = CheckResult(
            check_name="Section Completeness",
            category="sections"
        )
        
        required_sections = {
            "personal_info": bool(resume.personal_info.name and resume.personal_info.email),
            "experience": len(resume.experience) > 0,
            "skills": len(resume.skills) >= MIN_SKILLS_COUNT,
            "education": len(resume.education) > 0
        }
        
        recommended_sections = {
            "summary": bool(resume.summary),
            "projects": len(resume.projects) > 0
        }
        
        required_present = sum(required_sections.values())
        required_total = len(required_sections)
        
        completeness_score = int((required_present / required_total) * 100)
        
        # Determine status
        if required_present == required_total:
            result.status = "pass"
            result.passed = True
        elif required_present >= 3:
            result.status = "warning"
            result.passed = True
        else:
            result.status = "fail"
            result.passed = False
        
        result.score = completeness_score
        
        missing_required = [k for k, v in required_sections.items() if not v]
        missing_recommended = [k for k, v in recommended_sections.items() if not v]
        
        evidence = [f"{required_present}/{required_total} required sections complete"]
        if missing_required:
            evidence.append(f"Missing: {', '.join(missing_required)}")
        
        result.evidence_items = evidence
        
        # Create explanation
        result.explanation = Explanation(
            explanation_type=ExplanationType.WHAT_WE_FOUND,
            title="Section Coverage",
            summary=f"Your resume has {required_present} of {required_total} essential sections.",
            detail="ATS systems expect standard sections: Contact Info, Experience, Education, and Skills. Missing sections may cause parsing issues or reduce match scores.",
            signal_name="section_completeness",
            signal_value=completeness_score,
            signal_strength=SignalStrength.STRONG if completeness_score == 100 else SignalStrength.MODERATE,
            confidence=ConfidenceLevel.HIGH,
            is_actionable=bool(missing_required),
            action_text=f"Add: {', '.join(missing_required)}" if missing_required else None,
            action_priority=ActionPriority.HIGH if missing_required else ActionPriority.LOW
        )
        
        return result
    
    def _check_readability(self, resume: ResumeEntity) -> CheckResult:
        """Check recruiter readability"""
        result = CheckResult(
            check_name="Recruiter Readability",
            category="readability"
        )
        
        issues = []
        total_bullets = 0
        long_bullets = 0
        
        # Check bullet length
        for exp in resume.experience:
            for bullet in exp.bullets:
                total_bullets += 1
                if len(bullet.text) > MAX_BULLET_LENGTH:
                    long_bullets += 1
        
        if total_bullets > 0:
            long_bullet_pct = (long_bullets / total_bullets) * 100
            if long_bullet_pct > 30:
                issues.append(f"{int(long_bullet_pct)}% of bullets may be too long for quick scanning")
        
        # Check experience count
        if len(resume.experience) > 10:
            issues.append("Consider condensing older roles - 10+ positions may overwhelm recruiters")
        
        # Check bullet count per job
        for exp in resume.experience:
            if len(exp.bullets) > 8:
                issues.append(f"Position at {exp.company} has {len(exp.bullets)} bullets - consider reducing to 5-6")
                break  # Only flag once
        
        # Determine status
        if not issues:
            result.status = "pass"
            result.passed = True
        else:
            result.status = "warning"
            result.passed = True
        
        readability_score = max(0, 100 - (len(issues) * 15))
        result.score = readability_score
        result.evidence_items = issues if issues else ["Resume is well-structured for quick scanning"]
        
        # Create explanation
        result.explanation = Explanation(
            explanation_type=ExplanationType.WHY_IT_MATTERS,
            title="Scan-ability",
            summary="Recruiters spend 6-7 seconds on initial resume scan." if not issues else f"Found {len(issues)} readability concerns.",
            detail="Concise bullets (1-2 lines), clear section headers, and prioritized content help recruiters quickly identify your value.",
            signal_name="readability",
            signal_value=readability_score,
            signal_strength=SignalStrength.STRONG if not issues else SignalStrength.MODERATE,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason="Based on content length analysis; visual layout may differ.",
            is_actionable=bool(issues),
            action_text=issues[0] if issues else None,
            action_priority=ActionPriority.LOW
        )
        
        return result
    
    # =========================================================================
    # AGGREGATION & SUMMARY
    # =========================================================================
    
    def _determine_readiness_level(self, evaluation: ATSEvaluation) -> str:
        """Determine overall readiness level"""
        checks = evaluation.get_all_checks()
        
        failed_count = sum(1 for c in checks if c.status == "fail")
        warning_count = sum(1 for c in checks if c.status == "warning")
        
        if failed_count > 0:
            return "needs_work"
        elif warning_count >= 3:
            return "good"  # Not excellent due to warnings
        elif warning_count >= 1:
            return "good"
        else:
            return "excellent"
    
    def _collect_primary_issues(self, evaluation: ATSEvaluation) -> List[str]:
        """Collect the most important issues to address"""
        issues = []
        
        for check in evaluation.get_all_checks():
            if check.explanation.is_actionable and check.explanation.action_text:
                if check.explanation.action_priority in [ActionPriority.CRITICAL, ActionPriority.HIGH]:
                    issues.insert(0, check.explanation.action_text)
                else:
                    issues.append(check.explanation.action_text)
        
        return issues[:5]  # Top 5 issues
    
    def _generate_summary(self, evaluation: ATSEvaluation) -> Explanation:
        """Generate overall summary explanation"""
        level_descriptions = {
            "excellent": "Your resume is well-optimized for ATS systems.",
            "good": "Your resume should pass most ATS filters with minor improvements.",
            "needs_work": "Some changes are needed to improve ATS compatibility."
        }
        
        level_details = {
            "excellent": "All critical checks passed. Your resume follows ATS best practices and should parse correctly in most systems.",
            "good": "Most checks passed with some areas for improvement. These optimizations can increase your match scores.",
            "needs_work": "We found issues that may prevent your resume from being properly parsed or ranked by ATS systems."
        }
        
        return Explanation(
            explanation_type=ExplanationType.WHAT_WE_FOUND,
            title="ATS Readiness Summary",
            summary=level_descriptions[evaluation.readiness_level],
            detail=level_details[evaluation.readiness_level],
            signal_name="overall_readiness",
            signal_value=evaluation.readiness_level,
            signal_strength=SignalStrength.STRONG if evaluation.readiness_level == "excellent" else SignalStrength.MODERATE,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason="ATS systems vary - this is a simulation based on common patterns.",
            is_actionable=evaluation.readiness_level != "excellent",
            action_text=evaluation.primary_issues[0] if evaluation.primary_issues else None,
            action_priority=ActionPriority.HIGH if evaluation.readiness_level == "needs_work" else ActionPriority.MEDIUM
        )
    
    def _generate_detailed_explanations(self, evaluation: ATSEvaluation) -> List[Explanation]:
        """Generate list of detailed explanations for each finding"""
        explanations = []
        
        for check in evaluation.get_all_checks():
            explanations.append(check.explanation)
        
        return explanations
    
    def _calculate_internal_score(self, evaluation: ATSEvaluation) -> int:
        """
        Calculate internal score for backend use only.
        
        IMPORTANT: This score should NEVER be shown to users.
        It's only for internal ranking/sorting purposes.
        """
        checks = evaluation.get_all_checks()
        
        total_weight = sum(SECTION_WEIGHTS.values())
        weighted_score = 0
        
        category_weights = {
            "parsing": SECTION_WEIGHTS.get("personal_info", 0.20),
            "formatting": 0.15,
            "keywords": SECTION_WEIGHTS.get("experience", 0.35),
            "sections": 0.15,
            "readability": 0.15
        }
        
        for check in checks:
            weight = category_weights.get(check.category, 0.1)
            
            if check.status == "pass":
                score = check.score if check.score else 100
            elif check.status == "warning":
                score = check.score if check.score else 70
            else:
                score = check.score if check.score else 40
            
            weighted_score += (score * weight)
        
        return int(weighted_score)


# Backward compatibility function
def calculate_ats_readiness(
    resume_json: Dict[str, Any],
    job_desc: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    
    Converts dict to ResumeEntity and runs evaluation.
    """
    from app.domain.entities.resume import ResumeEntity
    
    resume = ResumeEntity.from_dict(resume_json)
    
    job_skills = None
    if job_desc:
        job_skills = job_desc.get("required_skills", [])
    
    engine = ATSSimulationEngine()
    evaluation = engine.evaluate(resume, job_skills)
    
    return evaluation.to_dict()
