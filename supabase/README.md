# Supabase AI Platform Setup

## Overview

This directory contains SQL migrations for the CareerCopilot AI platform, powered by Supabase (PostgreSQL).

## Architecture

### Database Design Principles
1. **Relational First**: Core data uses relational tables with proper foreign keys
2. **JSONB for Flexibility**: Metadata and unstructured data in JSONB columns
3. **Immutable Prompts**: Production prompts cannot be edited (only retired)
4. **Complete Observability**: Every AI request/response logged
5. **RLS Security**: Row-level security for multi-tenant isolation

### Key Features
- ✅ **Prompt Versioning**: Immutable production prompts with rollback support
- ✅ **Request/Response Logging**: Complete audit trail of all AI operations
- ✅ **Cost Tracking**: Per-request token usage and cost estimation
- ✅ **Evaluation Pipeline**: Quality metrics for AI responses
- ✅ **Auto-improvement**: Safe, validated prompt optimization
- ✅ **Explainability**: Link AI outputs to deterministic signals
- ✅ **RLS Policies**: Secure multi-tenant data access

## Migration Files

### 20250101000000_initial_schema.sql
Core data model:
- `user_profiles` - User account information
- `resumes` - Resume master records
- `resume_versions` - Version control for resumes
- `resume_sections` - Resume sections (experience, education, etc.)
- `resume_bullets` - Individual bullet points with signals
- `job_descriptions` - Job postings for matching
- `job_skill_requirements` - Required skills per job
- `skills` - Skills taxonomy (hierarchical)
- `resume_skills` - Skills extracted from resumes
- `skill_gaps` - Identified skill gaps

### 20250101000001_ai_platform.sql
AI system tables:
- `ai_prompts` - Versioned prompt registry
- `ai_requests` - Every AI request logged
- `ai_responses` - Validated AI outputs
- `explanations` - User-facing explanations with signals
- `ai_evaluations` - Quality assessments
- `prompt_candidates` - Auto-improvement pipeline
- `applications` - Job application tracking

**Triggers:**
- `prevent_production_prompt_edits()` - Blocks editing production prompts
- `update_updated_at_column()` - Auto-updates timestamps

### 20250101000002_rls_policies.sql
Row Level Security policies:
- User data isolation (users see only their data)
- AI system transparency (users can read production prompts)
- Admin bypass for service role
- Secure multi-tenant operation

### 20250101000003_views_rpcs.sql
Optimized read patterns:
- **Materialized View**: `current_resumes` - Fast access to active resumes
- **View**: `ai_request_summary` - Observability dashboard
- **View**: `user_skill_gaps` - Real-time skill matching
- **View**: `prompt_performance` - Prompt quality metrics

**Stored Procedures (RPCs):**
- `get_resume_with_job_match()` - Single call for resume + analysis
- `record_ai_request()` - Atomic request logging with stats update
- `record_ai_response()` - Response logging with validation
- `calculate_ats_score()` - Deterministic ATS scoring
- `get_promotable_prompt_candidates()` - Filter ready candidates
- `promote_prompt_to_production()` - Safe prompt deployment

### 20250101000004_seed_prompts.sql
Production-ready AI prompts:
- `analyze_resume_v1` - Comprehensive resume analysis
- `generate_bullets_v1` - STAR-format bullet generation
- `extract_skills_v1` - Skill extraction and categorization
- `match_job_v1` - Job-resume matching
- `optimize_summary_v1` - Resume summary optimization

## Setup Instructions

### 1. Create Supabase Project
```bash
# Go to https://supabase.com
# Create new project
# Note down:
# - Project URL
# - anon (public) key
# - service_role (secret) key
```

### 2. Set Environment Variables
```bash
# In backend/.env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Keep your existing DATABASE_URL for backward compatibility
DATABASE_URL=postgresql://...
```

### 3. Run Migrations

**Option A: Using Supabase CLI (Recommended)**
```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push

# Or run individually
supabase db execute -f supabase/migrations/20250101000000_initial_schema.sql
supabase db execute -f supabase/migrations/20250101000001_ai_platform.sql
supabase db execute -f supabase/migrations/20250101000002_rls_policies.sql
supabase db execute -f supabase/migrations/20250101000003_views_rpcs.sql
supabase db execute -f supabase/migrations/20250101000004_seed_prompts.sql
```

**Option B: Using SQL Editor in Supabase Dashboard**
1. Go to Supabase Dashboard → SQL Editor
2. Copy contents of each migration file
3. Execute in order (000000 → 000004)

**Option C: Using psql**
```bash
# Get connection string from Supabase dashboard
psql "postgresql://postgres:[YOUR-PASSWORD]@db.your-project.supabase.co:5432/postgres"

# Run migrations
\i supabase/migrations/20250101000000_initial_schema.sql
\i supabase/migrations/20250101000001_ai_platform.sql
\i supabase/migrations/20250101000002_rls_policies.sql
\i supabase/migrations/20250101000003_views_rpcs.sql
\i supabase/migrations/20250101000004_seed_prompts.sql
```

### 4. Verify Setup
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';

-- Check prompts loaded
SELECT skill_name, version, status 
FROM ai_prompts 
ORDER BY skill_name;

-- Test a stored procedure
SELECT * FROM get_promotable_prompt_candidates();
```

## Usage Examples

### Python (FastAPI Backend)

```python
from app.repositories import AIRepository, ResumeRepository
from app.services.ai_orchestrator_v2 import AIOrchestrator, AIRequestMetadata
from uuid import uuid4

