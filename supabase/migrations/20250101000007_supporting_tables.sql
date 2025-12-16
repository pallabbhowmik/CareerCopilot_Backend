-- =====================================================
-- Additional tables needed by FastAPI models
-- These support the resume, analysis, and template features
-- =====================================================

-- Templates table
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    config JSONB,
    preview_image VARCHAR(500),
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Resumes table  
CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES templates(id),
    title VARCHAR(255),
    content_raw TEXT,
    content_structured JSONB,
    style_config JSONB,
    heatmap_data JSONB,
    bullet_feedback JSONB,
    strength_score INTEGER,
    ats_score INTEGER,
    variant_group_id INTEGER,
    version INTEGER DEFAULT 1,
    parent_resume_id INTEGER REFERENCES resumes(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job descriptions table
CREATE TABLE IF NOT EXISTS job_descriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    company VARCHAR(255),
    url TEXT,
    description TEXT,
    required_skills JSONB,
    preferred_skills JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analysis table
CREATE TABLE IF NOT EXISTS analysis (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    resume_id INTEGER REFERENCES resumes(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES job_descriptions(id),
    analysis_type VARCHAR(50),
    result JSONB,
    score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Applications table
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    resume_id INTEGER REFERENCES resumes(id),
    company VARCHAR(255),
    job_title VARCHAR(255),
    job_url TEXT,
    status VARCHAR(50) DEFAULT 'applied',
    notes TEXT,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    response_received BOOLEAN DEFAULT FALSE,
    interview_scheduled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_job_descriptions_user_id ON job_descriptions(user_id);
CREATE INDEX idx_analysis_user_id ON analysis(user_id);
CREATE INDEX idx_applications_user_id ON applications(user_id);
