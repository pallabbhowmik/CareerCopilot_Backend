"""
ATS Risk Explainer Skill

Explains ATS (Applicant Tracking System) compatibility issues in plain language.
Helps users understand WHY something might cause problems.
"""
from typing import Dict, Any, List
from dataclasses import dataclass
import time
import re

from . import AISkill, SkillInput, SkillOutput, SkillCategory, ToneConstraint


@dataclass
class ATSRisk:
    """An identified ATS risk"""
    category: str
    severity: str  # high, medium, low
    issue: str
    explanation: str
    fix: str
    affected_content: str


# ATS compatibility rules
ATS_RULES = {
    "file_format": {
        "description": "File format compatibility",
        "check": "format",
        "risks": [
            ("pdf_with_images", "high", "PDF contains complex images or graphics"),
            ("docx_with_text_boxes", "high", "Document uses text boxes"),
            ("non_standard_format", "high", "Non-standard file format"),
        ]
    },
    "section_headers": {
        "description": "Section header recognition",
        "standard_headers": ["Experience", "Work Experience", "Education", "Skills", "Summary"],
        "risks": [
            ("creative_headers", "medium", "Non-standard section headers"),
            ("missing_headers", "high", "Missing standard sections"),
        ]
    },
    "formatting": {
        "description": "Text formatting issues",
        "risks": [
            ("tables", "high", "Content in tables may not parse correctly"),
            ("columns", "medium", "Multi-column layouts can confuse parsing"),
            ("headers_footers", "medium", "Content in headers/footers may be missed"),
            ("special_characters", "low", "Special characters or symbols"),
        ]
    },
    "contact_info": {
        "description": "Contact information detection",
        "risks": [
            ("missing_email", "high", "No email address detected"),
            ("missing_phone", "medium", "No phone number detected"),
            ("formatted_phone", "low", "Unusual phone number format"),
        ]
    },
    "keywords": {
        "description": "Keyword matching",
        "risks": [
            ("skill_abbreviations", "medium", "Skills using abbreviations only"),
            ("missing_job_keywords", "high", "Missing key job requirement terms"),
        ]
    }
}


