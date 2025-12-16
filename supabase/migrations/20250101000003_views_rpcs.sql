-- =====================================================
-- CareerCopilot AI - Views and Stored Procedures
-- Migration: 20250101000003
-- Description: Optimized read patterns and business logic
-- =====================================================

-- =====================================================
-- MATERIALIZED VIEW: Current Resume State
-- Purpose: Fast access to active resume versions
-- =====================================================

CREATE MATERIALIZED VIEW current_resumes AS
SELECT 
    r.id AS resume_id,
    r.user_id,
    r.title AS resume_name,
    rv.id AS version_id,
    rv.version,
    rv.created_at AS version_created_at,
    rv.strength_score,
    rv.content_structured AS full_content,
    r.created_at,
    r.updated_at
FROM resumes r
JOIN resume_versions rv ON r.id = rv.resume_id
WHERE r.deleted_at IS NULL
  AND rv.id = (
      SELECT id FROM resume_versions
      WHERE resume_id = r.id
      ORDER BY version DESC
      LIMIT 1
  );

-- Index for fast user lookups
CREATE INDEX idx_current_resumes_user ON current_resumes(user_id);

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_current_resumes()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY current_resumes;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VIEW: AI Request Summary
-- Purpose: Observability dashboard for AI costs
-- =====================================================

CREATE OR REPLACE VIEW ai_request_summary AS
SELECT 
    DATE_TRUNC('day', req.created_at) AS request_date,
    req.user_id,
    req.skill_name,
    p.prompt_name,
    p.prompt_version,
    COUNT(*) AS request_count,
    AVG(req.latency_ms) AS avg_latency_ms,
    SUM(req.input_tokens) AS total_input_tokens,
    SUM(req.output_tokens) AS total_output_tokens,
    SUM(req.estimated_cost_usd) AS total_cost_usd,
    AVG(CASE WHEN resp.schema_valid THEN 1 ELSE 0 END) AS validation_pass_rate,
    AVG(resp.confidence_score) AS avg_confidence
FROM ai_requests req
LEFT JOIN ai_responses resp ON req.id = resp.request_id
LEFT JOIN ai_prompts p ON req.prompt_id = p.id
GROUP BY DATE_TRUNC('day', req.created_at), req.user_id, req.skill_name, p.prompt_name, p.prompt_version;

-- =====================================================
-- VIEW: Skill Gap Analysis
-- Purpose: Real-time skill matching for jobs
-- =====================================================

CREATE OR REPLACE VIEW user_skill_gaps AS
SELECT 
    sg.user_id,
    sg.job_id,
    jd.title AS job_title,
    jd.company AS company_name,
    sg.required_skill_id AS skill_id,
    s.skill_name,
    s.skill_category,
    sg.has_skill,
    sg.priority_level,
    sg.roi_score,
    sg.created_at AS identified_at,
    CASE 
        WHEN sg.has_skill THEN 0
        WHEN sg.priority_level = 'critical' THEN 4
        WHEN sg.priority_level = 'high' THEN 3
        WHEN sg.priority_level = 'medium' THEN 2
        ELSE 1
    END AS gap_severity
FROM skill_gaps sg
JOIN skills s ON sg.required_skill_id = s.id
JOIN job_descriptions jd ON sg.job_id = jd.id
WHERE jd.deleted_at IS NULL;

-- =====================================================
-- VIEW: Prompt Performance Metrics
-- Purpose: Monitoring prompt quality over time
-- =====================================================

CREATE OR REPLACE VIEW prompt_performance AS
SELECT 
    p.id AS prompt_id,
    p.skill_name,
    p.prompt_version,
    p.status,
    COUNT(DISTINCT req.id) AS total_requests,
    AVG(req.latency_ms) AS avg_latency_ms,
    AVG(req.estimated_cost_usd) AS avg_cost_usd,
    AVG(CASE WHEN resp.schema_valid THEN 1.0 ELSE 0.0 END) AS success_rate,
    AVG(e.helpfulness_score) AS avg_helpfulness,
    AVG(e.safety_score) AS avg_safety,
    COUNT(DISTINCT e.id) AS evaluation_count,
    p.promoted_at
FROM ai_prompts p
LEFT JOIN ai_requests req ON req.prompt_id = p.id
LEFT JOIN ai_responses resp ON resp.request_id = req.id
LEFT JOIN ai_evaluations e ON e.prompt_id = p.id
GROUP BY p.id, p.skill_name, p.prompt_version, p.status, p.promoted_at;

