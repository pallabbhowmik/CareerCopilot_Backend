"""
Resume Section Rewriter Skill

AI-powered skill for rewriting and improving resume sections.
Uses constrained AI generation with strict guardrails.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time
import re

from . import AISkill, SkillInput, SkillOutput, SkillCategory, ToneConstraint


@dataclass
class RewriteResult:
    """Result of a section rewrite"""
    original: str
    rewritten: str
    changes_made: List[str]
    improvement_score: float
    reasoning: str


# Rewrite rules and patterns
SECTION_REWRITE_RULES = {
    "summary": {
        "max_sentences": 4,
        "should_include": ["years of experience", "key skills", "value proposition"],
        "should_avoid": ["I am", "seeking", "looking for", "objective"],
        "tone": "confident but not arrogant"
    },
    "experience": {
        "bullet_format": "action_verb + task + result",
        "should_include": ["metrics", "impact", "scope"],
        "should_avoid": ["responsibilities included", "duties", "helped with"],
        "max_bullets_per_role": 6
    },
    "skills": {
        "format": "grouped by category",
        "should_avoid": ["proficient in", "familiar with", "soft skills list"],
        "prioritize": "job-relevant skills first"
    }
}


class ResumeSectionRewriter(AISkill):
    """
    Rewrites resume sections with AI assistance.
    
    Single responsibility: Improve section content while preserving facts.
    
    CRITICAL CONSTRAINTS:
    - NEVER fabricate information
    - NEVER add skills/experiences not mentioned
    - MUST preserve factual accuracy
    - SHOULD improve clarity and impact
    """
    
    name = "resume_section_rewriter"
    version = "1.0.0"
    category = SkillCategory.GENERATION
    requires_ai = True  # Best with AI, falls back to rules
    
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start_time = time.time()
        
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
        
        # Determine section type
        section_type = input_data.context.get("section_type", "experience")
        
        # Get rewrite constraints
        constraints = SECTION_REWRITE_RULES.get(section_type, {})
        
        # Perform rewrite
        if self.ai_orchestrator:
            result = await self._ai_rewrite(
                input_data.primary_content,
                section_type,
                constraints,
                input_data.context,
                input_data.tone
            )
        else:
            result = self._rule_based_rewrite(
                input_data.primary_content,
                section_type,
                constraints,
                input_data.tone
            )
        
        # Validate output
        validation_issues = self._validate_rewrite(
            input_data.primary_content,
            result.rewritten
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        return SkillOutput(
            result={
                "original": result.original,
                "rewritten": result.rewritten,
                "changes_made": result.changes_made,
                "improvement_score": result.improvement_score,
                "section_type": section_type,
                "warnings": validation_issues
            },
            confidence=result.improvement_score / 100 * 0.7 + 0.3 if not validation_issues else 0.5,
            reasoning_trace=result.reasoning,
            skill_name=self.name,
            skill_version=self.version,
            execution_time_ms=execution_time,
            input_hash=self._hash_input(input_data),
            warnings=validation_issues
        )
    
    async def _ai_rewrite(
        self,
        content: str,
        section_type: str,
        constraints: Dict,
        context: Dict[str, Any],
        tone: ToneConstraint
    ) -> RewriteResult:
        """AI-powered rewrite with strict constraints"""
        # Build prompt with guardrails
        system_prompt = self._build_rewrite_prompt(section_type, constraints)
        
        # Call AI (placeholder - would use ai_orchestrator)
        # For now, fall back to rule-based
        return self._rule_based_rewrite(content, section_type, constraints, tone)
    
    def _rule_based_rewrite(
        self,
        content: str,
        section_type: str,
        constraints: Dict,
        tone: ToneConstraint
    ) -> RewriteResult:
        """Rule-based rewrite for when AI is unavailable"""
        original = content
        rewritten = content
        changes_made = []
        
        if section_type == "experience":
            rewritten, changes = self._rewrite_experience_bullets(content)
            changes_made.extend(changes)
        elif section_type == "summary":
            rewritten, changes = self._rewrite_summary(content)
            changes_made.extend(changes)
        elif section_type == "skills":
            rewritten, changes = self._rewrite_skills(content)
            changes_made.extend(changes)
        
        # Calculate improvement score
        improvement_score = self._calculate_improvement(original, rewritten, changes_made)
        
        return RewriteResult(
            original=original,
            rewritten=rewritten,
            changes_made=changes_made,
            improvement_score=improvement_score,
            reasoning=f"Applied {len(changes_made)} rule-based improvements to {section_type} section"
        )
    
    def _rewrite_experience_bullets(self, content: str) -> tuple[str, List[str]]:
        """Rewrite experience bullets"""
        lines = content.split('\n')
        rewritten_lines = []
        changes = []
        
        for line in lines:
            original_line = line
            
            # Remove weak starters
            weak_patterns = [
                (r'^Responsible for\s+', ''),
                (r'^Duties included\s+', ''),
                (r'^Helped (?:with\s+)?', ''),
                (r'^Assisted (?:with\s+)?', ''),
                (r'^Was involved in\s+', ''),
            ]
            
            for pattern, replacement in weak_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
                    # Capitalize first letter
                    if line:
                        line = line[0].upper() + line[1:]
                    changes.append(f"Removed weak starter from: {original_line[:50]}...")
            
            # Convert passive to active (simple cases)
            passive_patterns = [
                (r'was\s+(\w+ed)\s+by', r'\1'),
                (r'were\s+(\w+ed)\s+by', r'\1'),
            ]
            
            for pattern, replacement in passive_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
                    changes.append(f"Converted passive voice in: {original_line[:50]}...")
            
            rewritten_lines.append(line)
        
        return '\n'.join(rewritten_lines), changes
    
    def _rewrite_summary(self, content: str) -> tuple[str, List[str]]:
        """Rewrite summary section"""
        changes = []
        rewritten = content
        
        # Remove first-person "I am" constructions
        if re.search(r'\bI am\b', content, re.IGNORECASE):
            # Convert "I am a software engineer" to "Software engineer"
            rewritten = re.sub(
                r'\bI am (?:a |an )?', '', rewritten, flags=re.IGNORECASE
            )
            changes.append("Removed first-person 'I am' construction")
        
        # Remove "seeking" language
        if re.search(r'\bseeking\b|\blooking for\b', content, re.IGNORECASE):
            rewritten = re.sub(
                r'(?:,?\s*)?(?:seeking|looking for)[^.]*\.?', 
                '.', rewritten, flags=re.IGNORECASE
            )
            changes.append("Removed 'seeking/looking for' language")
        
        return rewritten.strip(), changes
    
    def _rewrite_skills(self, content: str) -> tuple[str, List[str]]:
        """Rewrite skills section"""
        changes = []
        rewritten = content
        
        # Remove fluffy qualifiers
        fluffy = [
            r'\bproficient in\b',
            r'\bfamiliar with\b', 
            r'\bknowledge of\b',
            r'\bexperience with\b',
            r'\bworking knowledge of\b'
        ]
        
        for pattern in fluffy:
            if re.search(pattern, content, re.IGNORECASE):
                rewritten = re.sub(pattern + r'\s*', '', rewritten, flags=re.IGNORECASE)
                changes.append(f"Removed qualifier: {pattern}")
        
        return rewritten.strip(), changes
    
    def _validate_rewrite(self, original: str, rewritten: str) -> List[str]:
        """Validate that rewrite didn't introduce issues"""
        issues = []
        
        # Check that we didn't add significant content
        original_words = set(original.lower().split())
        rewritten_words = set(rewritten.lower().split())
        
        new_words = rewritten_words - original_words
        # Allow some new words (articles, connectors)
        allowed_new = {'the', 'a', 'an', 'and', 'or', 'with', 'for', 'to', 'of', 'in'}
        truly_new = new_words - allowed_new
        
        if len(truly_new) > len(original_words) * 0.3:  # More than 30% new content
            issues.append("Warning: Rewrite may have added content not in original")
        
        # Check we didn't remove too much
        if len(rewritten) < len(original) * 0.5:
            issues.append("Warning: Rewrite significantly shortened content")
        
        return issues
    
    def _calculate_improvement(
        self,
        original: str,
        rewritten: str,
        changes: List[str]
    ) -> float:
        """Calculate improvement score"""
        if original == rewritten:
            return 0  # No change
        
        score = 50  # Base score for any change
        
        # Points for each improvement type
        score += len(changes) * 10
        
        # Cap at 100
        return min(100, score)
    
    def _build_rewrite_prompt(self, section_type: str, constraints: Dict) -> str:
        """Build prompt for AI rewriting"""
        return f"""You are a resume improvement expert. Rewrite the following {section_type} section.

CRITICAL RULES - NEVER VIOLATE:
1. NEVER fabricate or add information not present in the original
2. NEVER add skills, experiences, or achievements that weren't mentioned
3. NEVER change dates, company names, job titles, or factual details
4. PRESERVE all numbers, metrics, and quantifiable data exactly

IMPROVEMENTS TO MAKE:
- Strengthen action verbs (Led, Developed, Achieved instead of Helped, Assisted)
- Add clearer structure to bullets (Action + Context + Result)
- Remove weak language and filler words
- Improve professional tone
- Optimize for ATS keyword scanning

CONSTRAINTS FOR {section_type.upper()}:
{constraints}

Return ONLY the rewritten section, no explanations."""