class ATSRiskExplainer(AISkill):
    """
    Explains ATS compatibility risks in plain language.
    
    Single responsibility: Identify and explain ATS parsing risks.
    """
    
    name = "ats_risk_explainer"
    version = "1.0.0"
    category = SkillCategory.ANALYSIS
    requires_ai = False
    
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
        
        # Analyze for ATS risks
        risks = self._identify_risks(input_data.primary_content, input_data.context)
        
        # Calculate overall ATS score
        ats_score = self._calculate_ats_score(risks)
        
        # Generate explanations
        explanations = self._generate_explanations(risks, input_data.tone)
        
        # Build reasoning
        reasoning = self._build_reasoning(risks)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SkillOutput(
            result={
                "ats_score": ats_score,
                "risk_count": len(risks),
                "risks_by_severity": {
                    "high": len([r for r in risks if r.severity == "high"]),
                    "medium": len([r for r in risks if r.severity == "medium"]),
                    "low": len([r for r in risks if r.severity == "low"])
                },
                "risks": [self._risk_to_dict(r) for r in risks],
                "explanations": explanations,
                "summary": self._generate_summary(risks, ats_score, input_data.tone)
            },
            confidence=0.85,  # Rule-based analysis has high confidence
            reasoning_trace=reasoning,
            skill_name=self.name,
            skill_version=self.version,
            execution_time_ms=execution_time,
            input_hash=self._hash_input(input_data)
        )
    
    def _identify_risks(self, content: str, context: Dict[str, Any]) -> List[ATSRisk]:
        """Identify ATS risks in content"""
        risks = []
        
        # Check formatting risks
        risks.extend(self._check_formatting_risks(content))
        
        # Check section headers
        risks.extend(self._check_section_risks(content))
        
        # Check contact info
        risks.extend(self._check_contact_risks(content))
        
        # Check keywords if job description provided
        if job_desc := context.get("job_description"):
            risks.extend(self._check_keyword_risks(content, job_desc))
        
        return risks
    
    def _check_formatting_risks(self, content: str) -> List[ATSRisk]:
        """Check for formatting-related risks"""
        risks = []
        
        # Check for table indicators
        if re.search(r'\|.*\|.*\|', content) or '\t\t\t' in content:
            risks.append(ATSRisk(
                category="formatting",
                severity="high",
                issue="Possible table structure detected",
                explanation="Tables in resumes often don't parse correctly in ATS systems. "
                           "The content inside tables may be scrambled, misread, or completely ignored.",
                fix="Convert table content to a simple bulleted list format",
                affected_content=content[:100] if len(content) > 100 else content
            ))
        
        # Check for column indicators (multiple spaces suggesting columns)
        lines = content.split('\n')
        column_lines = [l for l in lines if re.search(r'\S\s{4,}\S', l)]
        if len(column_lines) > 3:
            risks.append(ATSRisk(
                category="formatting",
                severity="medium",
                issue="Multi-column layout suspected",
                explanation="Multi-column layouts can confuse ATS parsers. Content might be read "
                           "across columns instead of down, scrambling your information.",
                fix="Use a single-column layout for maximum compatibility",
                affected_content="Multiple lines with column spacing detected"
            ))
        
        # Check for special characters
        special_chars = re.findall(r'[★☆●○◆◇→←↑↓✓✗]', content)
        if special_chars:
            risks.append(ATSRisk(
                category="formatting",
                severity="low",
                issue="Special characters detected",
                explanation="Some special characters or symbols may not render correctly in all systems, "
                           "potentially appearing as garbled text.",
                fix="Replace special symbols with standard characters (*, -, +)",
                affected_content=f"Characters found: {', '.join(set(special_chars))}"
            ))
        
        return risks
    
    def _check_section_risks(self, content: str) -> List[ATSRisk]:
        """Check section header risks"""
        risks = []
        content_lower = content.lower()
        
        standard_headers = [
            ("experience", ["experience", "work experience", "professional experience", "employment"]),
            ("education", ["education", "academic", "qualifications", "degrees"]),
            ("skills", ["skills", "technical skills", "core competencies", "expertise"]),
        ]
        
        missing_sections = []
        for section_name, variations in standard_headers:
            found = any(var in content_lower for var in variations)
            if not found:
                missing_sections.append(section_name)
        
        if missing_sections:
            risks.append(ATSRisk(
                category="section_headers",
                severity="high" if "experience" in missing_sections else "medium",
                issue=f"Standard section(s) may be missing: {', '.join(missing_sections)}",
                explanation="ATS systems look for standard section headers to categorize your information. "
                           "Without them, your content may be misclassified or ignored entirely.",
                fix=f"Add clear section headers: {', '.join(s.title() for s in missing_sections)}",
                affected_content="Section headers"
            ))
        
        return risks
    
    def _check_contact_risks(self, content: str) -> List[ATSRisk]:
        """Check contact information risks"""
        risks = []
        
        # Email check
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        if not re.search(email_pattern, content):
            risks.append(ATSRisk(
                category="contact_info",
                severity="high",
                issue="No email address detected",
                explanation="Without a valid email address, recruiters cannot contact you. "
                           "This is critical information that must be easily identifiable.",
                fix="Add your email address near the top of your resume",
                affected_content="Contact section"
            ))
        
        # Phone check
        phone_pattern = r'[\d\s\-\(\)\.]{10,}'
        if not re.search(phone_pattern, content):
            risks.append(ATSRisk(
                category="contact_info",
                severity="medium",
                issue="No phone number detected",
                explanation="A phone number is expected in the contact section. "
                           "Some recruiters prefer phone over email for initial contact.",
                fix="Add your phone number in a standard format (e.g., 555-123-4567)",
                affected_content="Contact section"
            ))
        
        return risks
    
    def _check_keyword_risks(self, content: str, job_desc: str) -> List[ATSRisk]:
        """Check keyword matching with job description"""
        risks = []
        content_lower = content.lower()
        job_lower = job_desc.lower()
        
        # Extract potential keywords from job description
        # Look for skills, technologies, requirements
        skill_patterns = [
            r'\b(?:proficient|experience|knowledge|familiar)\s+(?:in|with)\s+(\w+(?:\s+\w+)?)',
            r'(\d+\+?\s*years?\s+(?:of\s+)?(?:\w+\s+){1,3}experience)',
        ]
        
        job_keywords = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, job_lower)
            job_keywords.update(matches)
        
        # Common technical skills to check
        tech_skills = [
            "python", "javascript", "java", "sql", "aws", "azure", "react",
            "node", "docker", "kubernetes", "machine learning", "ai"
        ]
        
        for skill in tech_skills:
            if skill in job_lower and skill not in content_lower:
                job_keywords.add(skill)
        
        missing_keywords = [k for k in job_keywords if k not in content_lower]
        
        if missing_keywords:
            risks.append(ATSRisk(
                category="keywords",
                severity="high",
                issue=f"Missing key terms from job description",
                explanation="ATS systems often rank candidates by keyword matching. "
                           "Missing relevant keywords can lower your ranking significantly.",
                fix=f"Consider adding relevant experience with: {', '.join(missing_keywords[:5])}",
                affected_content=f"Keywords: {', '.join(missing_keywords[:5])}"
            ))
        
        return risks
    
    def _calculate_ats_score(self, risks: List[ATSRisk]) -> float:
        """Calculate overall ATS compatibility score"""
        base_score = 100
        
        for risk in risks:
            if risk.severity == "high":
                base_score -= 15
            elif risk.severity == "medium":
                base_score -= 8
            else:
                base_score -= 3
        
        return max(0, base_score)
    
    def _generate_explanations(self, risks: List[ATSRisk], tone: ToneConstraint) -> List[str]:
        """Generate plain-language explanations"""
        explanations = []
        
        if tone == ToneConstraint.SUPPORTIVE:
            prefix = "Here's something to consider: "
        else:
            prefix = ""
        
        for risk in risks:
            if risk.severity == "high":
                explanations.append(f"{prefix}{risk.explanation}")
        
        return explanations[:3]  # Top 3 explanations
    
    def _generate_summary(self, risks: List[ATSRisk], score: float, tone: ToneConstraint) -> str:
        """Generate summary"""
        high_count = len([r for r in risks if r.severity == "high"])
        
        if tone == ToneConstraint.SUPPORTIVE:
            if score >= 80:
                return f"Good news! Your resume appears to be ATS-friendly with a score of {score:.0f}/100. " \
                       f"A few minor tweaks could make it even stronger."
            elif score >= 60:
                return f"Your ATS compatibility score is {score:.0f}/100. " \
                       f"Addressing {high_count} key issue(s) could significantly improve your chances."
            else:
                return f"Your ATS score of {score:.0f}/100 suggests some formatting changes would help. " \
                       f"Let's focus on the {high_count} high-priority items first."
        else:
            return f"ATS Score: {score:.0f}/100. High priority issues: {high_count}."
    
    def _build_reasoning(self, risks: List[ATSRisk]) -> str:
        """Build reasoning trace"""
        categories = set(r.category for r in risks)
        severities = {"high": 0, "medium": 0, "low": 0}
        for r in risks:
            severities[r.severity] += 1
        
        return (
            f"Analyzed {len(categories)} risk categories. "
            f"Found {severities['high']} high, {severities['medium']} medium, {severities['low']} low severity issues. "
            f"Categories checked: {', '.join(categories)}."
        )
    
    def _risk_to_dict(self, risk: ATSRisk) -> Dict[str, Any]:
        return {
            "category": risk.category,
            "severity": risk.severity,
            "issue": risk.issue,
            "explanation": risk.explanation,
            "fix": risk.fix
        }
