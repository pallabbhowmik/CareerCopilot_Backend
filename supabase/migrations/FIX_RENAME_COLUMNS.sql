-- =====================================================
-- Rename template columns to match model expectations
-- =====================================================

-- Rename config to config_json (only if config exists and config_json doesn't)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'templates' AND column_name = 'config'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'templates' AND column_name = 'config_json'
    ) THEN
        ALTER TABLE templates RENAME COLUMN config TO config_json;
    END IF;
END $$;

-- Rename preview_image to preview_image_url (only if preview_image exists and preview_image_url doesn't)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'templates' AND column_name = 'preview_image'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'templates' AND column_name = 'preview_image_url'
    ) THEN
        ALTER TABLE templates RENAME COLUMN preview_image TO preview_image_url;
    END IF;
END $$;

-- Add slug if missing
ALTER TABLE templates ADD COLUMN IF NOT EXISTS slug VARCHAR(255);

-- Add preview_url if missing
ALTER TABLE templates ADD COLUMN IF NOT EXISTS preview_url VARCHAR(500);

-- Add is_ats_safe if missing  
ALTER TABLE templates ADD COLUMN IF NOT EXISTS is_ats_safe BOOLEAN DEFAULT TRUE;

-- Add is_active if missing
ALTER TABLE templates ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Add recommended_for if missing
ALTER TABLE templates ADD COLUMN IF NOT EXISTS recommended_for JSONB DEFAULT '[]'::jsonb;

-- Add popularity_score if missing
ALTER TABLE templates ADD COLUMN IF NOT EXISTS popularity_score INTEGER DEFAULT 0;

-- Add updated_at to applications if missing
ALTER TABLE applications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
