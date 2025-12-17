-- =====================================================
-- COMPLETE DATABASE RESET for FastAPI Auth
-- Run this to drop ALL tables and start fresh
-- =====================================================

-- Drop ALL tables including AI platform ones
DROP TABLE IF EXISTS prompt_candidates CASCADE;
DROP TABLE IF EXISTS ai_evaluations CASCADE;
DROP TABLE IF EXISTS explanations CASCADE;
DROP TABLE IF EXISTS ai_responses CASCADE;
DROP TABLE IF EXISTS ai_requests CASCADE;
DROP TABLE IF EXISTS ai_prompts CASCADE;
DROP TABLE IF EXISTS analyses CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS skill_gaps CASCADE;
DROP TABLE IF EXISTS resume_skills CASCADE;
DROP TABLE IF EXISTS job_skill_requirements CASCADE;
DROP TABLE IF EXISTS resume_bullets CASCADE;
DROP TABLE IF EXISTS resume_sections CASCADE;
DROP TABLE IF EXISTS resume_versions CASCADE;
DROP TABLE IF EXISTS resumes CASCADE;
DROP TABLE IF EXISTS job_descriptions CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS templates CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop materialized views
DROP MATERIALIZED VIEW IF EXISTS current_resumes CASCADE;

-- Drop views  
DROP VIEW IF EXISTS ai_request_summary CASCADE;
DROP VIEW IF EXISTS user_skill_gaps CASCADE;
DROP VIEW IF EXISTS prompt_performance CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS refresh_current_resumes() CASCADE;
DROP FUNCTION IF EXISTS record_ai_request CASCADE;
DROP FUNCTION IF EXISTS record_ai_response CASCADE;
DROP FUNCTION IF EXISTS get_resume_with_job_match CASCADE;
DROP FUNCTION IF EXISTS calculate_ats_score CASCADE;
DROP FUNCTION IF EXISTS get_promotable_prompt_candidates CASCADE;
DROP FUNCTION IF EXISTS promote_prompt_to_production CASCADE;
