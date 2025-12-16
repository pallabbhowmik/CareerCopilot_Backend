-- =====================================================
-- Additional AI Skills for Frontend Integration
-- Migration: 20250101000005
-- Description: 7 additional skills for complete feature set
-- =====================================================

-- =====================================================
-- SKILL: improve_bullet
-- Purpose: Suggest improvements to a single bullet point
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
    'improve_bullet',
    1,
    'Improve this resume bullet point while preserving the core facts.

Original Bullet:
{original_text}

Context:
Section Type: {context.section_type}
Current Signals: {context.current_signals}

Guidelines:
1. Use strong action verbs
2. Add quantifiable metrics if facts support it
3. Apply STAR format (Situation, Task, Action, Result)
4. Keep length appropriate (1-2 lines)
5. Preserve truthfulness - do NOT invent facts
6. Improve clarity and impact

Return JSON:
{{
    "improved_text": "<improved bullet point>",
    "explanation": "<why this is better>",
    "signals_used": [<list of signals from original>],
    "changes_made": [
        {{
            "type": "<action_verb|metric|structure|clarity>",
            "description": "<what changed>"
        }}
    ],
    "confidence": <0.0-1.0>,
    "preserves_facts": <true|false>
}}',
    'gpt-4',
    0.7,
    '{
        "type": "object",
        "required": ["improved_text", "explanation", "signals_used", "confidence", "preserves_facts"],
        "properties": {
            "improved_text": {"type": "string", "maxLength": 200},
            "explanation": {"type": "string"},
            "signals_used": {"type": "array"},
            "changes_made": {"type": "array"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "preserves_facts": {"type": "boolean"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Improves single bullet point with explanation",
        "max_tokens": 1000,
        "typical_cost": 0.03,
        "typical_latency_ms": 2000
    }'::jsonb
);

-- =====================================================
-- SKILL: explain_bullet_strength
-- Purpose: Explain why a bullet is strong or weak
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
    'explain_bullet_strength',
    1,
    'Explain why this resume bullet point is effective or needs improvement.

Bullet Point:
{bullet_text}

Deterministic Signals Detected:
{signals}

Provide user-friendly explanation in JSON:
{{
    "strength_level": "<strong|moderate|weak>",
    "explanation": "<why it is strong or weak>",
    "key_strengths": [<list of good elements>],
    "improvement_areas": [<list of what could be better>],
    "signals_explained": [
        {{
            "signal": "<signal name>",
            "meaning": "<what this signal indicates>",
            "impact": "<positive|neutral|negative>"
        }}
    ]
}}',
    'gpt-4',
    0.3,
    '{
        "type": "object",
        "required": ["strength_level", "explanation", "key_strengths", "improvement_areas"],
        "properties": {
            "strength_level": {"type": "string", "enum": ["strong", "moderate", "weak"]},
            "explanation": {"type": "string", "maxLength": 300},
            "key_strengths": {"type": "array"},
            "improvement_areas": {"type": "array"},
            "signals_explained": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Explains bullet point quality based on signals",
        "max_tokens": 800,
        "typical_cost": 0.025,
        "typical_latency_ms": 1800
    }'::jsonb
);

-- =====================================================
-- SKILL: summarize_section_quality
-- Purpose: Summarize heatmap scores in plain language
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
    'summarize_section_quality',
    1,
    'Translate this deterministic quality score into user-friendly language.

Section Type: {section_type}
Deterministic Score: {deterministic_score}/100
Detected Signals: {signals}

Provide concise summary (max 2 sentences) in JSON:
{{
    "summary": "<plain language summary>",
    "top_issue": "<main thing to fix, if any>",
    "tone": "<encouraging|neutral|constructive>"
}}

Guidelines:
- Be encouraging but honest
- Focus on actionable feedback
- Reference specific signals
- Keep it brief',
    'gpt-4',
    0.5,
    '{
        "type": "object",
        "required": ["summary", "tone"],
        "properties": {
            "summary": {"type": "string", "maxLength": 200},
            "top_issue": {"type": "string"},
            "tone": {"type": "string", "enum": ["encouraging", "neutral", "constructive"]}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Summarizes deterministic scores for heatmap",
        "max_tokens": 400,
        "typical_cost": 0.015,
        "typical_latency_ms": 1200
    }'::jsonb
);

-- =====================================================
-- SKILL: recommend_template
-- Purpose: Recommend best templates for user
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
    'recommend_template',
    1,
    'Recommend the best resume templates for this user.

User Profile:
Role: {role}
Country: {country}
Experience: {experience_years} years

Available Templates:
{available_templates}

Select top 3 templates and explain why in JSON:
{{
    "top_3": [
        {{
            "template_id": "<template id>",
            "reason": "<why this fits>",
            "suitability_score": <0-100>
        }}
    ],
    "reasoning": "<overall recommendation strategy>"
}}

