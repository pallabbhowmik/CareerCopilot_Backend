-- Add missing file_path column to resumes table
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);
