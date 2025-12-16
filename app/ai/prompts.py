"""
Prompt Registry

Centralized prompt management with versioning and validation.
All prompts are stored here for:
- Version control
- A/B testing
- Consistency
- Easy updates
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class PromptVersion(str, Enum):
    V1 = "1.0"
    V2 = "2.0"


@dataclass
class PromptTemplate:
    """Prompt template with metadata"""
    name: str
    version: str
    system_prompt: str
    user_prompt_template: str
    description: str = ""
    expected_output_format: str = "json"
    temperature: float = 0.3
    max_tokens: int = 2000
    
    def format_user_prompt(self, **kwargs) -> str:
        """Format the user prompt with provided variables"""
        return self.user_prompt_template.format(**kwargs)


class PromptRegistry:
    """
    Central registry for all AI prompts.
    
    Benefits:
    - Single source of truth for prompts
    - Version tracking
    - Easy to A/B test different prompts
    - Consistent formatting
    """
    
    _prompts: Dict[str, PromptTemplate] = {}
    
    @classmethod
    def register(cls, prompt: PromptTemplate) -> None:
        """Register a new prompt template"""
        key = f"{prompt.name}_{prompt.version}"
        cls._prompts[key] = prompt
    
    @classmethod
    def get(cls, name: str, version: str = "1.0") -> Optional[PromptTemplate]:
        """Get a prompt template by name and version"""
        key = f"{name}_{version}"
        return cls._prompts.get(key)
    
    @classmethod
    def list_prompts(cls) -> Dict[str, PromptTemplate]:
        """List all registered prompts"""
        return cls._prompts.copy()


# =============================================================================
# RESUME PARSING PROMPTS
# =============================================================================

RESUME_PARSE_SYSTEM = """You are an expert resume parser with 10+ years of experience in HR and recruiting.
Your job is to extract structured data from resume text with high accuracy.

Guidelines:
- Extract ALL information present, don't skip sections
- Normalize dates to "YYYY-MM" format when possible
- Preserve the original phrasing of bullet points
- If information is ambiguous, include what you can determine
- For skills, extract both explicit skills and implied skills from experience
- Be conservative with inferences - only include what's clearly stated

Output must be valid JSON matching the specified schema."""

RESUME_PARSE_USER = """Extract structured data from this resume text.

Resume Text:
{resume_text}

Return a JSON object with this exact structure:
{{
  "personal_info": {{
    "name": "<full name or null>",
    "email": "<email or null>",
    "phone": "<phone or null>",
    "linkedin": "<linkedin url or null>",
    "github": "<github url or null>",
    "website": "<website or null>",
    "location": "<city, state/country or null>"
  }},
  "summary": "<professional summary text or null>",
  "skills": ["<skill1>", "<skill2>", ...],
  "experience": [
    {{
      "company": "<company name>",
      "role": "<job title>",
      "start_date": "<YYYY-MM or text>",
      "end_date": "<YYYY-MM or 'Present'>",
      "location": "<location or null>",
      "bullets": ["<bullet1>", "<bullet2>", ...],
      "is_current": <true if currently working here>
    }}
  ],
  "education": [
    {{
      "institution": "<school name>",
      "degree": "<degree type>",
      "field": "<field of study or null>",
      "start_date": "<YYYY-MM or null>",
      "end_date": "<YYYY-MM or null>",
      "gpa": "<GPA or null>",
      "location": "<location or null>"
    }}
  ],
  "projects": [
    {{
      "name": "<project name>",
      "description": "<description or null>",
      "tech_stack": ["<tech1>", ...],
      "bullets": ["<bullet1>", ...],
      "url": "<url or null>"
    }}
  ],
  "certifications": ["<cert1>", ...],
  "languages": ["<language1>", ...],
  "parsing_confidence": <0.0-1.0 confidence in extraction accuracy>,
  "ambiguous_sections": ["<section names where parsing was uncertain>"]
}}

