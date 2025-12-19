-- =====================================================
-- JobPathAI - DIAGNOSTIC & FIX
-- Run this to diagnose and fix RLS issues
-- =====================================================

-- =====================================================
-- STEP 1: Check if RLS is enabled
-- =====================================================

SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE schemaname = 'public'
AND tablename IN (
    'user_profiles',
    'resumes',
    'resume_versions',
    'resume_sections',
    'resume_bullets'
)
ORDER BY tablename;

-- Should show rls_enabled = true for both tables

-- =====================================================
-- STEP 2: Check if policies exist
-- =====================================================

SELECT 
    schemaname,
    tablename,
    policyname,
    cmd
FROM pg_policies 
WHERE schemaname = 'public'
AND tablename IN (
    'user_profiles',
    'resumes',
    'resume_versions',
    'resume_sections',
    'resume_bullets'
)
ORDER BY tablename, policyname;

-- Should show multiple policies for each table

-- =====================================================
-- STEP 3: Check if user profile exists
-- =====================================================

-- Check as service role (bypass RLS)
SELECT * FROM user_profiles WHERE user_id = 'ec111de9-27ef-4a49-8671-c433de5424e0';

-- =====================================================
-- STEP 4: Fix - Temporarily disable RLS to create profile
-- =====================================================

-- Disable RLS temporarily
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;

-- Create the profile
INSERT INTO user_profiles (user_id, email, full_name)
VALUES ('ec111de9-27ef-4a49-8671-c433de5424e0'::uuid, 'pallab424@gmail.com', 'Pallab')
ON CONFLICT (user_id) DO UPDATE SET email = EXCLUDED.email, full_name = EXCLUDED.full_name;

-- Re-enable RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- STEP 5: Verify the fix
-- =====================================================

-- NOTE: In the Supabase SQL editor, auth.uid() is typically NULL because
-- there's no JWT context. To verify RLS behavior, test via your app/API.
-- If your app still gets 403 with PostgREST error=42501, you are missing GRANTs.

-- Check table privileges for the authenticated role
SELECT
    table_schema,
    table_name,
    privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'authenticated'
    AND table_schema = 'public'
    AND table_name IN (
        'user_profiles',
        'resumes',
        'resume_versions',
        'resume_sections',
        'resume_bullets'
    )
ORDER BY table_name, privilege_type;

-- Fix missing GRANTs (safe + required for PostgREST)
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.resumes TO authenticated;

-- Resume editor tables
GRANT SELECT, INSERT, UPDATE, DELETE ON public.resume_versions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.resume_sections TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.resume_bullets TO authenticated;

-- Helpful for identity/sequence-backed columns (safe even if you don't use sequences)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Ensure future tables also work without manual grants
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO authenticated;

-- =====================================================
-- STEP 6: If policies are missing, recreate them
-- =====================================================

-- Drop and recreate user_profiles policies
DROP POLICY IF EXISTS "Users can read own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;

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

-- Drop and recreate resumes policies
DROP POLICY IF EXISTS "Users can read own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can create resumes" ON resumes;
DROP POLICY IF EXISTS "Users can update own resumes" ON resumes;
DROP POLICY IF EXISTS "Users can delete own resumes" ON resumes;

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
-- ✅ DIAGNOSTIC COMPLETE
-- Now refresh your app and test!
-- =====================================================
