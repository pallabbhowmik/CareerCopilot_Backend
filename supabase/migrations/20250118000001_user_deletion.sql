-- =====================================================
-- USER DELETION RPC FUNCTION
-- Allows users to delete their own account
-- =====================================================

-- This function must be created as it's called from the settings page
-- It safely deletes the user's auth account which cascades to all related data

CREATE OR REPLACE FUNCTION delete_user()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Delete the authenticated user
  -- Cascading foreign keys will handle related data in:
  -- - user_profiles
  -- - resumes  
  -- - applications
  DELETE FROM auth.users WHERE id = auth.uid();
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION delete_user() TO authenticated;

-- =====================================================
-- VERIFICATION
-- =====================================================

SELECT 'delete_user function created successfully!' as status;
