-- =====================================================
-- CareerCopilot AI - Production Schema for 100K+ Users
-- Optimized for scale with Supabase
-- =====================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- =====================================================
-- 1. USER PROFILES (Auth Integration)
-- =====================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    target_role TEXT,
    experience_level TEXT CHECK (experience_level IN ('entry', 'mid', 'senior', 'lead', 'executive')),
    country TEXT,
    career_goal TEXT,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);

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

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- =====================================================
-- 2. RESUMES (File Storage + Metadata)
-- =====================================================

CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    original_filename TEXT,
    file_path TEXT, -- Supabase Storage path
    file_size INTEGER,
    
    -- Parsed content
    content_raw TEXT,
    content_structured JSONB,
    
    -- Analysis results
    parsing_status TEXT DEFAULT 'pending',
    ats_score INTEGER,
    strength_score INTEGER,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add columns if they don't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='resumes' AND column_name='parsing_status') THEN
        ALTER TABLE resumes ADD COLUMN parsing_status TEXT DEFAULT 'pending';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='resumes' AND column_name='ats_score') THEN
        ALTER TABLE resumes ADD COLUMN ats_score INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='resumes' AND column_name='strength_score') THEN
        ALTER TABLE resumes ADD COLUMN strength_score INTEGER;
    END IF;
END $$;

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'resumes_parsing_status_check') THEN
        ALTER TABLE resumes ADD CONSTRAINT resumes_parsing_status_check CHECK (parsing_status IN ('pending', 'processing', 'completed', 'failed'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'resumes_ats_score_check') THEN
        ALTER TABLE resumes ADD CONSTRAINT resumes_ats_score_check CHECK (ats_score >= 0 AND ats_score <= 100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'resumes_strength_score_check') THEN
        ALTER TABLE resumes ADD CONSTRAINT resumes_strength_score_check CHECK (strength_score >= 0 AND strength_score <= 100);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_created_at ON resumes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_resumes_parsing_status ON resumes(parsing_status);

-- =====================================================
-- 3. JOB APPLICATIONS (Tracking)
-- =====================================================

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    
    -- Job details
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_url TEXT,
    location TEXT,
    salary_range TEXT,
    
    -- Application status
    status TEXT DEFAULT 'applied',
    application_date DATE,
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add columns if they don't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='applications' AND column_name='application_date') THEN
        ALTER TABLE applications ADD COLUMN application_date DATE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='applications' AND column_name='salary_range') THEN
        ALTER TABLE applications ADD COLUMN salary_range TEXT;
    END IF;
END $$;

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'applications_status_check') THEN
        ALTER TABLE applications ADD CONSTRAINT applications_status_check CHECK (status IN (
            'wishlist', 'applied', 'screening', 'interview', 
            'offer', 'rejected', 'accepted', 'declined', 'withdrawn'
        ));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_date ON applications(application_date DESC);

-- =====================================================
-- 4. RESUME TEMPLATES
-- =====================================================

CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    description TEXT,
    preview_image_url TEXT,
    template_data JSONB NOT NULL,
    
    -- Metrics
    usage_count INTEGER DEFAULT 0,
    rating NUMERIC(3,2),
    
    -- Metadata
    is_premium BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add columns if they don't exist (for existing tables)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='usage_count') THEN
        ALTER TABLE templates ADD COLUMN usage_count INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='rating') THEN
        ALTER TABLE templates ADD COLUMN rating NUMERIC(3,2);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='is_premium') THEN
        ALTER TABLE templates ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'templates_category_check') THEN
        ALTER TABLE templates ADD CONSTRAINT templates_category_check CHECK (category IN ('modern', 'classic', 'creative', 'technical', 'executive'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'templates_rating_check') THEN
        ALTER TABLE templates ADD CONSTRAINT templates_rating_check CHECK (rating >= 0 AND rating <= 5);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_templates_usage ON templates(usage_count DESC) WHERE is_active = TRUE;

-- =====================================================
-- 5. SKILLS TAXONOMY (For matching & intelligence)
-- =====================================================

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_name TEXT NOT NULL UNIQUE,
    skill_category TEXT CHECK (skill_category IN ('technical', 'soft', 'domain', 'tool', 'framework', 'language')),
    aliases TEXT[],
    
    -- Trend data
    popularity_score FLOAT DEFAULT 0.0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(skill_category);

-- =====================================================
-- 6. AI ANALYSIS CACHE (For performance)
-- =====================================================

CREATE TABLE IF NOT EXISTS ai_analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash TEXT NOT NULL UNIQUE,
    analysis_type TEXT NOT NULL CHECK (analysis_type IN ('resume_parse', 'ats_score', 'job_match', 'improvement')),
    input_data JSONB NOT NULL,
    output_data JSONB NOT NULL,
    
    -- Cache management
    hit_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_cache_hash ON ai_analysis_cache(content_hash);
CREATE INDEX IF NOT EXISTS idx_ai_cache_expires ON ai_analysis_cache(expires_at);

-- =====================================================
-- ROW LEVEL SECURITY (Critical for 100K+ users)
-- =====================================================

-- User Profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = user_id);

-- Resumes
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can insert own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can update own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can delete own resumes" ON resumes;
CREATE POLICY "Users can view own resumes" ON resumes FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own resumes" ON resumes FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own resumes" ON resumes FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own resumes" ON resumes FOR DELETE USING (auth.uid() = user_id);

-- Applications
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own applications" ON applications;
DROP POLICY IF EXISTS "Users can insert own applications" ON applications;
DROP POLICY IF EXISTS "Users can update own applications" ON applications;
DROP POLICY IF EXISTS "Users can delete own applications" ON applications;
CREATE POLICY "Users can view own applications" ON applications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own applications" ON applications FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own applications" ON applications FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own applications" ON applications FOR DELETE USING (auth.uid() = user_id);

-- Templates (Public read, admin write)
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view active templates" ON templates;
CREATE POLICY "Anyone can view active templates" ON templates FOR SELECT USING (is_active = TRUE);

-- Skills (Public read)
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view skills" ON skills;
CREATE POLICY "Anyone can view skills" ON skills FOR SELECT USING (true);

-- =====================================================
-- PERFORMANCE OPTIMIZATIONS
-- =====================================================

-- Automatic updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_resumes_updated_at ON resumes;
CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_applications_updated_at ON applications;
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SEED DATA (Templates & Skills)
-- =====================================================

-- Insert default templates
INSERT INTO templates (name, category, description, template_data, is_active) VALUES
('Modern Professional', 'modern', 'Clean and modern design perfect for tech roles', '{"layout": "single-column", "colors": {"primary": "#2563eb"}}', true),
('Classic Executive', 'classic', 'Traditional format for senior positions', '{"layout": "two-column", "colors": {"primary": "#1f2937"}}', true),
('Creative Designer', 'creative', 'Bold and colorful for creative industries', '{"layout": "grid", "colors": {"primary": "#ec4899"}}', true)
ON CONFLICT (name) DO NOTHING;

-- Insert common skills
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

SELECT 'Schema created successfully!' as status;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
