-- =====================================================
-- CareerCopilot AI - AI Platform Schema
-- Migration: 20250101000001
-- Description: AI prompts, requests, responses, and evaluation tables
-- =====================================================

-- =====================================================
-- SECTION E: AI PLATFORM (CRITICAL)
-- =====================================================

CREATE TABLE IF NOT EXISTS ai_prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_name TEXT NOT NULL, -- e.g., 'bullet_quality_analyzer_v2'
    prompt_version INT NOT NULL DEFAULT 1,
    skill_name TEXT NOT NULL, -- Which AI skill uses this
    
    -- Prompt content (immutable once in production)
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL, -- With {{variables}}
    
    -- Model configuration
    model_name TEXT NOT NULL DEFAULT 'gpt-4o-mini',
    model_provider TEXT NOT NULL DEFAULT 'openai' CHECK (model_provider IN ('openai', 'anthropic')),
    temperature FLOAT DEFAULT 0.3,
    max_tokens INT DEFAULT 1000,
    
    -- Output schema (Pydantic model name or JSON schema)
    output_schema JSONB,
    
    -- Status and lifecycle
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'staging', 'production', 'retired')),
    promoted_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    parent_prompt_id UUID REFERENCES ai_prompts(id), -- For versioning lineage
    
    -- Performance metadata
    avg_latency_ms FLOAT,
    avg_tokens_used INT,
    avg_cost_usd FLOAT,
    success_rate FLOAT,
    
    -- Quality metrics
    avg_helpfulness_score FLOAT, -- From evaluations
    avg_safety_score FLOAT,
    
    -- Metadata
    created_by UUID REFERENCES user_profiles(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT ai_prompts_unique_name_version UNIQUE(prompt_name, prompt_version),
    CONSTRAINT ai_prompts_status_immutable CHECK (
        (status != 'production' AND status != 'retired') OR 
        (system_prompt IS NOT NULL AND user_prompt_template IS NOT NULL)
    )
);

CREATE INDEX idx_ai_prompts_skill_name ON ai_prompts(skill_name);
CREATE INDEX idx_ai_prompts_status ON ai_prompts(status);
CREATE INDEX idx_ai_prompts_name_version ON ai_prompts(prompt_name, prompt_version);
CREATE INDEX idx_ai_prompts_promoted_at ON ai_prompts(promoted_at) WHERE status = 'production';

-- Function to prevent editing production prompts
CREATE OR REPLACE FUNCTION prevent_production_prompt_edits()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'production' AND (
        OLD.system_prompt != NEW.system_prompt OR 
        OLD.user_prompt_template != NEW.user_prompt_template
    ) THEN
        RAISE EXCEPTION 'Cannot edit production prompts. Create a new version instead.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER protect_production_prompts
    BEFORE UPDATE ON ai_prompts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_production_prompt_edits();

CREATE TABLE IF NOT EXISTS ai_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id TEXT UNIQUE NOT NULL, -- For distributed tracing
    
    -- Context
    user_id UUID REFERENCES user_profiles(user_id),
    resume_version_id UUID REFERENCES resume_versions(id),
    job_id UUID REFERENCES job_descriptions(id),
    
    -- AI configuration
    prompt_id UUID NOT NULL REFERENCES ai_prompts(id),
    skill_name TEXT NOT NULL,
    
    -- Request content
    input_data JSONB NOT NULL,
    rendered_prompt TEXT NOT NULL, -- After template substitution
    
    -- Model details
    model_name TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    temperature FLOAT,
    max_tokens INT,
    
    -- Execution metadata
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    latency_ms INT,
    
    -- Cost tracking
    input_tokens INT,
    output_tokens INT,
    total_tokens INT,
    estimated_cost_usd FLOAT,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed', 'timeout', 'rate_limited')),
    error_message TEXT,
    retry_count INT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_requests_user_id ON ai_requests(user_id);
CREATE INDEX idx_ai_requests_prompt_id ON ai_requests(prompt_id);
CREATE INDEX idx_ai_requests_skill_name ON ai_requests(skill_name);
CREATE INDEX idx_ai_requests_status ON ai_requests(status);
CREATE INDEX idx_ai_requests_created_at ON ai_requests(created_at);
CREATE INDEX idx_ai_requests_request_id ON ai_requests(request_id);

CREATE TABLE IF NOT EXISTS ai_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES ai_requests(id) ON DELETE CASCADE,
    
    -- Response content
    raw_response TEXT NOT NULL, -- Full LLM response
    parsed_response JSONB NOT NULL, -- Structured output
    
    -- Validation
    schema_valid BOOLEAN DEFAULT TRUE,
    validation_errors JSONB,
    
    -- Confidence and quality
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    reasoning_trace JSONB, -- Chain of thought if applicable
    
    -- Safety checks
    contains_unsafe_content BOOLEAN DEFAULT FALSE,
    safety_flags JSONB,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_responses_request_id ON ai_responses(request_id);
CREATE INDEX idx_ai_responses_schema_valid ON ai_responses(schema_valid);
CREATE INDEX idx_ai_responses_confidence ON ai_responses(confidence_score);

