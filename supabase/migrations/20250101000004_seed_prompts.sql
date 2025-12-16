-- =====================================================
-- Seed Data: Initial AI Prompts
-- Migration: 20250101000004
-- Description: Production-ready prompts for core skills
-- =====================================================

-- =====================================================
-- SKILL: analyze_resume
-- Purpose: Comprehensive resume analysis
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    version,
    prompt_text,
    model,
    temperature,
    expected_output_schema,
    status,
    deployed_at,
    metadata
) VALUES (
    'analyze_resume',
    1,
    'Analyze the following resume and provide detailed feedback.

Resume:
{resume_text}

Target Job (if provided):
{job_description}

Provide your analysis in JSON format with the following structure:
{{
    "overall_score": <number 0-100>,
    "strengths": [<list of strengths>],
    "weaknesses": [<list of weaknesses>],
    "missing_keywords": [<list of keywords not found>],
    "ats_compatibility": <number 0-100>,
    "recommendations": [
        {{
            "category": "<category>",
            "priority": "<high/medium/low>",
            "suggestion": "<specific suggestion>",
            "rationale": "<why this matters>"
        }}
    ],
    "skill_gaps": [
        {{
            "skill": "<skill name>",
            "importance": "<critical/important/nice-to-have>",
            "suggested_action": "<how to address>"
        }}
    ]
}}',
    'gpt-4',
    0.3,
    '{
        "type": "object",
        "required": ["overall_score", "strengths", "weaknesses", "recommendations"],
        "properties": {
            "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
            "missing_keywords": {"type": "array", "items": {"type": "string"}},
            "ats_compatibility": {"type": "number", "minimum": 0, "maximum": 100},
            "recommendations": {"type": "array"},
            "skill_gaps": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Analyzes resume and provides actionable feedback",
        "max_tokens": 2000,
        "typical_cost": 0.06,
        "typical_latency_ms": 3000
    }'::jsonb
);

-- =====================================================
-- SKILL: generate_bullets
-- Purpose: Generate STAR-format bullet points
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    version,
    prompt_text,
    model,
    temperature,
    expected_output_schema,
    status,
    deployed_at,
    metadata
) VALUES (
    'generate_bullets',
    1,
    'Generate 3-5 compelling resume bullet points for the following work experience.

Job Title: {job_title}
Company: {company}
Description: {experience_description}

Guidelines:
1. Use STAR format (Situation, Task, Action, Result)
2. Start with strong action verbs
3. Include quantifiable results when possible
4. Use power words that pass ATS systems
5. Keep each bullet to 1-2 lines
6. Focus on achievements, not responsibilities

Return JSON format:
{{
    "bullets": [
        {{
            "text": "<bullet point>",
            "action_verb": "<verb used>",
            "has_metric": <true/false>,
            "ats_keywords": [<list of keywords>],
            "star_elements": {{
                "situation": "<brief context>",
                "task": "<what needed to be done>",
                "action": "<what you did>",
                "result": "<impact/outcome>"
            }}
        }}
    ],
    "suggested_skills": [<skills demonstrated in these bullets>]
}}',
    'gpt-4',
    0.7,
    '{
        "type": "object",
        "required": ["bullets"],
        "properties": {
            "bullets": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["text", "action_verb", "has_metric"],
                    "properties": {
                        "text": {"type": "string"},
                        "action_verb": {"type": "string"},
                        "has_metric": {"type": "boolean"},
                        "ats_keywords": {"type": "array"},
                        "star_elements": {"type": "object"}
                    }
                }
            },
            "suggested_skills": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Generates STAR-format resume bullets",
        "max_tokens": 1500,
        "typical_cost": 0.04,
        "typical_latency_ms": 2500
    }'::jsonb
);

-- =====================================================
-- SKILL: extract_skills
-- Purpose: Extract and categorize skills from resume
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    version,
    prompt_text,
    model,
    temperature,
    expected_output_schema,
    status,
    deployed_at,
    metadata
) VALUES (
    'extract_skills',
    1,
    'Extract all skills from the following resume and categorize them.

Resume:
{resume_text}

Categorize skills into:
- technical_skills: Programming languages, frameworks, tools
- soft_skills: Communication, leadership, problem-solving
- domain_skills: Industry-specific knowledge
- certifications: Professional certifications

For each skill, estimate proficiency level based on context:
1 = Beginner/Mentioned
2 = Intermediate/Used
3 = Advanced/Led projects
4 = Expert/Taught others

Return JSON format:
{{
    "technical_skills": [
        {{
            "name": "<skill>",
            "category": "<languages/frameworks/tools/databases>",
            "proficiency_level": <1-4>,
            "evidence": "<where mentioned in resume>",
            "years_experience": <estimated years or null>
        }}
    ],
    "soft_skills": [
        {{
            "name": "<skill>",
            "proficiency_level": <1-4>,
            "evidence": "<context from resume>"
        }}
    ],
    "domain_skills": [
        {{
            "name": "<skill>",
            "industry": "<industry>",
            "proficiency_level": <1-4>
        }}
    ],
    "certifications": [
        {{
            "name": "<certification>",
            "issuer": "<issuing organization>",
            "year": <year or null>
        }}
    ]
}}',
    'gpt-4',
    0.2,
    '{
        "type": "object",
        "required": ["technical_skills", "soft_skills"],
        "properties": {
            "technical_skills": {"type": "array"},
            "soft_skills": {"type": "array"},
            "domain_skills": {"type": "array"},
            "certifications": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Extracts and categorizes skills from resume text",
        "max_tokens": 2000,
        "typical_cost": 0.05,
        "typical_latency_ms": 3500
    }'::jsonb
);

