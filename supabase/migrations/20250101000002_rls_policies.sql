-- =====================================================
-- CareerCopilot AI - Row Level Security Policies
-- Migration: 20250101000002
-- Description: Comprehensive RLS policies for all tables
-- =====================================================

-- Enable RLS on all tables
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
-- USER PROFILES
-- =====================================================

-- Users can read their own profile
CREATE POLICY "Users can read own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can insert their own profile
CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Service role bypasses RLS (automatic)

-- =====================================================
-- RESUMES
-- =====================================================

-- Users can read their own resumes
CREATE POLICY "Users can read own resumes"
    ON resumes FOR SELECT
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        AND deleted_at IS NULL
    );

-- Users can create resumes
CREATE POLICY "Users can create resumes"
    ON resumes FOR INSERT
    WITH CHECK (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- Users can update their own resumes
CREATE POLICY "Users can update own resumes"
    ON resumes FOR UPDATE
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    )
    WITH CHECK (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- Users can soft delete their own resumes
CREATE POLICY "Users can delete own resumes"
    ON resumes FOR DELETE
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- =====================================================
-- RESUME VERSIONS
-- =====================================================

-- Users can read their resume versions
CREATE POLICY "Users can read own resume versions"
    ON resume_versions FOR SELECT
    USING (
        resume_id IN (
            SELECT id FROM resumes 
            WHERE user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
            AND deleted_at IS NULL
        )
    );

-- Users can create resume versions
CREATE POLICY "Users can create resume versions"
    ON resume_versions FOR INSERT
    WITH CHECK (
        resume_id IN (
            SELECT id FROM resumes 
            WHERE user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        )
    );

-- Users can update their resume versions
CREATE POLICY "Users can update own resume versions"
    ON resume_versions FOR UPDATE
    USING (
        resume_id IN (
            SELECT id FROM resumes 
            WHERE user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        )
    );

-- =====================================================
-- RESUME SECTIONS
-- =====================================================

-- Users can read their resume sections
CREATE POLICY "Users can read own resume sections"
    ON resume_sections FOR SELECT
    USING (
        resume_version_id IN (
            SELECT rv.id FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
            AND r.deleted_at IS NULL
        )
    );

-- Users can create resume sections
CREATE POLICY "Users can create resume sections"
    ON resume_sections FOR INSERT
    WITH CHECK (
        resume_version_id IN (
            SELECT rv.id FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        )
    );

-- Users can update resume sections
CREATE POLICY "Users can update resume sections"
    ON resume_sections FOR UPDATE
    USING (
        resume_version_id IN (
            SELECT rv.id FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        )
    );

-- =====================================================
-- RESUME BULLETS
-- =====================================================

-- Users can read their resume bullets
CREATE POLICY "Users can read own resume bullets"
    ON resume_bullets FOR SELECT
    USING (
        section_id IN (
            SELECT rs.id FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
            AND r.deleted_at IS NULL
        )
    );

-- Users can create resume bullets
CREATE POLICY "Users can create resume bullets"
    ON resume_bullets FOR INSERT
    WITH CHECK (
        section_id IN (
            SELECT rs.id FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        )
    );

-- Users can update resume bullets
CREATE POLICY "Users can update resume bullets"
    ON resume_bullets FOR UPDATE
    USING (
        section_id IN (
            SELECT rs.id FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        )
    );

-- =====================================================
-- JOB DESCRIPTIONS
-- =====================================================

-- Users can read their own job descriptions
CREATE POLICY "Users can read own job descriptions"
    ON job_descriptions FOR SELECT
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        AND deleted_at IS NULL
    );

-- Users can create job descriptions
CREATE POLICY "Users can create job descriptions"
    ON job_descriptions FOR INSERT
    WITH CHECK (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- Users can update their job descriptions
CREATE POLICY "Users can update own job descriptions"
    ON job_descriptions FOR UPDATE
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- Users can delete their job descriptions
CREATE POLICY "Users can delete own job descriptions"
    ON job_descriptions FOR DELETE
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- =====================================================
-- JOB SKILL REQUIREMENTS
-- =====================================================

-- Users can read job skill requirements for their jobs
CREATE POLICY "Users can read job skill requirements"
    ON job_skill_requirements FOR SELECT
    USING (
        job_id IN (
            SELECT id FROM job_descriptions 
            WHERE user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
            AND deleted_at IS NULL
        )
    );

-- =====================================================
-- SKILLS (READ-ONLY FOR USERS)
-- =====================================================

-- All authenticated users can read skills taxonomy
CREATE POLICY "Users can read skills taxonomy"
    ON skills FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- =====================================================
-- RESUME SKILLS
-- =====================================================

-- Users can read their resume skills
CREATE POLICY "Users can read own resume skills"
    ON resume_skills FOR SELECT
    USING (
        resume_version_id IN (
            SELECT rv.id FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
            AND r.deleted_at IS NULL
        )
    );

-- =====================================================
-- SKILL GAPS
-- =====================================================

-- Users can read their own skill gaps
CREATE POLICY "Users can read own skill gaps"
    ON skill_gaps FOR SELECT
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- =====================================================
-- AI SYSTEM TABLES (READ-ONLY FOR USERS)
-- =====================================================

-- Users can read production prompts (for transparency)
CREATE POLICY "Users can read production prompts"
    ON ai_prompts FOR SELECT
    USING (
        auth.uid() IS NOT NULL 
        AND status = 'production'
    );

-- Users can read their own AI requests
CREATE POLICY "Users can read own ai requests"
    ON ai_requests FOR SELECT
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- Users can read responses to their requests
CREATE POLICY "Users can read own ai responses"
    ON ai_responses FOR SELECT
    USING (
        request_id IN (
            SELECT id FROM ai_requests 
            WHERE user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        )
    );

-- Users can read explanations for their data
CREATE POLICY "Users can read own explanations"
    ON explanations FOR SELECT
    USING (
        resume_version_id IN (
            SELECT rv.id FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE r.user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
            AND r.deleted_at IS NULL
        )
    );

-- AI evaluations and prompt candidates are admin-only (no user policies)

-- =====================================================
-- APPLICATIONS
-- =====================================================

-- Users can read their own applications
CREATE POLICY "Users can read own applications"
    ON applications FOR SELECT
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
        AND deleted_at IS NULL
    );

-- Users can create applications
CREATE POLICY "Users can create applications"
    ON applications FOR INSERT
    WITH CHECK (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- Users can update their applications
CREATE POLICY "Users can update own applications"
    ON applications FOR UPDATE
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- Users can delete their applications
CREATE POLICY "Users can delete own applications"
    ON applications FOR DELETE
    USING (
        user_id = (SELECT user_id FROM user_profiles WHERE auth.uid() = user_id LIMIT 1)
    );

-- =====================================================
-- ADMIN/SERVICE ROLE NOTES
-- =====================================================

-- Service role (using SUPABASE_SERVICE_ROLE_KEY) automatically bypasses RLS
-- This is needed for:
-- 1. AI Orchestrator writing to ai_requests, ai_responses
-- 2. Background jobs updating prompt statistics
-- 3. Auto-improvement pipeline evaluating prompts
-- 4. Admin operations

-- Example service role usage in FastAPI:
-- from supabase import create_client
-- supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
