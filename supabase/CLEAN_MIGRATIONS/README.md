# 🚀 JobPathAI Database Setup Guide

## Quick Start (3 Steps)

### 1️⃣ Reset Database (Clean Slate)

**Open Supabase SQL Editor:**
- Go to: https://supabase.com/dashboard
- Select project: `civkxziltjtalooemdbr`
- Click: SQL Editor → New Query

**Run Reset Script:**
```sql
-- Copy and paste entire RESET_DATABASE.sql content
-- WARNING: This deletes ALL data!
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
```

✅ **Result:** Empty database ready for migration

---

### 2️⃣ Run Migrations in Order

Run each script **one at a time** in the same SQL Editor:

#### **Migration 1: Core Schema**
1. Open: `CLEAN_MIGRATIONS/01_core_schema.sql`
2. Copy entire file
3. Paste in SQL Editor
4. Click **Run** (Ctrl+Enter)
5. ✅ Should see: "Success. No rows returned"

**Creates:** All tables (user_profiles, resumes, resume_versions, job_descriptions, skills, applications, AI tables)

---

#### **Migration 2: Enable RLS**
1. Open: `CLEAN_MIGRATIONS/02_enable_rls.sql`
2. Copy entire file
3. Paste in SQL Editor
4. Click **Run**
5. ✅ Should see: "Success. No rows returned"

**Creates:** All Row Level Security policies for data protection

---

#### **Migration 3: Storage (Optional)**
1. Open: `CLEAN_MIGRATIONS/03_storage_setup.sql`
2. Copy entire file
3. Paste in SQL Editor
4. Click **Run**
5. ✅ Should see: "Success. No rows returned"

**Creates:** Storage buckets for resume uploads and avatars

---

## ✅ Verify Setup

Run this query to confirm everything worked:

```sql
-- Check tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- Should return 17 tables:
-- ai_evaluations, ai_prompts, ai_requests, ai_responses
-- applications, explanations, job_descriptions
-- job_skill_requirements, prompt_candidates, resume_bullets
-- resume_sections, resume_skills, resume_versions, resumes
-- skill_gaps, skills, user_profiles

-- Check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- All should show: rowsecurity = true

-- Check policies exist
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename;

-- Should show ~30+ policies
```

---

## 🧪 Test the Fix

1. **Refresh your app:** https://career-copilot-frontend-two.vercel.app
2. **Login/Signup:** Create a test account
3. **Check Console (F12):**
   - ✅ No 403 errors
   - ✅ No "permission denied" errors
   - ✅ User profile loads
   - ✅ Resume upload works

---

## 📊 Database Schema Overview

### Core Tables:
- **user_profiles**: User account data
- **resumes**: Resume documents
- **resume_versions**: Version history
- **resume_sections**: Parsed resume sections
- **resume_bullets**: Individual bullet points
- **job_descriptions**: Saved job postings
- **skills**: Master skills list
- **resume_skills**: Skills per resume
- **job_skill_requirements**: Required skills per job
- **skill_gaps**: Missing skills analysis
- **applications**: Job applications tracking

### AI Platform:
- **ai_prompts**: Prompt templates
- **ai_requests**: AI request logs
- **ai_responses**: AI response logs
- **explanations**: AI-generated explanations
- **ai_evaluations**: Quality metrics
- **prompt_candidates**: A/B testing

---

## 🔒 Security Features

✅ **Row Level Security (RLS)** enabled on all tables  
✅ **Users can only access their own data**  
✅ **Direct auth.uid() comparisons** (no circular references)  
✅ **Service role bypass** for backend operations  
✅ **Storage policies** for file uploads  

---

## 🆘 Troubleshooting

### Issue: "relation already exists"
**Solution:** You already have tables. Either:
1. Skip to migration 2 (RLS policies)
2. Or run RESET_DATABASE.sql first to start fresh

### Issue: "column does not exist"
**Solution:** Run migration 1 (01_core_schema.sql) first

### Issue: Still getting 403 errors
**Check:**
1. RLS policies created (run verification query)
2. User is authenticated (check auth.uid())
3. User profile exists in user_profiles table

```sql
-- Check your user profile
SELECT * FROM user_profiles WHERE user_id = auth.uid();

-- If empty, create one:
INSERT INTO user_profiles (user_id, email, full_name)
VALUES (auth.uid(), auth.email(), 'Your Name');
```

---

## 📁 File Structure

```
backend/supabase/
├── CLEAN_MIGRATIONS/           ← NEW! Use these
│   ├── 01_core_schema.sql     (Step 1: Tables)
│   ├── 02_enable_rls.sql      (Step 2: Security)
│   └── 03_storage_setup.sql   (Step 3: Files)
├── migrations/                 ← OLD (ignore these)
│   ├── 20250101000000_*.sql
│   └── ...
└── RESET_DATABASE.sql         (Clean slate)
```

---

## ✨ What's Different?

### Old migrations had:
- ❌ Circular RLS policy references
- ❌ Missing columns (variant_group_id)
- ❌ Complex subqueries causing 403 errors
- ❌ 15+ fragmented migration files

### New migrations have:
- ✅ Direct auth.uid() comparisons
- ✅ Clean schema (no extra columns)
- ✅ Simple, working RLS policies
- ✅ 3 consolidated files

---

## 🎉 Success Checklist

- [ ] Ran RESET_DATABASE.sql
- [ ] Ran 01_core_schema.sql successfully
- [ ] Ran 02_enable_rls.sql successfully
- [ ] Ran 03_storage_setup.sql (if needed)
- [ ] Verified 17 tables exist
- [ ] Verified RLS enabled on all tables
- [ ] Verified ~30+ policies created
- [ ] Tested app - no 403 errors
- [ ] User profile loads correctly
- [ ] Resume upload works

---

**Need Help?** Check the console errors and compare with the verification queries above.