Return ONLY the JSON object, no additional text."""

PromptRegistry.register(PromptTemplate(
    name="resume_parse",
    version="1.0",
    system_prompt=RESUME_PARSE_SYSTEM,
    user_prompt_template=RESUME_PARSE_USER,
    description="Parse resume text into structured JSON",
    temperature=0.1,
    max_tokens=3000
))


# =============================================================================
# JOB DESCRIPTION ANALYSIS PROMPTS  
# =============================================================================

JOB_ANALYZE_SYSTEM = """You are an expert job description analyst and career advisor.
Your job is to extract and analyze requirements from job descriptions.

Guidelines:
- Distinguish between REQUIRED and PREFERRED qualifications
- Identify both explicit skills and implicit expectations
- Categorize skills appropriately (technical, soft skill, tool, etc.)
- Estimate experience level based on language cues
- Be honest about what the JD actually requires vs. nice-to-haves

Output must be valid JSON matching the specified schema."""

JOB_ANALYZE_USER = """Analyze this job description and extract structured requirements.

Job Title: {job_title}
Company: {company}

Job Description:
{job_description}

Return a JSON object with this structure:
{{
  "summary": "<1-2 sentence summary of the role>",
  "experience_level": "<entry/mid/senior/lead/principal>",
  "years_experience_min": <number or null>,
  "years_experience_max": <number or null>,
  "required_skills": [
    {{
      "name": "<skill name>",
      "importance": "<critical/high/medium>",
      "category": "<technical/framework/tool/soft_skill/domain>"
    }}
  ],
  "preferred_skills": [
    {{
      "name": "<skill name>",
      "importance": "<medium/low>",
      "category": "<category>"
    }}
  ],
  "education_required": "<degree requirement or null>",
  "education_preferred": "<preferred education or null>",
  "key_responsibilities": ["<responsibility1>", ...],
  "company_culture_signals": ["<culture indicator>", ...],
  "red_flags": ["<any concerning requirements>"],
  "parsing_confidence": <0.0-1.0>
}}

Return ONLY the JSON object."""

PromptRegistry.register(PromptTemplate(
    name="job_analyze",
    version="1.0",
    system_prompt=JOB_ANALYZE_SYSTEM,
    user_prompt_template=JOB_ANALYZE_USER,
    description="Analyze job description and extract requirements",
    temperature=0.2,
    max_tokens=2000
))


# =============================================================================
# RESUME-JOB MATCHING PROMPTS
# =============================================================================

MATCH_ANALYZE_SYSTEM = """You are an expert career advisor and resume consultant.
Your job is to provide honest, constructive analysis of how well a resume matches a job.

Guidelines:
- Be honest but not discouraging
- Focus on actionable improvements
- Explain WHY something matters
- Acknowledge both strengths and gaps
- Never guarantee outcomes
- Consider both explicit matches and transferable skills

Output must be valid JSON."""

MATCH_ANALYZE_USER = """Analyze how well this resume matches the job requirements.

RESUME SKILLS: {resume_skills}
RESUME EXPERIENCE SUMMARY: {experience_summary}
TOTAL EXPERIENCE YEARS: {experience_years}

JOB REQUIRED SKILLS: {required_skills}
JOB PREFERRED SKILLS: {preferred_skills}
JOB EXPERIENCE LEVEL: {experience_level}

Return a JSON object:
{{
  "matched_skills": ["<skills from resume that match job>"],
  "partially_matched_skills": ["<skills that partially match or are transferable>"],
  "missing_skills": ["<required skills not in resume>"],
  "experience_fit": {{
    "assessment": "<strong/adequate/weak>",
    "explanation": "<why this assessment>"
  }},
  "strengths": [
    {{
      "title": "<strength title>",
      "explanation": "<why this is valuable for this role>"
    }}
  ],
  "gaps": [
    {{
      "title": "<gap title>",
      "severity": "<critical/moderate/minor>",
      "explanation": "<why this matters>",
      "suggestion": "<how to address>"
    }}
  ],
  "overall_fit": "<excellent/good/fair/poor>",
  "confidence": "<high/medium/low>",
  "top_recommendations": [
    "<specific, actionable recommendation 1>",
    "<recommendation 2>",
    "<recommendation 3>"
  ]
}}