-- =====================================================
-- RPC: Get User's Active Resume with Job Match
-- Purpose: Single call to get resume + job analysis
-- =====================================================

CREATE OR REPLACE FUNCTION get_resume_with_job_match(
    p_user_id UUID,
    p_job_id UUID
)
RETURNS TABLE(
    resume_id UUID,
    resume_name TEXT,
    version INTEGER,
    strength_score INTEGER,
    missing_skills JSONB,
    matched_skills JSONB,
    full_content JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cr.resume_id,
        cr.resume_name,
        cr.version,
        cr.strength_score,
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'skill_name', sg.skill_name,
                    'gap_severity', sg.gap_severity,
                    'priority_level', sg.priority_level,
                    'has_skill', sg.has_skill
                )
            )
            FROM user_skill_gaps sg
            WHERE sg.user_id = p_user_id 
              AND sg.job_id = p_job_id
              AND sg.has_skill = false
        ) AS missing_skills,
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'skill_name', s.skill_name,
                    'proficiency', rs.proficiency_level
                )
            )
            FROM resume_skills rs
            JOIN skills s ON rs.skill_id = s.id
            WHERE rs.resume_version_id = cr.version_id
        ) AS matched_skills,
        cr.full_content
    FROM current_resumes cr
    WHERE cr.user_id = p_user_id
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC: Record AI Request (Used by AI Orchestrator)
-- Purpose: Atomic logging of AI request
-- =====================================================

