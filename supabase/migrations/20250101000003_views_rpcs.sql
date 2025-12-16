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
    rv.version_number,
    rv.created_at AS version_created_at,
    rv.ats_score,
    rv.match_percentage,
    COALESCE(
        jsonb_build_object(
            'contact', rv.contact_info,
            'summary', rv.summary,
            'sections', (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'type', rs.section_type,
                        'order', rs.section_order,
                        'bullets', (
                            SELECT jsonb_agg(
                                jsonb_build_object(
                                    'text', rb.bullet_text,
                                    'order', rb.bullet_order,
                                    'signals', rb.signals
                                )
                                ORDER BY rb.bullet_order
                            )
                            FROM resume_bullets rb
                            WHERE rb.section_id = rs.id
                        )
                    )
                    ORDER BY rs.section_order
                )
                FROM resume_sections rs
                WHERE rs.resume_version_id = rv.id
            )
        ),
        '{}'::jsonb
    ) AS full_content,
    r.created_at,
    r.updated_at
FROM resumes r
JOIN resume_versions rv ON r.id = rv.resume_id
WHERE r.is_active = true
  AND r.deleted_at IS NULL
  AND rv.id = (
      SELECT id FROM resume_versions
      WHERE resume_id = r.id
      ORDER BY version_number DESC
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
    req.prompt_version,
    COUNT(*) AS request_count,
    AVG(req.latency_ms) AS avg_latency_ms,
    SUM(req.input_tokens) AS total_input_tokens,
    SUM(req.output_tokens) AS total_output_tokens,
    SUM(req.estimated_cost_usd) AS total_cost_usd,
    AVG(CASE WHEN resp.validation_passed THEN 1 ELSE 0 END) AS validation_pass_rate,
    AVG(resp.confidence_score) AS avg_confidence
FROM ai_requests req
LEFT JOIN ai_responses resp ON req.id = resp.request_id
GROUP BY DATE_TRUNC('day', req.created_at), req.user_id, req.skill_name, req.prompt_version;

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
    sg.skill_id,
    s.name AS skill_name,
    s.category AS skill_category,
    sg.proficiency_level_required,
    sg.proficiency_level_current,
    sg.identified_at,
    -- Gap severity: required - current (higher = bigger gap)
    (sg.proficiency_level_required - COALESCE(sg.proficiency_level_current, 0)) AS gap_severity,
    -- Check if skill is learnable
    s.is_technical AS is_technical_skill
FROM skill_gaps sg
JOIN skills s ON sg.skill_id = s.id
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
    p.version,
    p.status,
    p.total_uses,
    p.avg_latency_ms,
    p.avg_cost_usd,
    p.success_rate,
    -- Aggregate evaluation metrics
    AVG(e.helpfulness_score) AS avg_helpfulness,
    AVG(e.safety_score) AS avg_safety,
    AVG(e.consistency_score) AS avg_consistency,
    COUNT(DISTINCT e.id) AS evaluation_count,
    p.deployed_at,
    p.last_used_at
FROM ai_prompts p
LEFT JOIN ai_requests req ON req.prompt_version = CONCAT(p.skill_name, '_v', p.version)
LEFT JOIN ai_responses resp ON resp.request_id = req.id
LEFT JOIN ai_evaluations e ON e.response_id = resp.id
GROUP BY p.id, p.skill_name, p.version, p.status, p.total_uses, 
         p.avg_latency_ms, p.avg_cost_usd, p.success_rate, p.deployed_at, p.last_used_at;

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
    version_number INTEGER,
    match_percentage NUMERIC,
    ats_score NUMERIC,
    missing_skills JSONB,
    matched_skills JSONB,
    full_content JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cr.resume_id,
        cr.resume_name,
        cr.version_number,
        cr.match_percentage,
        cr.ats_score,
        -- Missing skills
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'skill_name', sg.skill_name,
                    'gap_severity', sg.gap_severity,
                    'proficiency_required', sg.proficiency_level_required
                )
            )
            FROM user_skill_gaps sg
            WHERE sg.user_id = p_user_id 
              AND sg.job_id = p_job_id
              AND sg.gap_severity > 0
        ) AS missing_skills,
        -- Matched skills
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'skill_name', s.name,
                    'proficiency', rs.proficiency_level,
                    'evidence_count', rs.evidence_count
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
-- Purpose: Atomic logging of AI request with validation
-- =====================================================

