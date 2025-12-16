-- =====================================================
-- CareerCopilot AI - Initial Supabase Schema
-- Migration: 20250101000000
-- Description: Core tables for production-grade AI feedback system
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- =====================================================
-- SECTION A: USER CONTEXT
-- =====================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    target_role TEXT,
    experience_level TEXT CHECK (experience_level IN ('entry', 'mid', 'senior', 'lead', 'executive')),
    country TEXT,
    career_goal TEXT,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT user_profiles_user_id_unique UNIQUE(user_id)
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_profiles_email ON user_profiles(email) WHERE deleted_at IS NULL;

-- =====================================================
-- SECTION B: RESUME SYSTEM
-- =====================================================

CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    template_id UUID,
    
    -- Current version tracking
    current_version_id UUID,
    
    -- Variant tracking for A/B testing
    variant_group_id UUID,
    is_control BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT resumes_title_length CHECK (char_length(title) <= 200)
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_resumes_variant_group ON resumes(variant_group_id) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS resume_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    parent_version_id UUID REFERENCES resume_versions(id),
    
    -- Raw content
    content_raw TEXT,
    file_path TEXT,
    file_hash TEXT, -- For deduplication
    
    -- Parsed structure (JSONB for flexibility)
    content_structured JSONB,
    
    -- Parsing metadata
    parsing_confidence TEXT CHECK (parsing_confidence IN ('high', 'medium', 'low')),
    parsing_errors JSONB,
    
    -- Analytics
    strength_score INT CHECK (strength_score >= 0 AND strength_score <= 100),
    heatmap_data JSONB,
    
    -- Status
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT resume_versions_unique_version UNIQUE(resume_id, version)
);

CREATE INDEX idx_resume_versions_resume_id ON resume_versions(resume_id);
CREATE INDEX idx_resume_versions_status ON resume_versions(status);
CREATE INDEX idx_resume_versions_parsing_confidence ON resume_versions(parsing_confidence);

-- Set current_version_id FK after resume_versions exists
ALTER TABLE resumes 
    ADD CONSTRAINT fk_resumes_current_version 
    FOREIGN KEY (current_version_id) 
    REFERENCES resume_versions(id);

CREATE TABLE IF NOT EXISTS resume_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_version_id UUID NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL CHECK (section_type IN ('personal_info', 'summary', 'experience', 'education', 'skills', 'projects', 'certifications', 'languages')),
    section_order INT NOT NULL,
    content JSONB NOT NULL,
    
    -- Analysis results
    ats_signals JSONB, -- Deterministic signals
    ai_feedback JSONB, -- AI interpretations
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resume_sections_version_id ON resume_sections(resume_version_id);
CREATE INDEX idx_resume_sections_type ON resume_sections(section_type);

CREATE TABLE IF NOT EXISTS resume_bullets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    section_id UUID NOT NULL REFERENCES resume_sections(id) ON DELETE CASCADE,
    bullet_text TEXT NOT NULL,
    bullet_order INT NOT NULL,
    
    -- Atomic analysis (deterministic)
    has_action_verb BOOLEAN,
    has_metrics BOOLEAN,
    has_context BOOLEAN,
    char_count INT,
    word_count INT,
    
    -- AI analysis
    strength_score INT CHECK (strength_score >= 0 AND strength_score <= 100),
    improvement_suggestions JSONB,
    tone_assessment TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT bullet_order_per_section UNIQUE(section_id, bullet_order)
);

CREATE INDEX idx_resume_bullets_section_id ON resume_bullets(section_id);
CREATE INDEX idx_resume_bullets_has_metrics ON resume_bullets(has_metrics);

-- =====================================================
-- SECTION C: JOB SYSTEM
-- =====================================================

CREATE TABLE IF NOT EXISTS job_descriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    job_url TEXT,
    
    -- Raw and parsed content
    raw_text TEXT NOT NULL,
    parsed_data JSONB,
    
    -- Extracted requirements
    experience_required TEXT,
    education_required TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    CONSTRAINT job_title_length CHECK (char_length(title) <= 200),
    CONSTRAINT job_company_length CHECK (char_length(company) <= 200)
);

CREATE INDEX idx_job_descriptions_user_id ON job_descriptions(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_job_descriptions_company ON job_descriptions(company) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS job_skill_requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_category TEXT, -- 'technical', 'soft', 'domain'
    is_required BOOLEAN DEFAULT TRUE,
    importance_level TEXT CHECK (importance_level IN ('critical', 'important', 'preferred', 'nice_to_have')),
    
    -- Normalization
    normalized_skill_name TEXT, -- Links to skills taxonomy
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_skill_requirements_job_id ON job_skill_requirements(job_id);
CREATE INDEX idx_job_skill_requirements_skill_name ON job_skill_requirements(normalized_skill_name);

-- =====================================================
-- SECTION D: SKILL INTELLIGENCE
-- =====================================================

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_name TEXT NOT NULL UNIQUE,
    skill_category TEXT CHECK (skill_category IN ('technical', 'soft', 'domain', 'tool', 'framework', 'language')),
    parent_skill_id UUID REFERENCES skills(id),
    
    -- Taxonomy metadata
    aliases TEXT[], -- Alternative names
    related_skills UUID[], -- Related skill IDs
    
    -- Popularity and trend
    popularity_score FLOAT DEFAULT 0.0,
    trend_direction TEXT CHECK (trend_direction IN ('rising', 'stable', 'declining')),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skills_name ON skills(skill_name);
CREATE INDEX idx_skills_category ON skills(skill_category);
CREATE INDEX idx_skills_parent ON skills(parent_skill_id);
CREATE INDEX idx_skills_aliases_gin ON skills USING gin(aliases);

CREATE TABLE IF NOT EXISTS resume_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_version_id UUID NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id),
    
    -- Evidence
    mentioned_in_sections UUID[], -- Array of section IDs
    evidence_strength TEXT CHECK (evidence_strength IN ('strong', 'moderate', 'weak')),
    
    -- Proficiency (if stated)
    proficiency_level TEXT CHECK (proficiency_level IN ('expert', 'advanced', 'intermediate', 'beginner')),
    years_experience FLOAT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT resume_skills_unique UNIQUE(resume_version_id, skill_id)
);

CREATE INDEX idx_resume_skills_version_id ON resume_skills(resume_version_id);
CREATE INDEX idx_resume_skills_skill_id ON resume_skills(skill_id);

CREATE TABLE IF NOT EXISTS skill_gaps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    resume_version_id UUID REFERENCES resume_versions(id),
    job_id UUID REFERENCES job_descriptions(id),
    
    -- Gap identification
    required_skill_id UUID NOT NULL REFERENCES skills(id),
    has_skill BOOLEAN DEFAULT FALSE,
    partial_match_skill_ids UUID[], -- Related skills user has
    
    -- Priority and recommendation
    priority_level TEXT CHECK (priority_level IN ('critical', 'high', 'medium', 'low')),
    roi_score FLOAT, -- Return on investment for learning this skill
    
    -- Learning resources
    recommended_resources JSONB,
    estimated_learning_time TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skill_gaps_user_id ON skill_gaps(user_id);
CREATE INDEX idx_skill_gaps_resume_version ON skill_gaps(resume_version_id);
CREATE INDEX idx_skill_gaps_job_id ON skill_gaps(job_id);
CREATE INDEX idx_skill_gaps_priority ON skill_gaps(priority_level);

-- To be continued in next migration file...