-- =====================================================
-- SKILL: match_job
-- Purpose: Calculate job-resume match score
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    version,
    prompt_text,
    model,
    temperature,
    expected_output_schema,
    status,
    deployed_at,
    metadata
) VALUES (
    'match_job',
    1,
    'Analyze how well this resume matches the job description.

Resume:
{resume_text}

Job Description:
{job_description}

Provide detailed matching analysis in JSON:
{{
    "match_score": <0-100>,
    "matched_requirements": [
        {{
            "requirement": "<from job description>",
            "evidence": "<from resume>",
            "strength": "<strong/moderate/weak>"
        }}
    ],
    "missing_requirements": [
        {{
            "requirement": "<from job description>",
            "criticality": "<must-have/nice-to-have>",
            "gap_size": "<large/medium/small>",
            "suggested_action": "<how to address>"
        }}
    ],
    "matched_keywords": [<list of matching keywords>],
    "missing_keywords": [<list of important missing keywords>],
    "role_fit_assessment": "<detailed paragraph>",
    "interview_talking_points": [
        "<points to emphasize in interview>"
    ],
    "resume_modifications": [
        {{
            "section": "<which section>",
            "modification": "<what to change>",
            "reason": "<why it helps>"
        }}
    ]
}}',
    'gpt-4',
    0.3,
    '{
        "type": "object",
        "required": ["match_score", "matched_requirements", "missing_requirements"],
        "properties": {
            "match_score": {"type": "number", "minimum": 0, "maximum": 100},
            "matched_requirements": {"type": "array"},
            "missing_requirements": {"type": "array"},
            "matched_keywords": {"type": "array"},
            "missing_keywords": {"type": "array"},
            "role_fit_assessment": {"type": "string"},
            "interview_talking_points": {"type": "array"},
            "resume_modifications": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Calculates job-resume match with detailed analysis",
        "max_tokens": 2500,
        "typical_cost": 0.08,
        "typical_latency_ms": 4000
    }'::jsonb
);

-- =====================================================
-- SKILL: optimize_summary
-- Purpose: Generate optimized resume summary
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    version,
    prompt_text,
    model,
    temperature,
    expected_output_schema,
    status,
    deployed_at,
    metadata
) VALUES (
    'optimize_summary',
    1,
    'Generate a compelling resume summary based on the following information.

Resume:
{resume_text}

Target Job (optional):
{job_description}

Guidelines:
1. 3-4 sentences maximum
2. Highlight top 3 value propositions
3. Include years of experience
4. Mention key technical skills
5. Add one quantifiable achievement
6. Use industry-specific keywords
7. Write in third person

Return JSON:
{{
    "summary": "<optimized summary text>",
    "key_value_props": [<3 main value propositions>],
    "keywords_included": [<ATS keywords used>],
    "alternative_versions": [
        {{
            "version": "<slightly different phrasing>",
            "tone": "<professional/enthusiastic/technical>"
        }}
    ]
}}',
    'gpt-4',
    0.6,
    '{
        "type": "object",
        "required": ["summary", "key_value_props"],
        "properties": {
            "summary": {"type": "string", "maxLength": 500},
            "key_value_props": {"type": "array", "minItems": 3, "maxItems": 3},
            "keywords_included": {"type": "array"},
            "alternative_versions": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Generates optimized resume summary",
        "max_tokens": 1000,
        "typical_cost": 0.03,
        "typical_latency_ms": 2000
    }'::jsonb
);

-- =====================================================
-- Create indexes for prompt lookup performance
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_prompts_skill_status 
    ON ai_prompts(skill_name, status) 
    WHERE status = 'production';

CREATE INDEX IF NOT EXISTS idx_prompts_performance 
    ON ai_prompts(skill_name, success_rate DESC, avg_latency_ms ASC) 
    WHERE status = 'production';
