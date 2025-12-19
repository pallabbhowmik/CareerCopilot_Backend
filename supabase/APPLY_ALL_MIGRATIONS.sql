-- =====================================================
-- JobPathAI - Complete Database Setup
-- Run this ENTIRE script in Supabase SQL Editor
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =====================================================
-- STEP 1: Create Core Tables
-- =====================================================

-- User Profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    target_role TEXT,
    experience_level TEXT,
    country TEXT,
    career_goal TEXT,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add missing columns if they don't exist
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Drop existing check constraint if it exists and recreate
DO $$ BEGIN
    ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_experience_level_check;
    ALTER TABLE user_profiles ADD CONSTRAINT user_profiles_experience_level_check 
        CHECK (experience_level IN ('entry', 'mid', 'senior', 'lead', 'executive'));
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- Add unique constraint if not exists
DO $$ BEGIN
    ALTER TABLE user_profiles ADD CONSTRAINT user_profiles_user_id_unique UNIQUE(user_id);
EXCEPTION WHEN duplicate_table THEN NULL;
WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);

-- Resumes
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    template_id UUID,
    current_version_id UUID,
    variant_group_id UUID,
    is_control BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add missing columns if they don't exist
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Add check constraint if not exists
DO $$ BEGIN
    ALTER TABLE resumes DROP CONSTRAINT IF EXISTS resumes_title_length;
    ALTER TABLE resumes ADD CONSTRAINT resumes_title_length CHECK (char_length(title) <= 200);
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_variant_group ON resumes(variant_group_id);

