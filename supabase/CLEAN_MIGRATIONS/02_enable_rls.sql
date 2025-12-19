-- =====================================================
-- JobPathAI - Step 2: Enable Row Level Security
-- Run this SECOND after 01_core_schema.sql
-- =====================================================

-- =====================================================
-- ENABLE RLS ON ALL TABLES
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
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE explanations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_candidates ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- USER PROFILES POLICIES
-- =====================================================

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

-- =====================================================
-- RESUMES POLICIES
-- =====================================================

CREATE POLICY "Users can read own resumes"
    ON resumes FOR SELECT
    USING (auth.uid() = user_id);

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

-- =====================================================
-- REQUIRED GRANTS (PostgREST needs table privileges too)
-- NOTE: RLS policies do NOT replace GRANTs. Without these,
-- you'll see 403 with PostgREST error=42501 (permission denied).
-- =====================================================

GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Supabase commonly installs extensions (uuid-ossp/pgcrypto) into `extensions`
GRANT USAGE ON SCHEMA extensions TO anon, authenticated;

-- Needed when tables use DEFAULT uuid_generate_v4().
-- In Supabase this function often lives in the `extensions` schema, not `public`.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE p.proname = 'uuid_generate_v4'
            AND n.nspname = 'extensions'
            AND p.pronargs = 0
    ) THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION extensions.uuid_generate_v4() TO anon, authenticated';
    ELSIF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE p.proname = 'uuid_generate_v4'
            AND n.nspname = 'public'
            AND p.pronargs = 0
    ) THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION public.uuid_generate_v4() TO anon, authenticated';
    END IF;

    -- Some projects use pgcrypto's gen_random_uuid() instead
    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE p.proname = 'gen_random_uuid'
            AND n.nspname = 'extensions'
            AND p.pronargs = 0
    ) THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION extensions.gen_random_uuid() TO anon, authenticated';
    ELSIF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE p.proname = 'gen_random_uuid'
            AND n.nspname = 'public'
            AND p.pronargs = 0
    ) THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION public.gen_random_uuid() TO anon, authenticated';
    END IF;
END $$;

-- Keep anon minimal; authenticated users get CRUD on app tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
-- Needed for foreign keys (e.g., resumes.user_id -> user_profiles.user_id)
GRANT REFERENCES ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Ensure future tables/sequences also work without manual grants
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT REFERENCES ON TABLES TO authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO authenticated;

-- =====================================================
-- RESUME VERSIONS POLICIES
-- =====================================================

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
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own resume versions"
    ON resume_versions FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM resumes 
            WHERE resumes.id = resume_versions.resume_id
            AND resumes.user_id = auth.uid()
        )
    );

-- =====================================================
-- RESUME SECTIONS POLICIES
-- =====================================================

CREATE POLICY "Users can manage own resume sections"
    ON resume_sections FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_sections.resume_version_id
            AND r.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_sections.resume_version_id
            AND r.user_id = auth.uid()
        )
    );

-- =====================================================
-- RESUME BULLETS POLICIES
-- =====================================================

CREATE POLICY "Users can manage own resume bullets"
    ON resume_bullets FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rs.id = resume_bullets.section_id
            AND r.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resume_sections rs
            JOIN resume_versions rv ON rs.resume_version_id = rv.id
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rs.id = resume_bullets.section_id
            AND r.user_id = auth.uid()
        )
    );

-- =====================================================
-- JOB DESCRIPTIONS POLICIES
-- =====================================================

CREATE POLICY "Users can read own job descriptions"
    ON job_descriptions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create job descriptions"
    ON job_descriptions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update job descriptions"
    ON job_descriptions FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete job descriptions"
    ON job_descriptions FOR DELETE
    USING (auth.uid() = user_id);

-- =====================================================
-- JOB SKILL REQUIREMENTS POLICIES
-- =====================================================

CREATE POLICY "Users can manage job skill requirements"
    ON job_skill_requirements FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM job_descriptions jd
            WHERE jd.id = job_skill_requirements.job_description_id
            AND jd.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM job_descriptions jd
            WHERE jd.id = job_skill_requirements.job_description_id
            AND jd.user_id = auth.uid()
        )
    );

-- =====================================================
-- SKILLS POLICIES
-- =====================================================

CREATE POLICY "Authenticated users can read skills"
    ON skills FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- Service role can manage skills
CREATE POLICY "Service role can manage skills"
    ON skills FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- =====================================================
-- RESUME SKILLS POLICIES
-- =====================================================

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

CREATE POLICY "Users can manage own resume skills"
    ON resume_skills FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_skills.resume_version_id
            AND r.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own resume skills"
    ON resume_skills FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM resume_versions rv
            JOIN resumes r ON rv.resume_id = r.id
            WHERE rv.id = resume_skills.resume_version_id
            AND r.user_id = auth.uid()
        )
    );

-- =====================================================
-- SKILL GAPS POLICIES
-- =====================================================

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
-- APPLICATIONS POLICIES
-- =====================================================

CREATE POLICY "Users can read own applications"
    ON applications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create applications"
    ON applications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update applications"
    ON applications FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete applications"
    ON applications FOR DELETE
    USING (auth.uid() = user_id);

-- =====================================================
-- AI PROMPTS POLICIES
-- =====================================================

CREATE POLICY "Anyone can read active prompts"
    ON ai_prompts FOR SELECT
    USING (is_active = true);

-- Service role can manage prompts
CREATE POLICY "Service role can manage prompts"
    ON ai_prompts FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- =====================================================
-- AI REQUESTS POLICIES
-- =====================================================

CREATE POLICY "Authenticated users can manage ai requests"
    ON ai_requests FOR ALL
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

-- =====================================================
-- AI RESPONSES POLICIES
-- =====================================================

CREATE POLICY "Authenticated users can read ai responses"
    ON ai_responses FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- Service role can insert responses
CREATE POLICY "Service role can insert ai responses"
    ON ai_responses FOR INSERT
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- =====================================================
-- EXPLANATIONS POLICIES
-- =====================================================

CREATE POLICY "Authenticated users can read explanations"
    ON explanations FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- Service role can manage explanations
CREATE POLICY "Service role can manage explanations"
    ON explanations FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- =====================================================
-- AI EVALUATIONS & PROMPT CANDIDATES
-- (Service role only - internal use)
-- =====================================================

CREATE POLICY "Service role manages ai evaluations"
    ON ai_evaluations FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

CREATE POLICY "Service role manages prompt candidates"
    ON prompt_candidates FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- =====================================================
-- ✅ Step 2 Complete: RLS Policies Enabled
-- Next: Run 03_storage_setup.sql (optional)
-- =====================================================
