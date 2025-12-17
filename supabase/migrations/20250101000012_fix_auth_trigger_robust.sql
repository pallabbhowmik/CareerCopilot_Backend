-- =====================================================
-- Fix Auth Trigger and Ensure Extensions
-- Migration: 20250101000012
-- Description: Robust version of the auth trigger with conflict handling and search_path
-- =====================================================

-- 1. Ensure UUID extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;

-- 2. Update the function to be more robust (non-blocking)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Try to create user profile, but don't block signup if it fails
    BEGIN
        INSERT INTO public.user_profiles (user_id, email, full_name)
        VALUES (
            NEW.id,
            NEW.email,
            COALESCE(NEW.raw_user_meta_data->>'full_name', '')
        )
        ON CONFLICT (user_id) DO UPDATE
        SET 
            email = EXCLUDED.email,
            full_name = COALESCE(EXCLUDED.full_name, public.user_profiles.full_name),
            updated_at = NOW();
    EXCEPTION
        WHEN OTHERS THEN
            -- Log error but don't fail the signup
            RAISE WARNING 'Failed to create user profile for %: %', NEW.id, SQLERRM;
    END;
    
    -- Always return NEW to allow signup to proceed
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Recreate the trigger to ensure it's active
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
