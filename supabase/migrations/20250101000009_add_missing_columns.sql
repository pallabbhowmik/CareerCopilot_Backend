-- =====================================================
-- Add missing columns to match SQLAlchemy models
-- Fix schema mismatches causing 500 errors
-- =====================================================

-- Add slug column to templates table
ALTER TABLE templates 
ADD COLUMN IF NOT EXISTS slug VARCHAR(255);

-- Add updated_at column to applications table
ALTER TABLE applications 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Add missing Template model columns
ALTER TABLE templates
ADD COLUMN IF NOT EXISTS config_json JSONB,
ADD COLUMN IF NOT EXISTS preview_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS preview_image_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS is_ats_safe BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS recommended_for JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS popularity_score INTEGER DEFAULT 0;

-- Rename config to config_json if it exists (for consistency)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'templates' 
        AND column_name = 'config'
    ) THEN
        ALTER TABLE templates RENAME COLUMN config TO config_json;
    END IF;
END $$;

-- Rename preview_image to preview_image_url if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'templates' 
        AND column_name = 'preview_image'
    ) THEN
        ALTER TABLE templates RENAME COLUMN preview_image TO preview_image_url;
    END IF;
END $$;

-- Add missing JobDescription columns
ALTER TABLE job_descriptions
ADD COLUMN IF NOT EXISTS content_raw TEXT,
ADD COLUMN IF NOT EXISTS requirements_structured JSONB;

-- Rename description to content_raw if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'job_descriptions' 
        AND column_name = 'description'
    ) THEN
        ALTER TABLE job_descriptions RENAME COLUMN description TO content_raw;
    END IF;
END $$;

-- Add missing Analysis columns
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS score_data JSONB,
ADD COLUMN IF NOT EXISTS gap_analysis JSONB,
ADD COLUMN IF NOT EXISTS recommendations JSONB,
ADD COLUMN IF NOT EXISTS job_description_id INTEGER REFERENCES job_descriptions(id);

-- Rename result to score_data if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'analyses' 
        AND column_name = 'result'
    ) THEN
        ALTER TABLE analyses RENAME COLUMN result TO score_data;
    END IF;
END $$;

-- Rename job_id to job_description_id if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'analyses' 
        AND column_name = 'job_id'
    ) THEN
        ALTER TABLE analyses RENAME COLUMN job_id TO job_description_id;
    END IF;
END $$;

-- Create unique constraint on templates.name if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'templates_name_key'
    ) THEN
        ALTER TABLE templates ADD CONSTRAINT templates_name_key UNIQUE (name);
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_templates_slug ON templates(slug);
CREATE INDEX IF NOT EXISTS idx_resumes_variant_group ON resumes(variant_group_id);
