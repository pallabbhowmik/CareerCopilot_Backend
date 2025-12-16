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
    prompt_name,
    prompt_version,
    system_prompt,
    user_prompt_template,
    model_name,
    temperature,
    output_schema,
    status,
    promoted_at
) VALUES (
    'analyze_resume',
    'analyze_resume_v1',
    1,
    'You are an expert resume analyzer. Provide detailed, actionable feedback on resume quality, ATS compatibility, and improvement areas.',
    'Analyze the following resume and provide detailed feedback.

Resume:
{resume_text}

Target Job (if provided):
{job_description}

Provide your analysis in JSON format with the following structure:
{
    "overall_score": <number 0-100>,
    "strengths": [<list of strengths>],
    "weaknesses": [<list of weaknesses>],
    "missing_keywords": [<list of keywords not found>],
    "ats_compatibility": <number 0-100>,
    "recommendations": [
        {
            "category": "<category>",
            "priority": "<high/medium/low>",
            "suggestion": "<specific suggestion>",
            "rationale": "<why this matters>"
        }
    ],
    "skill_gaps": [
        {
            "skill": "<skill name>",
            "importance": "<critical/important/nice-to-have>",
            "found_in_resume": <boolean>
        }
    ]
}',
    'gpt-4',
    0.3,
    '{
        "type": "object",
        "required": ["overall_score", "strengths", "weaknesses", "ats_compatibility"],
        "properties": {
            "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
            "strengths": {"type": "array"},
            "weaknesses": {"type": "array"},
            "missing_keywords": {"type": "array"},
            "ats_compatibility": {"type": "number", "minimum": 0, "maximum": 100},
            "recommendations": {"type": "array"},
            "skill_gaps": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW()
);

-- =====================================================
-- SKILL: generate_bullets
-- Purpose: Generate resume bullet points
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    prompt_name,
    prompt_version,
    system_prompt,
    user_prompt_template,
    model_name,
    temperature,
    output_schema,
    status,
    promoted_at
) VALUES (
    'generate_bullets',
    'generate_bullets_v1',
    1,
    'You are a professional resume writer specializing in achievement-oriented bullet points using the STAR method.',
    'Generate {count} resume bullet points for the following job experience.

Job Title: {job_title}
Company: {company}
Key Responsibilities: {responsibilities}
Achievements: {achievements}

Guidelines:
- Use strong action verbs
- Include quantifiable results when possible
- Follow STAR format (Situation, Task, Action, Result)
- Be specific and achievement-focused
- Keep each bullet to 1-2 lines

Return JSON:
{
    "bullets": [
        {
            "text": "<bullet point text>",
            "action_verb": "<primary action verb used>",
            "has_metric": <boolean>,
            "confidence": <0.0-1.0>
        }
    ]
}',
    'gpt-4',
    0.7,
    '{
        "type": "object",
        "required": ["bullets"],
        "properties": {
            "bullets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["text", "action_verb", "has_metric", "confidence"],
                    "properties": {
                        "text": {"type": "string", "maxLength": 200},
                        "action_verb": {"type": "string"},
                        "has_metric": {"type": "boolean"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                }
            }
        }
    }'::jsonb,
    'production',
    NOW()
);