# Initialize
ai_repo = AIRepository()
orchestrator = AIOrchestrator(ai_repo)

# Execute AI skill
metadata = AIRequestMetadata(
    user_id=uuid4(),
    skill_name="analyze_resume",
    trace_id="trace-123"
)

response = await orchestrator.analyze_resume(
    user_id=user_id,
    resume_text="...",
    job_description="..."
)

print(f"Request ID: {response.request_id}")
print(f"Confidence: {response.confidence_score}")
print(f"Cost: ${response.cost_usd}")
print(f"Output: {response.structured_output}")
```

### Direct Repository Access

```python
from app.repositories import AIRepository
from uuid import UUID

ai_repo = AIRepository()

# Get production prompt
prompt = ai_repo.get_production_prompt("analyze_resume")
print(f"Using prompt v{prompt['version']}")

# Get observability data
summary = ai_repo.get_ai_request_summary(
    skill_name="analyze_resume",
    start_date=datetime(2025, 1, 1)
)

for day in summary:
    print(f"{day['request_date']}: {day['request_count']} requests, ${day['total_cost_usd']:.4f}")
```

## Security Considerations

### Service Role vs Anon Key

**Service Role (Backend Only)**
- Used by AI Orchestrator
- Bypasses RLS
- NEVER expose to frontend
- Required for AI logging

**Anon Key (Frontend Safe)**
- Used by user-facing features
- Respects RLS policies
- Safe to expose in frontend
- Users see only their data

### RLS Testing

```sql
-- Test as user
SET request.jwt.claims = '{"sub": "user-uuid-here"}';

-- Should only see own resumes
SELECT * FROM resumes;

-- Reset
RESET request.jwt.claims;
```

## Observability Dashboard

### Cost Tracking
```sql
-- Daily AI costs
SELECT 
    request_date,
    SUM(total_cost_usd) as daily_cost,
    SUM(request_count) as total_requests
FROM ai_request_summary
WHERE request_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY request_date
ORDER BY request_date DESC;
```

### Prompt Performance
```sql
-- Best performing prompts
SELECT 
    skill_name,
    version,
    success_rate,
    avg_latency_ms,
    avg_cost_usd,
    total_uses
FROM prompt_performance
WHERE status = 'production'
ORDER BY success_rate DESC, avg_latency_ms ASC;
```

### Error Monitoring
```sql
-- Recent failed requests
SELECT 
    req.created_at,
    req.skill_name,
    req.user_id,
    resp.validation_errors
FROM ai_requests req
JOIN ai_responses resp ON req.id = resp.request_id
WHERE resp.validation_passed = false
ORDER BY req.created_at DESC
LIMIT 100;
```

## Auto-Improvement Pipeline

### Weekly Process (Manual for now, will automate)

1. **Collect Evaluations**
```sql
SELECT * FROM ai_evaluations 
WHERE created_at >= NOW() - INTERVAL '7 days';
```

2. **Generate Candidates**
```python
# AI analyzes low-scoring responses
# Proposes improved prompt
candidate_id = ai_repo.create_prompt_candidate(
    skill_name="analyze_resume",
    current_prompt_id=current_prompt.id,
    new_prompt_text="...",
    change_rationale="Improved clarity based on user feedback"
)
```

3. **Test Candidate**
```python
# Run 100+ test cases with candidate prompt
for test_case in test_cases:
    response = await orchestrator.execute_skill(
        skill_name="analyze_resume",
        input_data=test_case,
        metadata=metadata,
        use_prompt_version=candidate_version  # Test version
    )
    # Evaluate response...

# Update candidate with results
ai_repo.update_candidate_test_results(
    candidate_id=candidate_id,
    test_run_count=100,
    avg_score=0.85,
    vs_current_delta=0.07  # 7% improvement
)
```

4. **Promote to Production**
```python
# Manual review, then promote
promotable = ai_repo.get_promotable_candidates()
for candidate in promotable:
    # Admin reviews and approves
    new_prompt_id = ai_repo.promote_candidate_to_production(
        candidate_id=candidate['candidate_id'],
        admin_user_id=admin_user_id
    )
    print(f"Deployed {candidate['skill_name']} v{new_version}")
```

## Maintenance

### Refresh Materialized Views
```sql
-- Run daily via cron
SELECT refresh_current_resumes();
```

### Archive Old Data
```sql
-- Archive AI requests older than 90 days
-- (Keep for compliance, move to cold storage)
```

### Monitor Database Size
```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Troubleshooting

### RLS Blocking Queries
```sql
-- Temporarily disable for debugging (BE CAREFUL)
ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;

-- Re-enable when done
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;
```

### Slow Queries
```sql
-- Check for missing indexes
SELECT * FROM pg_stat_user_tables 
WHERE schemaname = 'public' 
ORDER BY seq_scan DESC;
```

### Prompt Not Found
```python
# Ensure prompt is deployed
prompt = ai_repo.get_production_prompt("skill_name")
if not prompt:
    print("No production prompt - check seed_prompts.sql was run")
```

## Future Enhancements

- [ ] Real-time evaluation triggers
- [ ] Automated A/B testing
- [ ] Cost budget alerts
- [ ] Anomaly detection
- [ ] Multi-region replication
- [ ] Advanced caching layer
- [ ] GraphQL API via Hasura

## Support

For issues or questions:
1. Check Supabase logs in Dashboard → Logs
2. Review RLS policies if data access fails
3. Verify migrations ran successfully
4. Check environment variables are set
