-- =====================================================
-- JobPathAI - Fixed Row Level Security Policies
-- Migration: 20250119000000
-- Description: Simplified RLS policies to fix 403 errors
-- =====================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can read own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;

DROP POLICY IF EXISTS "Users can read own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can create resumes" ON resumes;
DROP POLICY IF EXISTS "Users can update own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can delete own resumes" ON resumes;

DROP POLICY IF EXISTS "Users can read own resume versions" ON resume_versions;
DROP POLICY IF EXISTS "Users can create resume versions" ON resume_versions;
DROP POLICY IF EXISTS "Users can update own resume versions" ON resume_versions;

DROP POLICY IF EXISTS "Users can read own resume sections" ON resume_sections;
DROP POLICY IF EXISTS "Users can create resume sections" ON resume_sections;
DROP POLICY IF EXISTS "Users can update resume sections" ON resume_sections;

DROP POLICY IF EXISTS "Users can read own resume bullets" ON resume_bullets;
DROP POLICY IF EXISTS "Users can create resume bullets" ON resume_bullets;
DROP POLICY IF EXISTS "Users can update resume bullets" ON resume_bullets;

DROP POLICY IF EXISTS "Users can read own job descriptions" ON job_descriptions;
DROP POLICY IF EXISTS "Users can create job descriptions" ON job_descriptions;
DROP POLICY IF EXISTS "Users can update job descriptions" ON job_descriptions;
DROP POLICY IF EXISTS "Users can delete job descriptions" ON job_descriptions;

DROP POLICY IF EXISTS "Users can read own skills" ON skills;
DROP POLICY IF EXISTS "Users can read own resume skills" ON resume_skills;
DROP POLICY IF EXISTS "Users can read own skill gaps" ON skill_gaps;
DROP POLICY IF EXISTS "Users can read own applications" ON applications;

-- =====================================================
-- USER PROFILES - Simplified
-- =====================================================

-- Users can read their own profile (direct auth.uid() comparison)
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

-- =====================================================
-- RESUMES - Simplified (direct user_id comparison)
-- =====================================================

-- Users can read their own resumes
CREATE POLICY "Users can read own resumes"
    ON resumes FOR SELECT
    USING (auth.uid() = user_id AND deleted_at IS NULL);

-- Users can create resumes
CREATE POLICY "Users can create resumes"
    ON resumes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own resumes
CREATE POLICY "Users can update own resumes"
    ON resumes FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own resumes
CREATE POLICY "Users can delete own resumes"
    ON resumes FOR DELETE
    USING (auth.uid() = user_id);

-- =====================================================
-- RESUME VERSIONS
-- =====================================================

-- Users can read their resume versions
CREATE POLICY "Users can read own resume versions"
    ON resume_versions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
            AND resumes.deleted_at IS NULL
        )
    );

-- Users can create resume versions
CREATE POLICY "Users can create resume versions"
    ON resume_versions FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
        )
    );

-- Users can update their resume versions
CREATE POLICY "Users can update own resume versions"
    ON resume_versions FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
        )
    );

-- =====================================================
-- RESUME SECTIONS
-- =====================================================

-- Users can read their resume sections
CREATE POLICY "Users can read own resume sections"
    ON resume_sections FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_sections.resume_version_id
            AND r.user_id = auth.uid()
            AND r.deleted_at IS NULL
        )
    );

-- Users can create resume sections
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

-- Users can update resume sections
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

-- =====================================================
-- RESUME BULLETS
-- =====================================================

-- Users can read their resume bullets
CREATE POLICY "Users can read own resume bullets"
    ON resume_bullets FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rs.id = resume_bullets.section_id
            AND r.user_id = auth.uid()
            AND r.deleted_at IS NULL
        )
    );

-- Users can create resume bullets
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

-- Users can update resume bullets
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

-- =====================================================
-- JOB DESCRIPTIONS
-- =====================================================

-- Users can read their own job descriptions
CREATE POLICY "Users can read own job descriptions"
    ON job_descriptions FOR SELECT
    USING (auth.uid() = user_id AND deleted_at IS NULL);

-- Users can create job descriptions
CREATE POLICY "Users can create job descriptions"
    ON job_descriptions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own job descriptions
CREATE POLICY "Users can update job descriptions"
    ON job_descriptions FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own job descriptions
CREATE POLICY "Users can delete job descriptions"
    ON job_descriptions FOR DELETE
    USING (auth.uid() = user_id);

-- =====================================================
-- SKILLS & SKILL GAPS (READ-ONLY for users)
-- =====================================================

-- Users can read skills associated with their resumes
CREATE POLICY "Users can read own skills"
    ON skills FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM resume_skills rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rs.skill_id = skills.id
            AND r.user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM skill_gaps sg
            JOIN job_descriptions jd ON sg.job_description_id = jd.id
            WHERE sg.skill_id = skills.id
            AND jd.user_id = auth.uid()
        )
    );

-- Users can read resume skills for their resumes
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

-- Users can read skill gaps for their job descriptions
CREATE POLICY "Users can read own skill gaps"
    ON skill_gaps FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM job_descriptions jd
            WHERE jd.id = skill_gaps.job_description_id
            AND jd.user_id = auth.uid()
        )
    );

-- =====================================================
-- APPLICATIONS
-- =====================================================

-- Users can read their own applications
CREATE POLICY "Users can read own applications"
    ON applications FOR SELECT
    USING (auth.uid() = user_id AND deleted_at IS NULL);

-- Users can create applications
CREATE POLICY "Users can create applications"
    ON applications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their applications
CREATE POLICY "Users can update applications"
    ON applications FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their applications
CREATE POLICY "Users can delete applications"
    ON applications FOR DELETE
    USING (auth.uid() = user_id);

-- =====================================================
-- AI PLATFORM TABLES (Permissive for development)
-- =====================================================

-- AI Prompts: Anyone can read system prompts
CREATE POLICY "Anyone can read ai prompts"
    ON ai_prompts FOR SELECT
    USING (true);

-- AI Requests: Users can read/write their own
CREATE POLICY "Users can manage own ai requests"
    ON ai_requests FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles up
            WHERE up.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_profiles up
            WHERE up.user_id = auth.uid()
        )
    );

-- AI Responses: Users can read/write their own
CREATE POLICY "Users can manage own ai responses"
    ON ai_responses FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles up
            WHERE up.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_profiles up
            WHERE up.user_id = auth.uid()
        )
    );

-- Explanations: Users can read explanations for their content
CREATE POLICY "Users can read own explanations"
    ON explanations FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles up
            WHERE up.user_id = auth.uid()
        )
    );

-- AI Evaluations: Service role only (internal use)
-- No user policies needed

-- Prompt Candidates: Service role only (internal use)
-- No user policies needed
