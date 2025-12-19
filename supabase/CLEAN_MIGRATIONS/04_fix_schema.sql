-- =====================================================
-- JobPathAI - Step 4: Fix Schema & Auto-create Profiles
-- Run this FOURTH to fix remaining issues
-- =====================================================

-- =====================================================
-- Add missing columns to resumes table (frontend expects these)
-- =====================================================

ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_path TEXT;
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_size BIGINT;
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_type TEXT;
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS original_filename TEXT;

-- Resume parsing lifecycle (frontend sends parsing_status)
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS parsing_status TEXT DEFAULT 'pending';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'resumes_parsing_status_check'
  ) THEN
    ALTER TABLE resumes
      ADD CONSTRAINT resumes_parsing_status_check
      CHECK (parsing_status IN ('pending', 'processing', 'completed', 'failed'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_resumes_parsing_status ON resumes(parsing_status);

-- =====================================================
-- Create function to auto-create user profile on signup
-- =====================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (user_id, email, full_name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email)
  )
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Trigger: Auto-create profile when user signs up
-- =====================================================

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- Create missing profiles for existing users
-- =====================================================

INSERT INTO public.user_profiles (user_id, email, full_name)
SELECT 
  id,
  email,
  COALESCE(raw_user_meta_data->>'full_name', email)
FROM auth.users
WHERE id NOT IN (SELECT user_id FROM public.user_profiles)
ON CONFLICT (user_id) DO NOTHING;

-- =====================================================
-- Verify: Check your user profile exists
-- =====================================================

-- Run this query to see if your profile was created:
-- SELECT * FROM user_profiles WHERE user_id = auth.uid();

-- If you see your profile, you're good!
-- If empty, manually create it:
-- INSERT INTO user_profiles (user_id, email, full_name)
-- VALUES (auth.uid(), auth.email(), 'Your Name');

-- =====================================================
-- ✅ Step 4 Complete: Schema Fixed & Profiles Created
-- Now test your app - 403 errors should be gone!
-- =====================================================