-- =====================================================
-- SKILL: extract_skills
-- Purpose: Extract skills from resume text
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    prompt_name,
    prompt_version,
    system_prompt,
    user_prompt_template,
    model_name,
    temperature,
    output_schema,
    status,
    promoted_at
) VALUES (
    'extract_skills',
    'extract_skills_v1',
    1,
    'You are an expert at identifying and categorizing professional skills from resume text.',
    'Extract all technical and soft skills from this resume text.

Resume Text:
{resume_text}

Categorize skills into:
- Technical Skills (programming languages, tools, platforms)
- Soft Skills (communication, leadership, etc.)
- Domain Skills (industry-specific knowledge)

Return JSON:
{
    "technical_skills": [
        {
            "skill": "<skill name>",
            "proficiency": "<expert/advanced/intermediate/beginner>",
            "evidence": "<where found in resume>"
        }
    ],
    "soft_skills": [
        {
            "skill": "<skill name>",
            "evidence": "<where demonstrated>"
        }
    ],
    "domain_skills": [
        {
            "skill": "<skill name>",
            "evidence": "<where demonstrated>"
        }
    ]
}',
    'gpt-4',
    0.2,
    '{
        "type": "object",
        "required": ["technical_skills", "soft_skills", "domain_skills"],
        "properties": {
            "technical_skills": {"type": "array"},
            "soft_skills": {"type": "array"},
            "domain_skills": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW()
);

-- =====================================================
-- SKILL: match_job
-- Purpose: Match resume to job description
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    prompt_name,
    prompt_version,
    system_prompt,
    user_prompt_template,
    model_name,
    temperature,
    output_schema,
    status,
    promoted_at
) VALUES (
    'match_job',
    'match_job_v1',
    1,
    'You are a recruiting expert analyzing candidate-job fit based on resume content and job requirements.',
    'Analyze how well this resume matches the job description.

Resume Skills:
{resume_skills}

Job Description:
{job_description}

Provide detailed matching analysis in JSON:
{
    "overall_match": <0-100>,
    "matched_skills": [
        {
            "skill": "<skill name>",
            "required": <boolean>,
            "proficiency_match": "<excellent/good/partial/missing>"
        }
    ],
    "missing_skills": [
        {
            "skill": "<skill name>",
            "importance": "<critical/important/nice-to-have>",
            "can_learn_quickly": <boolean>
        }
    ],
    "recommendation": "<apply/maybe/not_recommended>",
    "reasoning": "<explanation of match assessment>"
}',
    'gpt-4',
    0.4,
    '{
        "type": "object",
        "required": ["overall_match", "matched_skills", "missing_skills", "recommendation"],
        "properties": {
            "overall_match": {"type": "number", "minimum": 0, "maximum": 100},
            "matched_skills": {"type": "array"},
            "missing_skills": {"type": "array"},
            "recommendation": {"type": "string", "enum": ["apply", "maybe", "not_recommended"]},
            "reasoning": {"type": "string"}
        }
    }'::jsonb,
    'production',
    NOW()
);

-- =====================================================
-- SKILL: optimize_summary
-- Purpose: Optimize professional summary
-- =====================================================

INSERT INTO ai_prompts (
    skill_name,
    prompt_name,
    prompt_version,
    system_prompt,
    user_prompt_template,
    model_name,
    temperature,
    output_schema,
    status,
    promoted_at
) VALUES (
    'optimize_summary',
    'optimize_summary_v1',
    1,
    'You are an expert resume writer specializing in compelling professional summaries that highlight unique value propositions.',
    'Optimize this professional summary for maximum impact.

Current Summary:
{current_summary}

Target Role: {target_role}
Experience Level: {experience_level}
Key Strengths: {key_strengths}

Create an optimized summary (3-4 sentences) that:
- Opens with a strong positioning statement
- Highlights unique value proposition
- Includes key achievements or metrics
- Aligns with target role
- Uses powerful but authentic language

Return JSON:
{
    "optimized_summary": "<improved summary text>",
    "improvements_made": [
        {
            "type": "<structure|language|metrics|positioning>",
            "description": "<what was improved>"
        }
    ],
    "key_phrases": [<phrases that strengthen the summary>],
    "confidence": <0.0-1.0>
}',
    'gpt-4',
    0.6,
    '{
        "type": "object",
        "required": ["optimized_summary", "improvements_made", "confidence"],
        "properties": {
            "optimized_summary": {"type": "string", "maxLength": 500},
            "improvements_made": {"type": "array"},
            "key_phrases": {"type": "array"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        }
    }'::jsonb,
    'production',
    NOW()
);

-- Verify seeded prompts
SELECT COUNT(*) as seed_prompt_count FROM ai_prompts WHERE status = 'production';
