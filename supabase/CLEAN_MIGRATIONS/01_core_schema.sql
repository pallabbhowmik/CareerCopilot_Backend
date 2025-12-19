-- =====================================================
-- JobPathAI - Step 1: Core Schema
-- Run this FIRST after reset
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =====================================================
-- USER PROFILES
-- =====================================================

CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    target_role TEXT,
    experience_level TEXT CHECK (experience_level IN ('entry', 'mid', 'senior', 'lead', 'executive')),
    country TEXT,
    career_goal TEXT,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_email ON user_profiles(email);

-- =====================================================
-- RESUMES
-- =====================================================

CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    template_id UUID,
    current_version_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT resumes_title_length CHECK (char_length(title) <= 200)
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id);

-- =====================================================
-- RESUME VERSIONS
-- =====================================================

CREATE TABLE resume_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    parent_version_id UUID REFERENCES resume_versions(id),
    content_raw TEXT,
    file_path TEXT,
    file_hash TEXT,
    content_structured JSONB,
    parsing_confidence TEXT CHECK (parsing_confidence IN ('high', 'medium', 'low')),
    parsing_errors JSONB,
    strength_score INT CHECK (strength_score >= 0 AND strength_score <= 100),
    heatmap_data JSONB,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT resume_versions_unique_version UNIQUE(resume_id, version)
);

CREATE INDEX idx_resume_versions_resume_id ON resume_versions(resume_id);
CREATE INDEX idx_resume_versions_status ON resume_versions(status);

-- =====================================================
-- RESUME SECTIONS
-- =====================================================

CREATE TABLE resume_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_version_id UUID NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL CHECK (section_type IN ('header', 'summary', 'experience', 'education', 'skills', 'projects', 'certifications', 'custom')),
    title TEXT,
    content TEXT,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resume_sections_version ON resume_sections(resume_version_id);
CREATE INDEX idx_resume_sections_type ON resume_sections(section_type);

-- =====================================================
-- RESUME BULLETS
-- =====================================================

CREATE TABLE resume_bullets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    section_id UUID NOT NULL REFERENCES resume_sections(id) ON DELETE CASCADE,
    original_text TEXT NOT NULL,
    improved_text TEXT,
    impact_score INT CHECK (impact_score >= 0 AND impact_score <= 100),
    keyword_matches TEXT[],
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resume_bullets_section ON resume_bullets(section_id);

-- =====================================================
-- JOB DESCRIPTIONS
-- =====================================================

CREATE TABLE job_descriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    company_name TEXT,
    job_title TEXT NOT NULL,
    job_url TEXT,
    description_raw TEXT NOT NULL,
    description_structured JSONB,
    required_skills TEXT[],
    preferred_skills TEXT[],
    experience_required TEXT,
    salary_range TEXT,
    location TEXT,
    match_score INT CHECK (match_score >= 0 AND match_score <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_job_descriptions_user ON job_descriptions(user_id);

-- =====================================================
-- SKILLS
-- =====================================================

CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    synonyms TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_skills_category ON skills(category);

-- =====================================================
-- RESUME SKILLS (Junction table)
-- =====================================================

CREATE TABLE resume_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_version_id UUID NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_level TEXT CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    years_experience INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT resume_skills_unique_skill UNIQUE(resume_version_id, skill_id)
);

CREATE INDEX idx_resume_skills_version ON resume_skills(resume_version_id);
CREATE INDEX idx_resume_skills_skill ON resume_skills(skill_id);

-- =====================================================
-- JOB SKILL REQUIREMENTS
-- =====================================================

CREATE TABLE job_skill_requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_description_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_category TEXT,
    importance_level TEXT CHECK (importance_level IN ('required', 'preferred', 'nice_to_have')),
    years_required INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_skill_requirements_job ON job_skill_requirements(job_description_id);

-- =====================================================
-- SKILL GAPS
-- =====================================================

CREATE TABLE skill_gaps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_description_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    gap_severity TEXT CHECK (gap_severity IN ('critical', 'moderate', 'minor')),
    recommendation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT skill_gaps_unique_gap UNIQUE(job_description_id, skill_id)
);

CREATE INDEX idx_skill_gaps_job ON skill_gaps(job_description_id);
CREATE INDEX idx_skill_gaps_skill ON skill_gaps(skill_id);

-- =====================================================
-- APPLICATIONS
-- =====================================================

CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    job_description_id UUID REFERENCES job_descriptions(id) ON DELETE SET NULL,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    application_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'applied' CHECK (status IN ('applied', 'screening', 'interviewing', 'offer', 'rejected', 'accepted', 'declined')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_applications_user ON applications(user_id);
CREATE INDEX idx_applications_status ON applications(status);

-- =====================================================
-- AI PROMPTS
-- =====================================================

CREATE TABLE ai_prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    template TEXT NOT NULL,
    variables JSONB,
    category TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_prompts_name ON ai_prompts(name);
CREATE INDEX idx_ai_prompts_category ON ai_prompts(category);

-- =====================================================
-- AI REQUESTS
-- =====================================================

CREATE TABLE ai_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID REFERENCES ai_prompts(id),
    input_data JSONB NOT NULL,
    context_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_requests_prompt ON ai_requests(prompt_id);

-- =====================================================
-- AI RESPONSES
-- =====================================================

CREATE TABLE ai_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES ai_requests(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    response_data JSONB NOT NULL,
    tokens_used INT,
    latency_ms INT,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_responses_request ON ai_responses(request_id);

-- =====================================================
-- EXPLANATIONS
-- =====================================================

CREATE TABLE explanations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type TEXT NOT NULL,
    content_id UUID NOT NULL,
    explanation TEXT NOT NULL,
    reasoning JSONB,
    confidence_score DECIMAL(3, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_explanations_content ON explanations(content_type, content_id);

-- =====================================================
-- AI EVALUATIONS
-- =====================================================

CREATE TABLE ai_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    response_id UUID NOT NULL REFERENCES ai_responses(id) ON DELETE CASCADE,
    evaluation_metrics JSONB NOT NULL,
    human_rating INT CHECK (human_rating >= 1 AND human_rating <= 5),
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_evaluations_response ON ai_evaluations(response_id);

-- =====================================================
-- PROMPT CANDIDATES
-- =====================================================

CREATE TABLE prompt_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES ai_prompts(id) ON DELETE CASCADE,
    candidate_template TEXT NOT NULL,
    performance_score DECIMAL(5, 2),
    test_results JSONB,
    is_winner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_candidates_prompt ON prompt_candidates(prompt_id);

-- =====================================================
-- TRIGGERS: Auto-update updated_at
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_resume_versions_updated_at BEFORE UPDATE ON resume_versions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_resume_sections_updated_at BEFORE UPDATE ON resume_sections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_resume_bullets_updated_at BEFORE UPDATE ON resume_bullets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_job_descriptions_updated_at BEFORE UPDATE ON job_descriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ai_prompts_updated_at BEFORE UPDATE ON ai_prompts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ✅ Step 1 Complete: Core Schema Created
-- Next: Run 02_enable_rls.sql
-- =====================================================