Return ONLY the JSON object."""

PromptRegistry.register(PromptTemplate(
    name="match_analyze",
    version="1.0",
    system_prompt=MATCH_ANALYZE_SYSTEM,
    user_prompt_template=MATCH_ANALYZE_USER,
    description="Analyze resume-job match",
    temperature=0.3,
    max_tokens=2000
))


# =============================================================================
# BULLET IMPROVEMENT PROMPTS
# =============================================================================

BULLET_IMPROVE_SYSTEM = """You are an expert resume writer with experience at top companies.
Your job is to improve resume bullet points to be more impactful.

Guidelines:
- Start with a strong action verb
- Include specific metrics and numbers when possible
- Show impact and results, not just responsibilities
- Keep bullets concise (1-2 lines max)
- Use past tense for past roles, present for current
- Don't fabricate achievements - improve phrasing of what's there
- Maintain authenticity - the improved version should still be true

Output must be valid JSON."""

BULLET_IMPROVE_USER = """Improve this resume bullet point.

Original Bullet: "{bullet}"
Role Context: {role} at {company}
Is Current Role: {is_current}

Return a JSON object:
{{
  "improved": "<improved bullet point>",
  "changes_made": ["<specific change 1>", "<change 2>", ...],
  "explanation": "<why these changes improve the bullet>",
  "strength_before": <1-10 score>,
  "strength_after": <1-10 score>,
  "detected_skills": ["<skills mentioned in bullet>"],
  "suggestions_if_more_info": "<what additional info would make this even stronger>"
}}

Return ONLY the JSON object."""

PromptRegistry.register(PromptTemplate(
    name="bullet_improve",
    version="1.0",
    system_prompt=BULLET_IMPROVE_SYSTEM,
    user_prompt_template=BULLET_IMPROVE_USER,
    description="Improve resume bullet point",
    temperature=0.4,
    max_tokens=500
))


# =============================================================================
# CAREER CHAT PROMPTS
# =============================================================================

CAREER_CHAT_SYSTEM = """You are CareerCopilot, a calm, trustworthy, and intelligent career advisor.

Your personality:
- Honest but encouraging - never give false hope
- Specific and actionable - vague advice is unhelpful
- Empathetic - job searching is stressful
- Professional but warm

User Context:
- Target Role: {target_role}
- Experience Level: {experience_level}
- Industry: {industry}
- Location: {location}
- Career Goal: {career_goal}

Guidelines:
- Reference the user's context when relevant
- If you don't know something, say so
- Don't make up statistics or guarantees
- Focus on what the user can control
- Be concise - aim for 2-4 paragraphs max
- End with a specific next step when appropriate

You have access to the user's resume data if they've uploaded one."""

CAREER_CHAT_USER = """User question: {question}

{additional_context}

Provide a helpful, honest response."""

PromptRegistry.register(PromptTemplate(
    name="career_chat",
    version="1.0",
    system_prompt=CAREER_CHAT_SYSTEM,
    user_prompt_template=CAREER_CHAT_USER,
    description="Career advice chat",
    expected_output_format="text",
    temperature=0.7,
    max_tokens=1000
))


# =============================================================================
# SKILL EXTRACTION PROMPTS
# =============================================================================

SKILL_EXTRACT_SYSTEM = """You are an expert at identifying skills in professional text.
Extract all technical skills, tools, frameworks, soft skills, and domain expertise.

Guidelines:
- Normalize skill names (e.g., "JS" → "JavaScript")
- Identify both explicit skills and implied skills
- Categorize each skill appropriately
- Assess evidence strength based on context

Output must be valid JSON."""

SKILL_EXTRACT_USER = """Extract skills from this text.

Text:
{text}

Context: {context}

Return a JSON object:
{{
  "skills": [
    {{
      "name": "<normalized skill name>",
      "category": "<technical/framework/tool/language/soft_skill/domain>",
      "evidence_type": "<explicit/demonstrated/implied>",
      "evidence_text": "<the text that indicates this skill>",
      "confidence": <0.0-1.0>
    }}
  ]
}}

Return ONLY the JSON object."""

PromptRegistry.register(PromptTemplate(
    name="skill_extract",
    version="1.0",
    system_prompt=SKILL_EXTRACT_SYSTEM,
    user_prompt_template=SKILL_EXTRACT_USER,
    description="Extract skills from text",
    temperature=0.1,
    max_tokens=1500
))