CREATE TABLE IF NOT EXISTS explanations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    response_id UUID REFERENCES ai_responses(id) ON DELETE CASCADE,
    
    -- Target context
    resume_version_id UUID REFERENCES resume_versions(id),
    section_id UUID REFERENCES resume_sections(id),
    bullet_id UUID REFERENCES resume_bullets(id),
    
    -- Explanation content
    explanation_type TEXT NOT NULL CHECK (explanation_type IN ('insight', 'warning', 'suggestion', 'reasoning')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    detail TEXT,
    
    -- Evidence linking
    signals JSONB, -- Links to deterministic signals
    ai_interpretation JSONB, -- AI's interpretation
    confidence_level TEXT CHECK (confidence_level IN ('high', 'medium', 'low')),
    
    -- Action guidance
    action_needed BOOLEAN DEFAULT FALSE,
    action_priority TEXT CHECK (action_priority IN ('critical', 'high', 'medium', 'low')),
    action_steps JSONB,
    
    -- UI metadata
    tooltip_text TEXT,
    display_category TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_explanations_response_id ON explanations(response_id);
CREATE INDEX idx_explanations_resume_version ON explanations(resume_version_id);
CREATE INDEX idx_explanations_type ON explanations(explanation_type);
CREATE INDEX idx_explanations_confidence ON explanations(confidence_level);

-- =====================================================
-- SECTION F: AI EVALUATION & IMPROVEMENT
-- =====================================================

CREATE TABLE IF NOT EXISTS ai_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- What's being evaluated
    prompt_id UUID NOT NULL REFERENCES ai_prompts(id),
    evaluation_type TEXT NOT NULL CHECK (evaluation_type IN ('golden_set', 'ab_test', 'human_review', 'auto_check')),
    
    -- Test case
    test_case_id UUID,
    input_data JSONB NOT NULL,
    expected_output JSONB,
    actual_output JSONB NOT NULL,
    
    -- Evaluation metrics
    structural_validity_score FLOAT CHECK (structural_validity_score >= 0 AND structural_validity_score <= 1),
    helpfulness_score FLOAT CHECK (helpfulness_score >= 0 AND helpfulness_score <= 1),
    consistency_score FLOAT CHECK (consistency_score >= 0 AND consistency_score <= 1),
    safety_score FLOAT CHECK (safety_score >= 0 AND safety_score <= 1),
    
    -- Overall assessment
    passed BOOLEAN,
    overall_score FLOAT CHECK (overall_score >= 0 AND overall_score <= 1),
    
    -- Failure analysis
    failure_reasons JSONB,
    
    -- Human reviewer (if applicable)
    reviewed_by UUID REFERENCES user_profiles(user_id),
    reviewer_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_evaluations_prompt_id ON ai_evaluations(prompt_id);
CREATE INDEX idx_ai_evaluations_type ON ai_evaluations(evaluation_type);
CREATE INDEX idx_ai_evaluations_passed ON ai_evaluations(passed);
CREATE INDEX idx_ai_evaluations_created_at ON ai_evaluations(created_at);

CREATE TABLE IF NOT EXISTS prompt_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_prompt_id UUID NOT NULL REFERENCES ai_prompts(id),
    
    -- Candidate details
    candidate_name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    
    -- Generation context
    generation_method TEXT CHECK (generation_method IN ('ai_proposed', 'human_written', 'hybrid')),
    generation_reasoning TEXT,
    
    -- Evaluation results
    evaluation_status TEXT DEFAULT 'pending' CHECK (evaluation_status IN ('pending', 'evaluating', 'approved', 'rejected')),
    num_evaluations INT DEFAULT 0,
    avg_score FLOAT,
    
    -- Statistical comparison with parent
    improvement_over_parent FLOAT, -- Percentage improvement
    statistically_significant BOOLEAN DEFAULT FALSE,
    confidence_interval JSONB, -- [lower, upper]
    
    -- Decision
    approved_by UUID REFERENCES user_profiles(user_id),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_candidates_parent ON prompt_candidates(parent_prompt_id);
CREATE INDEX idx_prompt_candidates_status ON prompt_candidates(evaluation_status);
CREATE INDEX idx_prompt_candidates_approved ON prompt_candidates(approved_at) WHERE approved_at IS NOT NULL;

-- =====================================================
-- SECTION G: APPLICATION TRACKING
-- =====================================================

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    resume_version_id UUID REFERENCES resume_versions(id),
    job_id UUID REFERENCES job_descriptions(id),
    
    -- Application details
    company TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_url TEXT,
    
    -- Status tracking
    status TEXT DEFAULT 'applied' CHECK (status IN ('applied', 'viewed', 'screening', 'interview', 'offer', 'rejected', 'withdrawn')),
    response_received BOOLEAN DEFAULT FALSE,
    interview_scheduled BOOLEAN DEFAULT FALSE,
    
    -- Dates
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    response_at TIMESTAMPTZ,
    interview_at TIMESTAMPTZ,
    outcome_at TIMESTAMPTZ,
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_applications_user_id ON applications(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_applications_resume_version ON applications(resume_version_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_applied_at ON applications(applied_at);

-- =====================================================
-- UPDATED_AT TRIGGERS
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON resumes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON resume_versions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON resume_sections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON resume_bullets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON job_descriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON skills FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON skill_gaps FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON ai_prompts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON explanations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON prompt_candidates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
