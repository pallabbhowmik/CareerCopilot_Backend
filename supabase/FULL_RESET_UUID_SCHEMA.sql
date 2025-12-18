-- =====================================================
-- FULL DATABASE RESET - UUID-Based Schema
-- WARNING: This will DELETE ALL DATA
-- Use only for clean production setup
-- =====================================================

-- Step 1: Disable RLS temporarily to avoid permission errors
ALTER TABLE IF EXISTS user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS resumes DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS applications DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS templates DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS skills DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ai_analysis_cache DISABLE ROW LEVEL SECURITY;

-- Step 2: Drop all triggers
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
DROP TRIGGER IF EXISTS update_resumes_updated_at ON resumes;
DROP TRIGGER IF EXISTS update_applications_updated_at ON applications;

-- Step 3: Drop all tables in dependency order
DROP TABLE IF EXISTS ai_analysis_cache CASCADE;
DROP TABLE IF EXISTS analyses CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS skill_gaps CASCADE;
DROP TABLE IF EXISTS resume_skills CASCADE;
DROP TABLE IF EXISTS job_skill_requirements CASCADE;
DROP TABLE IF EXISTS resume_bullets CASCADE;
DROP TABLE IF EXISTS resume_sections CASCADE;
DROP TABLE IF EXISTS resume_versions CASCADE;
DROP TABLE IF EXISTS resumes CASCADE;
DROP TABLE IF EXISTS job_descriptions CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS templates CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE; -- Old INTEGER-based table

-- Step 4: Drop functions
DROP FUNCTION IF EXISTS handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Step 5: Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =====================================================
-- USER PROFILES (UUID-Based)
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
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_email ON user_profiles(email);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  BEGIN
    INSERT INTO public.user_profiles (user_id, email, full_name, onboarding_completed)
    VALUES (
      NEW.id,
      NEW.email,
      COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
      FALSE
    );
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Failed to create user profile: %', SQLERRM;
  END;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- =====================================================
-- RESUMES (UUID-Based)
-- =====================================================

CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    original_filename TEXT,
    file_path TEXT,
    file_size INTEGER,
    
    content_raw TEXT,
    content_structured JSONB,
    
    parsing_status TEXT DEFAULT 'pending' CHECK (parsing_status IN ('pending', 'processing', 'completed', 'failed')),
    ats_score INTEGER CHECK (ats_score >= 0 AND ats_score <= 100),
    strength_score INTEGER CHECK (strength_score >= 0 AND strength_score <= 100),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_resumes_created_at ON resumes(created_at DESC);
CREATE INDEX idx_resumes_parsing_status ON resumes(parsing_status);

-- =====================================================
-- APPLICATIONS (UUID-Based)
-- =====================================================

CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_url TEXT,
    location TEXT,
    salary_range TEXT,
    
    status TEXT DEFAULT 'applied' CHECK (status IN (
        'wishlist', 'applied', 'screening', 'interview', 
        'offer', 'rejected', 'accepted', 'declined', 'withdrawn'
    )),
    application_date DATE,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_date ON applications(application_date DESC);

-- =====================================================
-- TEMPLATES (UUID-Based)
-- =====================================================

CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK (category IN ('modern', 'classic', 'creative', 'technical', 'executive')),
    description TEXT,
    preview_image_url TEXT,
    template_data JSONB NOT NULL,
    
    usage_count INTEGER DEFAULT 0,
    rating NUMERIC(3,2) CHECK (rating >= 0 AND rating <= 5),
    
    is_premium BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON templates(category) WHERE is_active = TRUE;
CREATE INDEX idx_templates_usage ON templates(usage_count DESC) WHERE is_active = TRUE;

-- =====================================================
-- SKILLS (UUID-Based)
-- =====================================================

CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_name TEXT NOT NULL UNIQUE,
    skill_category TEXT CHECK (skill_category IN ('technical', 'soft', 'domain', 'tool', 'framework', 'language')),
    aliases TEXT[],
    popularity_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skills_name ON skills(skill_name);
CREATE INDEX idx_skills_category ON skills(skill_category);

-- =====================================================
-- AI CACHE (UUID-Based)
-- =====================================================

CREATE TABLE ai_analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL UNIQUE,
    analysis_type TEXT NOT NULL CHECK (analysis_type IN ('resume_parse', 'ats_score', 'job_match', 'improvement')),
    input_data JSONB NOT NULL,
    output_data JSONB NOT NULL,
    
    hit_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_cache_hash ON ai_analysis_cache(content_hash);
CREATE INDEX idx_ai_cache_expires ON ai_analysis_cache(expires_at);

-- =====================================================
-- ROW LEVEL SECURITY
-- =====================================================

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = user_id);

ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own resumes" ON resumes FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own resumes" ON resumes FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own resumes" ON resumes FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own resumes" ON resumes FOR DELETE USING (auth.uid() = user_id);

ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own applications" ON applications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own applications" ON applications FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own applications" ON applications FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own applications" ON applications FOR DELETE USING (auth.uid() = user_id);

ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can view active templates" ON templates FOR SELECT USING (is_active = TRUE);

ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can view skills" ON skills FOR SELECT USING (true);

-- =====================================================
-- TRIGGERS
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SEED DATA
-- =====================================================

INSERT INTO templates (name, category, description, template_data, is_active) VALUES
('Modern Professional', 'modern', 'Clean and modern design perfect for tech roles', '{"layout": "single-column", "colors": {"primary": "#2563eb"}}', true),
('Classic Executive', 'classic', 'Traditional format for senior positions', '{"layout": "two-column", "colors": {"primary": "#1f2937"}}', true),
('Creative Designer', 'creative', 'Bold and colorful for creative industries', '{"layout": "grid", "colors": {"primary": "#ec4899"}}', true)
ON CONFLICT (name) DO NOTHING;

INSERT INTO skills (skill_name, skill_category, aliases) VALUES
('JavaScript', 'technical', ARRAY['JS', 'ECMAScript']),
('Python', 'technical', ARRAY['Python3']),
('React', 'framework', ARRAY['ReactJS', 'React.js']),
('Node.js', 'framework', ARRAY['NodeJS', 'Node']),
('Communication', 'soft', ARRAY['Verbal Communication', 'Written Communication']),
('Leadership', 'soft', ARRAY['Team Leadership', 'People Management'])
ON CONFLICT (skill_name) DO NOTHING;

-- =====================================================
-- VERIFICATION
-- =====================================================

SELECT 'UUID Schema created successfully!' as status;
SELECT 
    schemaname, 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
