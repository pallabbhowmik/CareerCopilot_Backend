-- =====================================================
-- RESET DATABASE - Clean Slate for Fresh Migration
-- ⚠️ WARNING: This will DELETE ALL DATA
-- =====================================================

-- Drop all tables in public schema (CASCADE removes dependent objects)
DROP SCHEMA IF EXISTS public CASCADE;

-- Recreate public schema
CREATE SCHEMA public;

-- Grant permissions
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- Re-enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Verify clean slate
SELECT COUNT(*) as remaining_tables 
FROM information_schema.tables 
WHERE table_schema = 'public';
-- Should return 0

-- =====================================================
-- Ready for migrations!
-- Now run in order:
-- 1. 20250101000000_initial_schema.sql
-- 2. 20250101000001_ai_platform.sql
-- 3. 20250101000002_rls_policies.sql
-- 4. 20250101000003_views_rpcs.sql
-- 5. 20250101000004_seed_prompts.sql
-- 6. 20250101000005_additional_prompts.sql
-- =====================================================
