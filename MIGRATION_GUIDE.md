# 🚀 Supabase Migration Execution Guide

**Last Updated**: December 17, 2025  
**Status**: All schema errors fixed - Ready to execute

---

## ✅ All Errors Fixed

### Issues Resolved:
1. ✅ **Column "version" does not exist** → Fixed to `prompt_version`
2. ✅ **Column r.name does not exist** → Fixed to `r.title`
3. ✅ All `ai_prompts` INSERT statements updated with correct schema
4. ✅ Materialized view `current_resumes` fixed

---

## 📋 Migration Execution Order

Run these migrations **in order** in your Supabase SQL Editor:

### Step 1: Core Schema
```sql
-- File: 20250101000000_initial_schema.sql
-- Creates: user_profiles, resumes, resume_versions, resume_sections, 
--          resume_bullets, job_descriptions, job_skill_requirements, 
--          skills, resume_skills, skill_gaps, applications
-- Size: 10.8 KB
```

### Step 2: AI Platform
```sql
-- File: 20250101000001_ai_platform.sql
-- Creates: ai_prompts, ai_requests, ai_responses, explanations,
--          ai_evaluations, prompt_candidates
-- Triggers: Immutability protection for production prompts
-- Size: 13.7 KB
```

### Step 3: Security Policies
```sql
-- File: 20250101000002_rls_policies.sql
-- Creates: 40+ Row Level Security policies for all tables
-- Ensures: User data isolation, secure access control
-- Size: 13.2 KB
```

### Step 4: Views & Functions
```sql
-- File: 20250101000003_views_rpcs.sql
-- Creates: current_resumes (materialized view), ai_request_summary,
--          user_skill_gaps, prompt_performance views
-- RPCs: record_ai_request, record_ai_response, calculate_ats_score,
--       promote_prompt_to_production
-- Size: 16.7 KB
-- ⚠️ FIXED: Changed r.name → r.title
```

### Step 5: Seed AI Prompts (5 skills)
```sql
-- File: 20250101000004_seed_prompts.sql
-- Inserts: 5 production AI prompts
-- Skills: analyze_resume, generate_bullets, extract_skills,
--         match_job, optimize_summary
-- Size: 12.1 KB
-- ✅ FIXED: All column names corrected
```

### Step 6: Additional AI Prompts (7 skills)
```sql
-- File: 20250101000005_additional_prompts.sql
-- Inserts: 7 additional AI prompts
-- Skills: improve_bullet, explain_bullet_strength, 
--         summarize_section_quality, recommend_template,
--         explain_ats_risk, explain_skill_gaps, career_advisor
-- Size: 13.3 KB
-- ✅ FIXED: All column names corrected
```

---

## 🎯 How to Execute

### Option 1: Supabase Dashboard (Recommended)

1. **Log into Supabase Dashboard**: https://supabase.com/dashboard
2. **Select your project**
3. **Navigate to**: SQL Editor (left sidebar)
4. **For each migration file**:
   - Click "+ New Query"
   - Copy entire content of migration file
   - Paste into SQL Editor
   - Click "Run" (or Ctrl+Enter)
   - ✅ Verify success message appears
5. **Verify completion** (see below)

### Option 2: Supabase CLI

```bash
# Install Supabase CLI (if not already)
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref YOUR_PROJECT_REF

# Run migrations
supabase db push
```

---

## ✅ Verification Queries

After running all migrations, verify everything is set up correctly:

### 1. Check Tables Created
```sql
SELECT COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE';
-- Expected: 17+ tables
```

### 2. Check AI Prompts Loaded
```sql
SELECT COUNT(*) as prompt_count 
FROM ai_prompts 
WHERE status = 'production';
-- Expected: 12 prompts (5 from 000004 + 7 from 000005)
```

### 3. Check RLS Policies Applied
```sql
SELECT COUNT(*) as policy_count 
FROM pg_policies 
WHERE schemaname = 'public';
-- Expected: 40+ policies
```

### 4. Check Views Created
```sql
SELECT COUNT(*) as view_count 
FROM information_schema.views 
WHERE table_schema = 'public';
-- Expected: 4+ views (including 1 materialized view)
```

### 5. Check Functions/RPCs Created
```sql
SELECT COUNT(*) as function_count 
FROM pg_proc 
WHERE pronamespace = 'public'::regnamespace;
-- Expected: 10+ functions
```

### 6. List All AI Skills
```sql
SELECT skill_name, prompt_version, model_name, temperature, status, promoted_at
FROM ai_prompts
WHERE status = 'production'
ORDER BY skill_name;
-- Should show all 12 skills
```

### 7. Check Materialized View
```sql
-- Test that current_resumes view works
SELECT COUNT(*) FROM current_resumes;
-- Should return 0 (no data yet) but NO errors
```

---

## ⚠️ Troubleshooting

### Error: "relation already exists"
**Solution**: Migration was already run. Skip to next migration.

### Error: "column does not exist"
**Cause**: Old migration files (before fix)  
**Solution**: You're using the FIXED versions now. Delete any old data and re-run from scratch:
```sql
-- ⚠️ WARNING: Deletes all data
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
-- Then re-run all migrations
```

### Error: "constraint violation"
**Cause**: Data integrity issue  
**Solution**: Check error message for specific constraint, ensure data quality

### Error: "permission denied"
**Cause**: Insufficient privileges  
**Solution**: Run migrations as database owner or with service_role key

---

## 📊 Expected Result

After successful migration:

```
✅ 17+ tables created
✅ 40+ RLS policies active
✅ 12 AI prompts in production
✅ 4+ views (1 materialized)
✅ 10+ stored procedures/functions
✅ All triggers active
✅ Indexes created
✅ Constraints enforced
```

---

## 🔄 Next Steps After Migration

1. **Set Environment Variables** in Render:
   ```
   SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   SUPABASE_ANON_KEY=your_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   JWT_SECRET_KEY=your_jwt_secret
   OPENAI_API_KEY=your_openai_key
   ```

2. **Test Backend Connection**:
   ```python
   # Run in your backend
   python -c "from app.repositories.supabase_client import get_supabase; print(get_supabase())"
   # Should connect without errors
   ```

3. **Test AI Prompts**:
   ```python
   # Test loading prompts
   from app.repositories.ai_repository import AIRepository
   repo = AIRepository()
   prompt = repo.get_production_prompt('analyze_resume')
   print(f"Loaded prompt: {prompt['skill_name']}")
   ```

4. **Start Phase 1 Implementation** per BUILD_ROADMAP.md

---

## 📝 Migration Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-17 | v2 | Fixed all schema column name mismatches |
| 2025-12-17 | v1 | Initial migration files created |

---

## 🆘 Support

If you encounter issues:

1. **Check Supabase Logs**: Dashboard → Logs → Database
2. **Verify Schema**: Compare with 20250101000001_ai_platform.sql
3. **Test Individual Queries**: Run verification queries one by one
4. **Check GitHub**: Latest fixes at commit `40c8631`

---

**All migrations ready to execute** ✅  
**No schema errors remaining** ✅  
**12 AI prompts ready to load** ✅