Consider:
- Industry norms for the role
- Regional preferences (country)
- Experience level appropriateness
- ATS compatibility
- Professional appearance',
    'gpt-4',
    0.4,
    '{
        "type": "object",
        "required": ["top_3", "reasoning"],
        "properties": {
            "top_3": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3
            },
            "reasoning": {"type": "string"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Recommends templates based on user profile",
        "max_tokens": 1200,
        "typical_cost": 0.035,
        "typical_latency_ms": 2200
    }'::jsonb
);

-- =====================================================
-- SKILL: explain_ats_risk
-- Purpose: Explain ATS check results
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
    'explain_ats_risk',
    1,
    'Explain this ATS compatibility check result to the user.

Check Name: {check_name}
Result: {result}
Context: {context}

Provide clear explanation and fix suggestion in JSON:
{{
    "explanation": "<what this check means>",
    "why_it_matters": "<impact on ATS parsing>",
    "fix_suggestion": "<how to fix it>",
    "urgency": "<critical|important|nice-to-have>",
    "example": "<concrete example if helpful>"
}}

Guidelines:
- Use plain language (avoid technical jargon)
- Be specific about what to change
- Explain the ATS impact
- Keep tone helpful, not alarming',
    'gpt-4',
    0.3,
    '{
        "type": "object",
        "required": ["explanation", "why_it_matters", "fix_suggestion", "urgency"],
        "properties": {
            "explanation": {"type": "string"},
            "why_it_matters": {"type": "string"},
            "fix_suggestion": {"type": "string"},
            "urgency": {"type": "string", "enum": ["critical", "important", "nice-to-have"]},
            "example": {"type": "string"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Explains ATS check results with fix suggestions",
        "max_tokens": 1000,
        "typical_cost": 0.03,
        "typical_latency_ms": 1800
    }'::jsonb
);

-- =====================================================
-- SKILL: explain_skill_gaps
-- Purpose: Explain missing skills and prioritize actions
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
    'explain_skill_gaps',
    1,
    'Analyze skill gaps between resume and job description.

Job Description:
{job_description}

Resume Skills:
{resume_skills}

Identified Gaps (deterministic):
{identified_gaps}

Provide reasoning and prioritization in JSON:
{{
    "gap_analysis": [
        {{
            "skill": "<skill name>",
            "importance": "<critical|important|nice-to-have>",
            "why_it_matters": "<explanation>",
            "how_to_address": "<concrete suggestions>",
            "timeline": "<immediate|short-term|long-term>"
        }}
    ],
    "prioritized_actions": [
        "<ordered list of what to do first>"
    ],
    "overall_assessment": "<honest assessment of fit>",
    "encouragement": "<balanced, realistic encouragement>"
}}

Guidelines:
- Be honest but encouraging
- Prioritize learnable vs. experience-based gaps
- Suggest specific actions
- No false guarantees
- Acknowledge strengths too',
    'gpt-4',
    0.4,
    '{
        "type": "object",
        "required": ["gap_analysis", "prioritized_actions", "overall_assessment"],
        "properties": {
            "gap_analysis": {"type": "array"},
            "prioritized_actions": {"type": "array"},
            "overall_assessment": {"type": "string"},
            "encouragement": {"type": "string"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Explains skill gaps with prioritized actions",
        "max_tokens": 2000,
        "typical_cost": 0.06,
        "typical_latency_ms": 3500
    }'::jsonb
);

-- =====================================================
-- SKILL: career_advisor
-- Purpose: Career copilot chat responses
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
    'career_advisor',
    1,
    'You are a calm, professional career advisor. Answer the user''s question based on their context.

User Question:
{user_question}

User Context:
Profile: {user_profile}
Resume: {resume_summary}
Skill Gaps: {skill_gaps}
Market Data: {market_context}

Provide helpful response in JSON:
{{
    "response_text": "<your response>",
    "action_items": [
        {{
            "action": "<specific thing to do>",
            "why": "<why it helps>",
            "priority": "<high|medium|low>"
        }}
    ],
    "sources": [<if you reference specific data>],
    "follow_up_questions": [<2-3 suggested follow-ups>]
}}

STRICT GUIDELINES:
- Be calm and professional
- No guarantees or predictions
- Always link to user''s specific context
- Suggest concrete actions
- Admit uncertainty when appropriate
- No hyperbole or exaggeration
- Focus on what user can control',
    'gpt-4',
    0.6,
    '{
        "type": "object",
        "required": ["response_text"],
        "properties": {
            "response_text": {"type": "string"},
            "action_items": {"type": "array"},
            "sources": {"type": "array"},
            "follow_up_questions": {"type": "array"}
        }
    }'::jsonb,
    'production',
    NOW(),
    '{
        "description": "Career copilot chat with strong guardrails",
        "max_tokens": 2500,
        "typical_cost": 0.08,
        "typical_latency_ms": 4000
    }'::jsonb
);

-- =====================================================
-- Update indexes for new skills
-- =====================================================

-- Already covered by existing indexes, but verify
SELECT COUNT(*) FROM ai_prompts WHERE status = 'production';
-- Should return 12 prompts (5 original + 7 new)