CREATE OR REPLACE FUNCTION record_ai_request(
    p_user_id UUID,
    p_skill_name TEXT,
    p_prompt_version TEXT,
    p_model TEXT,
    p_temperature NUMERIC,
    p_input_data JSONB,
    p_latency_ms INTEGER,
    p_input_tokens INTEGER,
    p_output_tokens INTEGER,
    p_estimated_cost_usd NUMERIC,
    p_trace_id TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_request_id UUID;
BEGIN
    INSERT INTO ai_requests (
        user_id,
        skill_name,
        prompt_version,
        model,
        temperature,
        input_data,
        latency_ms,
        input_tokens,
        output_tokens,
        estimated_cost_usd,
        trace_id
    ) VALUES (
        p_user_id,
        p_skill_name,
        p_prompt_version,
        p_model,
        p_temperature,
        p_input_data,
        p_latency_ms,
        p_input_tokens,
        p_output_tokens,
        p_estimated_cost_usd,
        COALESCE(p_trace_id, gen_random_uuid()::TEXT)
    )
    RETURNING id INTO v_request_id;
    
    -- Update prompt statistics
    UPDATE ai_prompts
    SET 
        total_uses = total_uses + 1,
        avg_latency_ms = ((avg_latency_ms * total_uses) + p_latency_ms) / (total_uses + 1),
        avg_cost_usd = ((avg_cost_usd * total_uses) + p_estimated_cost_usd) / (total_uses + 1),
        last_used_at = NOW()
    WHERE CONCAT(skill_name, '_v', version) = p_prompt_version;
    
    RETURN v_request_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC: Record AI Response
-- Purpose: Store validated AI output
-- =====================================================

CREATE OR REPLACE FUNCTION record_ai_response(
    p_request_id UUID,
    p_raw_output TEXT,
    p_structured_output JSONB,
    p_validation_passed BOOLEAN,
    p_validation_errors JSONB,
    p_confidence_score NUMERIC,
    p_safety_check_passed BOOLEAN
)
RETURNS UUID AS $$
DECLARE
    v_response_id UUID;
BEGIN
    INSERT INTO ai_responses (
        request_id,
        raw_output,
        structured_output,
        validation_passed,
        validation_errors,
        confidence_score,
        safety_check_passed
    ) VALUES (
        p_request_id,
        p_raw_output,
        p_structured_output,
        p_validation_passed,
        p_validation_errors,
        p_confidence_score,
        p_safety_check_passed
    )
    RETURNING id INTO v_response_id;
    
    -- Update prompt success rate
    UPDATE ai_prompts
    SET success_rate = (
        SELECT AVG(CASE WHEN validation_passed THEN 1.0 ELSE 0.0 END)
        FROM ai_responses resp
        JOIN ai_requests req ON resp.request_id = req.id
        WHERE CONCAT(ai_prompts.skill_name, '_v', ai_prompts.version) = req.prompt_version
    )
    WHERE id IN (
        SELECT p.id 
        FROM ai_prompts p
        JOIN ai_requests req ON CONCAT(p.skill_name, '_v', p.version) = req.prompt_version
        WHERE req.id = p_request_id
    );
    
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
    -- Count required skills
    SELECT COUNT(*) INTO v_required_skills
    FROM job_skill_requirements
    WHERE job_id = p_job_id;
    
    -- Count matched skills
    SELECT COUNT(DISTINCT jsr.skill_id) INTO v_matched_skills
    FROM job_skill_requirements jsr
    JOIN resume_skills rs ON jsr.skill_id = rs.skill_id
    WHERE jsr.job_id = p_job_id
      AND rs.resume_version_id = p_resume_version_id
      AND rs.proficiency_level >= jsr.minimum_proficiency;
    
    -- Calculate base score from skills (0-70 points)
    IF v_required_skills > 0 THEN
        v_score := (v_matched_skills::NUMERIC / v_required_skills) * 70;
    END IF;
    
    -- Count keyword matches in resume bullets (0-30 points)
    SELECT COUNT(*) INTO v_keyword_matches
    FROM resume_bullets rb
    JOIN resume_sections rs ON rb.section_id = rs.id
    JOIN job_descriptions jd ON jd.id = p_job_id
    WHERE rs.resume_version_id = p_resume_version_id
      AND (
          rb.bullet_text ILIKE '%' || ANY(string_to_array(jd.required_keywords, ',')) || '%'
      );
    
    -- Add keyword score (cap at 30)
    v_score := v_score + LEAST(v_keyword_matches * 5, 30);
    
    RETURN LEAST(v_score, 100);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- RPC: Get Prompt Candidates Ready for Production
-- Purpose: Filter candidates that meet promotion criteria
-- =====================================================

CREATE OR REPLACE FUNCTION get_promotable_prompt_candidates()
RETURNS TABLE(
    candidate_id UUID,
    skill_name TEXT,
    new_prompt_text TEXT,
    test_run_count INTEGER,
    avg_score NUMERIC,
    vs_current_delta NUMERIC,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pc.id,
        pc.skill_name,
        pc.new_prompt_text,
        pc.test_run_count,
        pc.avg_score,
        pc.vs_current_delta,
        pc.created_at
    FROM prompt_candidates pc
    WHERE pc.status = 'validated'
      AND pc.test_run_count >= 100  -- Minimum statistical significance
      AND pc.avg_score > 0.75       -- Minimum quality bar
      AND pc.vs_current_delta > 0.05 -- Must be 5%+ better
      AND pc.created_at > NOW() - INTERVAL '30 days' -- Recent only
    ORDER BY pc.vs_current_delta DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC: Promote Prompt Candidate to Production
-- Purpose: Safe promotion with rollback support
-- =====================================================

CREATE OR REPLACE FUNCTION promote_prompt_to_production(
    p_candidate_id UUID,
    p_admin_user_id UUID
)
RETURNS UUID AS $$
DECLARE
    v_candidate RECORD;
    v_current_prompt_id UUID;
    v_new_prompt_id UUID;
    v_new_version INTEGER;
BEGIN
    -- Get candidate details
    SELECT * INTO v_candidate
    FROM prompt_candidates
    WHERE id = p_candidate_id
      AND status = 'validated';
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Candidate not found or not validated';
    END IF;
    
    -- Get current production prompt
    SELECT id INTO v_current_prompt_id
    FROM ai_prompts
    WHERE skill_name = v_candidate.skill_name
      AND status = 'production'
    ORDER BY version DESC
    LIMIT 1;
    
    -- Retire current prompt
    IF v_current_prompt_id IS NOT NULL THEN
        UPDATE ai_prompts
        SET status = 'retired'
        WHERE id = v_current_prompt_id;
    END IF;
    
    -- Get next version number
    SELECT COALESCE(MAX(version), 0) + 1 INTO v_new_version
    FROM ai_prompts
    WHERE skill_name = v_candidate.skill_name;
    
    -- Create new production prompt
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
    )
    SELECT 
        v_candidate.skill_name,
        v_new_version,
        v_candidate.new_prompt_text,
        model,
        temperature,
        expected_output_schema,
        'production',
        NOW(),
        jsonb_build_object(
            'promoted_from_candidate', p_candidate_id,
            'promoted_by', p_admin_user_id,
            'predecessor_prompt', v_current_prompt_id,
            'test_results', jsonb_build_object(
                'test_run_count', v_candidate.test_run_count,
                'avg_score', v_candidate.avg_score,
                'vs_current_delta', v_candidate.vs_current_delta
            )
        )
    FROM ai_prompts
    WHERE id = v_current_prompt_id
    RETURNING id INTO v_new_prompt_id;
    
    -- Mark candidate as deployed
    UPDATE prompt_candidates
    SET 
        status = 'deployed',
        deployed_prompt_id = v_new_prompt_id,
        updated_at = NOW()
    WHERE id = p_candidate_id;
    
    RETURN v_new_prompt_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Indexes for View Performance
-- =====================================================

-- ai_requests aggregations
CREATE INDEX idx_ai_requests_date_skill ON ai_requests(DATE_TRUNC('day', created_at), skill_name);
CREATE INDEX idx_ai_requests_user_date ON ai_requests(user_id, created_at DESC);

-- ai_evaluations lookups
CREATE INDEX idx_ai_evaluations_response ON ai_evaluations(response_id);

-- prompt_candidates filtering
CREATE INDEX idx_prompt_candidates_status_score ON prompt_candidates(status, avg_score) 
WHERE status = 'validated';