-- Resume Versions
CREATE TABLE IF NOT EXISTS resume_versions (
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

CREATE INDEX IF NOT EXISTS idx_resume_versions_resume_id ON resume_versions(resume_id);
CREATE INDEX IF NOT EXISTS idx_resume_versions_status ON resume_versions(status);

-- Resume Sections
CREATE TABLE IF NOT EXISTS resume_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_version_id UUID NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL CHECK (section_type IN ('header', 'summary', 'experience', 'education', 'skills', 'projects', 'certifications', 'custom')),
    title TEXT,
    content TEXT,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resume_sections_version ON resume_sections(resume_version_id);
CREATE INDEX IF NOT EXISTS idx_resume_sections_type ON resume_sections(section_type);

-- Resume Bullets
CREATE TABLE IF NOT EXISTS resume_bullets (
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

CREATE INDEX IF NOT EXISTS idx_resume_bullets_section ON resume_bullets(section_id);

-- Job Descriptions
CREATE TABLE IF NOT EXISTS job_descriptions (
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
    match_score INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add missing columns if they don't exist
ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Add check constraint
DO $$ BEGIN
    ALTER TABLE job_descriptions DROP CONSTRAINT IF EXISTS job_descriptions_match_score_check;
    ALTER TABLE job_descriptions ADD CONSTRAINT job_descriptions_match_score_check 
        CHECK (match_score >= 0 AND match_score <= 100);
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_job_descriptions_user ON job_descriptions(user_id);

-- Job Skill Requirements
CREATE TABLE IF NOT EXISTS job_skill_requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_description_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_category TEXT,
    importance_level TEXT CHECK (importance_level IN ('required', 'preferred', 'nice_to_have')),
    years_required INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_skill_requirements_job ON job_skill_requirements(job_description_id);

-- Skills
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    synonyms TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);

-- Resume Skills
CREATE TABLE IF NOT EXISTS resume_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_version_id UUID NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_level TEXT CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    years_experience INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT resume_skills_unique_skill UNIQUE(resume_version_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_resume_skills_version ON resume_skills(resume_version_id);
CREATE INDEX IF NOT EXISTS idx_resume_skills_skill ON resume_skills(skill_id);

-- Skill Gaps
CREATE TABLE IF NOT EXISTS skill_gaps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_description_id UUID NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    gap_severity TEXT CHECK (gap_severity IN ('critical', 'moderate', 'minor')),
    recommendation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT skill_gaps_unique_gap UNIQUE(job_description_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_skill_gaps_job ON skill_gaps(job_description_id);
CREATE INDEX IF NOT EXISTS idx_skill_gaps_skill ON skill_gaps(skill_id);

-- Applications
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    job_description_id UUID REFERENCES job_descriptions(id) ON DELETE SET NULL,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    application_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'applied',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add missing columns if they don't exist
ALTER TABLE applications ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Add check constraint
DO $$ BEGIN
    ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_status_check;
    ALTER TABLE applications ADD CONSTRAINT applications_status_check 
        CHECK (status IN ('applied', 'screening', 'interviewing', 'offer', 'rejected', 'accepted', 'declined'));
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

-- =====================================================
-- STEP 2: Create AI Platform Tables
-- =====================================================

-- AI Prompts
CREATE TABLE IF NOT EXISTS ai_prompts (
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

CREATE INDEX IF NOT EXISTS idx_ai_prompts_name ON ai_prompts(name);
CREATE INDEX IF NOT EXISTS idx_ai_prompts_category ON ai_prompts(category);

-- AI Requests
CREATE TABLE IF NOT EXISTS ai_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID REFERENCES ai_prompts(id),
    input_data JSONB NOT NULL,
    context_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_requests_prompt ON ai_requests(prompt_id);

-- AI Responses
CREATE TABLE IF NOT EXISTS ai_responses (
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

CREATE INDEX IF NOT EXISTS idx_ai_responses_request ON ai_responses(request_id);

-- Explanations
CREATE TABLE IF NOT EXISTS explanations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type TEXT NOT NULL,
    content_id UUID NOT NULL,
    explanation TEXT NOT NULL,
    reasoning JSONB,
    confidence_score DECIMAL(3, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_explanations_content ON explanations(content_type, content_id);

-- AI Evaluations
CREATE TABLE IF NOT EXISTS ai_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    response_id UUID NOT NULL REFERENCES ai_responses(id) ON DELETE CASCADE,
    evaluation_metrics JSONB NOT NULL,
    human_rating INT CHECK (human_rating >= 1 AND human_rating <= 5),
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_evaluations_response ON ai_evaluations(response_id);

-- Prompt Candidates
CREATE TABLE IF NOT EXISTS prompt_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES ai_prompts(id) ON DELETE CASCADE,
    candidate_template TEXT NOT NULL,
    performance_score DECIMAL(5, 2),
    test_results JSONB,
    is_winner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_candidates_prompt ON prompt_candidates(prompt_id);

-- =====================================================
-- STEP 3: Enable RLS on All Tables
-- =====================================================

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_bullets ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_skill_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE explanations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- STEP 4: Drop Old Policies (if they exist)
-- =====================================================

DROP POLICY IF EXISTS "Users can read own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can read own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can create resumes" ON resumes;
DROP POLICY IF EXISTS "Users can update own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can delete own resumes" ON resumes;

-- =====================================================
-- STEP 5: Create Fixed RLS Policies
-- =====================================================

-- USER PROFILES
CREATE POLICY "Users can read own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- RESUMES
CREATE POLICY "Users can read own resumes"
    ON resumes FOR SELECT
    USING (auth.uid() = user_id AND deleted_at IS NULL);

CREATE POLICY "Users can create resumes"
    ON resumes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own resumes"
    ON resumes FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own resumes"
    ON resumes FOR DELETE
    USING (auth.uid() = user_id);

-- RESUME VERSIONS
CREATE POLICY "Users can read own resume versions"
    ON resume_versions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create resume versions"
    ON resume_versions FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update own resume versions"
    ON resume_versions FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
        )
    );

-- RESUME SECTIONS
CREATE POLICY "Users can read own resume sections"
    ON resume_sections FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_sections.resume_version_id
            AND r.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create resume sections"
    ON resume_sections FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_sections.resume_version_id
            AND r.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update resume sections"
    ON resume_sections FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_sections.resume_version_id
            AND r.user_id = auth.uid()
        )
    );

-- RESUME BULLETS
CREATE POLICY "Users can read own resume bullets"
    ON resume_bullets FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rs.id = resume_bullets.section_id
            AND r.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create resume bullets"
    ON resume_bullets FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rs.id = resume_bullets.section_id
            AND r.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update resume bullets"
    ON resume_bullets FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rs.id = resume_bullets.section_id
            AND r.user_id = auth.uid()
        )
    );

-- JOB DESCRIPTIONS
CREATE POLICY "Users can read own job descriptions"
    ON job_descriptions FOR SELECT
    USING (auth.uid() = user_id AND deleted_at IS NULL);

CREATE POLICY "Users can create job descriptions"
    ON job_descriptions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update job descriptions"
    ON job_descriptions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete job descriptions"
    ON job_descriptions FOR DELETE
    USING (auth.uid() = user_id);

-- APPLICATIONS
CREATE POLICY "Users can read own applications"
    ON applications FOR SELECT
    USING (auth.uid() = user_id AND deleted_at IS NULL);

CREATE POLICY "Users can create applications"
    ON applications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update applications"
    ON applications FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete applications"
    ON applications FOR DELETE
    USING (auth.uid() = user_id);

-- SKILLS (READ-ONLY for authenticated users)
CREATE POLICY "Authenticated users can read skills"
    ON skills FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- RESUME SKILLS
CREATE POLICY "Users can read own resume skills"
    ON resume_skills FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_skills.resume_version_id
            AND r.user_id = auth.uid()
        )
    );

-- SKILL GAPS
CREATE POLICY "Users can read own skill gaps"
    ON skill_gaps FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM job_descriptions jd
            WHERE jd.id = skill_gaps.job_description_id
            AND jd.user_id = auth.uid()
        )
    );

-- AI PROMPTS (Everyone can read)
CREATE POLICY "Anyone can read ai prompts"
    ON ai_prompts FOR SELECT
    USING (true);

-- AI REQUESTS (Authenticated users)
CREATE POLICY "Authenticated users can manage ai requests"
    ON ai_requests FOR ALL
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

-- AI RESPONSES (Authenticated users)
CREATE POLICY "Authenticated users can manage ai responses"
    ON ai_responses FOR ALL
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

-- EXPLANATIONS (Authenticated users can read)
CREATE POLICY "Authenticated users can read explanations"
    ON explanations FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- =====================================================
-- STEP 6: Create Updated At Trigger
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE column_name = 'updated_at' 
        AND table_schema = 'public'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SUCCESS! Database is ready to use
-- =====================================================
