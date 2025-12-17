-- =====================================================
-- Add missing columns (safe version - checks if exists)
-- =====================================================

-- Add missing columns to templates table (only if they don't exist)
DO $$
BEGIN
    -- Add slug
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='slug') THEN
        ALTER TABLE templates ADD COLUMN slug VARCHAR(255);
    END IF;
    
    -- Add preview_url
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='preview_url') THEN
        ALTER TABLE templates ADD COLUMN preview_url VARCHAR(500);
    END IF;
    
    -- Add preview_image_url
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='preview_image_url') THEN
        ALTER TABLE templates ADD COLUMN preview_image_url VARCHAR(500);
    END IF;
    
    -- Add is_ats_safe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='is_ats_safe') THEN
        ALTER TABLE templates ADD COLUMN is_ats_safe BOOLEAN DEFAULT TRUE;
    END IF;
    
    -- Add is_active
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='is_active') THEN
        ALTER TABLE templates ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;
    
    -- Add recommended_for
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='recommended_for') THEN
        ALTER TABLE templates ADD COLUMN recommended_for JSONB DEFAULT '[]'::jsonb;
    END IF;
    
    -- Add popularity_score
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='templates' AND column_name='popularity_score') THEN
        ALTER TABLE templates ADD COLUMN popularity_score INTEGER DEFAULT 0;
    END IF;
END $$;

-- Add updated_at to applications table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='applications' AND column_name='updated_at') THEN
        ALTER TABLE applications ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_templates_slug ON templates(slug);
CREATE INDEX IF NOT EXISTS idx_resumes_variant_group ON resumes(variant_group_id);