CREATE OR REPLACE FUNCTION record_ai_request(
    p_user_id UUID,
    p_prompt_id UUID,
    p_skill_name TEXT,
    p_input_data JSONB,
    p_rendered_prompt TEXT,
    p_model_name TEXT,
    p_model_provider TEXT,
    p_temperature NUMERIC,
    p_max_tokens INTEGER,
    p_request_id TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_request_id UUID;
BEGIN
    INSERT INTO ai_requests (
        user_id,
        prompt_id,
        skill_name,
        input_data,
        rendered_prompt,
        model_name,
        model_provider,
        temperature,
        max_tokens,
        request_id,
        started_at
    ) VALUES (
        p_user_id,
        p_prompt_id,
        p_skill_name,
        p_input_data,
        p_rendered_prompt,
        p_model_name,
        p_model_provider,
        p_temperature,
        p_max_tokens,
        COALESCE(p_request_id, gen_random_uuid()::TEXT),
        NOW()
    )
    RETURNING id INTO v_request_id;
    
    RETURN v_request_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC: Record AI Response
-- Purpose: Store validated AI output
-- =====================================================

CREATE OR REPLACE FUNCTION record_ai_response(
    p_request_id UUID,
    p_raw_response TEXT,
    p_parsed_response JSONB,
    p_schema_valid BOOLEAN,
    p_validation_errors JSONB,
    p_confidence_score NUMERIC,
    p_contains_unsafe_content BOOLEAN
)
RETURNS UUID AS $$
DECLARE
    v_response_id UUID;
BEGIN
    INSERT INTO ai_responses (
        request_id,
        raw_response,
        parsed_response,
        schema_valid,
        validation_errors,
        confidence_score,
        contains_unsafe_content
    ) VALUES (
        p_request_id,
        p_raw_response,
        p_parsed_response,
        p_schema_valid,
        p_validation_errors,
        p_confidence_score,
        p_contains_unsafe_content
    )
    RETURNING id INTO v_response_id;
    
    RETURN v_response_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC: Calculate ATS Score
-- Purpose: Deterministic scoring based on keywords
-- =====================================================

CREATE OR REPLACE FUNCTION calculate_ats_score(
    p_resume_version_id UUID,
    p_job_id UUID
)
RETURNS NUMERIC AS $$
DECLARE
    v_score NUMERIC := 0;
    v_required_skills INTEGER;
    v_matched_skills INTEGER;
    v_keyword_matches INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_required_skills
    FROM job_skill_requirements
    WHERE job_id = p_job_id;
    
    SELECT COUNT(DISTINCT jsr.skill_id) INTO v_matched_skills
    FROM job_skill_requirements jsr
    JOIN resume_skills rs ON jsr.skill_id = rs.skill_id
    WHERE jsr.job_id = p_job_id
      AND rs.resume_version_id = p_resume_version_id
      AND rs.proficiency_level >= jsr.minimum_proficiency;
    
    IF v_required_skills > 0 THEN
        v_score := (v_matched_skills::NUMERIC / v_required_skills) * 70;
    END IF;
    
    SELECT COUNT(*) INTO v_keyword_matches
    FROM resume_bullets rb
    JOIN resume_sections rs ON rb.section_id = rs.id
    JOIN job_descriptions jd ON jd.id = p_job_id
    WHERE rs.resume_version_id = p_resume_version_id
      AND jd.required_keywords IS NOT NULL
      AND rb.bullet_text ILIKE '%' || ANY(string_to_array(jd.required_keywords, ',')) || '%';
    
    v_score := v_score + LEAST(v_keyword_matches * 5, 30);
    
    RETURN LEAST(v_score, 100);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- RPC: Get Promotable Prompt Candidates
-- Purpose: Filter candidates ready for production
-- =====================================================

CREATE OR REPLACE FUNCTION get_promotable_prompt_candidates()
RETURNS TABLE(
    candidate_id UUID,
    candidate_name TEXT,
    system_prompt TEXT,
    user_prompt_template TEXT,
    num_evaluations INTEGER,
    avg_score FLOAT,
    improvement_over_parent FLOAT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pc.id,
        pc.candidate_name,
        pc.system_prompt,
        pc.user_prompt_template,
        pc.num_evaluations,
        pc.avg_score,
        pc.improvement_over_parent,
        pc.created_at
    FROM prompt_candidates pc
    WHERE pc.evaluation_status = 'approved'
      AND pc.num_evaluations >= 100
      AND pc.avg_score > 0.75
      AND pc.improvement_over_parent > 0.05
      AND pc.created_at > NOW() - INTERVAL '30 days'
    ORDER BY pc.improvement_over_parent DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC: Promote Prompt to Production
-- Purpose: Safe promotion with rollback support
-- =====================================================

CREATE OR REPLACE FUNCTION promote_prompt_to_production(
    p_candidate_id UUID,
    p_admin_user_id UUID
)
RETURNS UUID AS $$
DECLARE
    v_candidate RECORD;
    v_parent_prompt RECORD;
    v_new_prompt_id UUID;
    v_new_version INTEGER;
BEGIN
    SELECT * INTO v_candidate
    FROM prompt_candidates
    WHERE id = p_candidate_id
      AND evaluation_status = 'approved';
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Candidate not found or not approved';
    END IF;
    
    SELECT * INTO v_parent_prompt
    FROM ai_prompts
    WHERE id = v_candidate.parent_prompt_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Parent prompt not found';
    END IF;
    
    -- Retire current production prompt
    UPDATE ai_prompts
    SET status = 'retired', retired_at = NOW()
    WHERE id = v_candidate.parent_prompt_id
      AND status = 'production';
    
    -- Get next version number for this skill
    SELECT COALESCE(MAX(prompt_version), 0) + 1 INTO v_new_version
    FROM ai_prompts
    WHERE skill_name = v_parent_prompt.skill_name;
    
    -- Create new production prompt from candidate
    INSERT INTO ai_prompts (
        skill_name,
        prompt_name,
        prompt_version,
        system_prompt,
        user_prompt_template,
        model_name,
        model_provider,
        temperature,
        max_tokens,
        output_schema,
        status,
        promoted_at,
        parent_prompt_id,
        created_by
    ) VALUES (
        v_parent_prompt.skill_name,
        v_parent_prompt.skill_name || '_v' || v_new_version,
        v_new_version,
        v_candidate.system_prompt,
        v_candidate.user_prompt_template,
        v_parent_prompt.model_name,
        v_parent_prompt.model_provider,
        v_parent_prompt.temperature,
        v_parent_prompt.max_tokens,
        v_parent_prompt.output_schema,
        'production',
        NOW(),
        v_candidate.parent_prompt_id,
        p_admin_user_id
    )
    RETURNING id INTO v_new_prompt_id;
    
    -- Mark candidate as successfully promoted
    UPDATE prompt_candidates
    SET 
        approved_by = p_admin_user_id,
        approved_at = NOW(),
        updated_at = NOW()
    WHERE id = p_candidate_id;
    
    RETURN v_new_prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Indexes for View Performance
-- =====================================================

CREATE INDEX idx_ai_requests_user_date ON ai_requests(user_id, created_at DESC);
CREATE INDEX idx_ai_requests_created_skill ON ai_requests(created_at, skill_name);
CREATE INDEX idx_prompt_candidates_status_score ON prompt_candidates(evaluation_status, avg_score) 
WHERE evaluation_status = 'approved';
