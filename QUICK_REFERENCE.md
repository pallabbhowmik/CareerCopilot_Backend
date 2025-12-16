# 🚀 Supabase AI Platform - Quick Reference

## ⚡ Quick Start (5 minutes)

### 1. Get Supabase Credentials
```bash
# Visit: https://supabase.com/dashboard
# Project Settings → API → Copy these:
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
```

### 2. Run Migrations
```bash
# Supabase Dashboard → SQL Editor → Run each file:
supabase/migrations/20250101000000_initial_schema.sql
supabase/migrations/20250101000001_ai_platform.sql
supabase/migrations/20250101000002_rls_policies.sql
supabase/migrations/20250101000003_views_rpcs.sql
supabase/migrations/20250101000004_seed_prompts.sql
```

### 3. Test Connection
```python
from app.repositories import get_supabase
client = get_supabase()
prompts = client.table('ai_prompts').select('*').execute()
print(f"✓ {len(prompts.data)} prompts loaded")
```

## 🎯 Common Tasks

### Execute AI Skill
```python
from app.services.ai_orchestrator_v2 import AIOrchestrator, AIRequestMetadata
from uuid import uuid4

orchestrator = AIOrchestrator()

response = await orchestrator.analyze_resume(
    user_id=uuid4(),
    resume_text="Your resume here...",
    trace_id="trace-123"
)

print(f"Cost: ${response.cost_usd}")
print(f"Result: {response.structured_output}")
```

### Get User's AI Usage
```python
from app.repositories import AIRepository
from datetime import datetime, timedelta

ai_repo = AIRepository()
summary = ai_repo.get_ai_request_summary(
    user_id=user_id,
    start_date=datetime.now() - timedelta(days=30)
)
```

### Create Evaluation
```python
ai_repo.create_evaluation(
    response_id=response.response_id,
    evaluator_type="human",
    helpfulness_score=0.9,
    safety_score=1.0,
    consistency_score=0.85,
    evaluator_notes="Very helpful suggestions"
)
```

## 📊 Observability Queries

### Daily Costs
```sql
SELECT 
    request_date,
    SUM(total_cost_usd) as cost,
    SUM(request_count) as requests
FROM ai_request_summary
WHERE request_date >= CURRENT_DATE - 30
GROUP BY request_date
ORDER BY request_date DESC;
```

### Prompt Performance
```sql
SELECT 
    skill_name,
    success_rate,
    avg_latency_ms,
    total_uses
FROM prompt_performance
WHERE status = 'production'
ORDER BY success_rate DESC;
```

### Failed Requests
```sql
SELECT 
    req.created_at,
    req.skill_name,
    resp.validation_errors
FROM ai_requests req
JOIN ai_responses resp ON req.id = resp.request_id
WHERE resp.validation_passed = false
ORDER BY req.created_at DESC
LIMIT 20;
```

## 🔧 Troubleshooting

### "No prompt found"
```bash
# Run seed migration:
# supabase/migrations/20250101000004_seed_prompts.sql
```

### "RLS policy violation"
```python
# Use service role client:
from app.repositories import get_supabase
client = get_supabase()  # Not get_user_supabase()
```

### High Latency
```sql
-- Check slow prompts
SELECT * FROM prompt_performance 
WHERE avg_latency_ms > 5000;
```

## 📁 Key Files

```
backend/
├── supabase/
│   ├── README.md                     ← Setup guide
│   ├── INTEGRATION_GUIDE.md          ← How to use
│   ├── DEPLOYMENT_CHECKLIST.md       ← Deploy steps
│   └── migrations/                   ← SQL files
│
├── app/
│   ├── repositories/
│   │   ├── supabase_client.py        ← Connection
│   │   └── ai_repository.py          ← AI data access
│   │
│   └── services/
│       └── ai_orchestrator_v2.py     ← AI coordinator
│
└── SUPABASE_IMPLEMENTATION_SUMMARY.md ← This guide
```

## 🎯 5 Production AI Skills

1. **analyze_resume** - Comprehensive analysis
2. **generate_bullets** - STAR-format bullets
3. **extract_skills** - Skill extraction
4. **match_job** - Job matching
5. **optimize_summary** - Summary optimization

## 🔒 Security Checklist

- [ ] Service role key is SECRET (never in frontend)
- [ ] RLS enabled on all tables
- [ ] Environment variables set correctly
- [ ] HTTPS only in production
- [ ] Prompt injection checks enabled

## 📈 Success Metrics

- **Latency**: < 3s average
- **Validation Rate**: > 95%
- **Safety**: 100% pass
- **Cost**: < $0.10 per request

## 🆘 Emergency Rollback

```python
# Feature flag in .env:
FEATURE_SUPABASE_AI=false  # Disable immediately
```

```sql
-- Rollback prompt:
UPDATE ai_prompts SET status = 'retired' 
WHERE skill_name = 'X' AND version = 2;

UPDATE ai_prompts SET status = 'production' 
WHERE skill_name = 'X' AND version = 1;
```

## 📞 Get Help

- **Setup Issues**: Read `supabase/README.md`
- **Integration**: Check `supabase/INTEGRATION_GUIDE.md`
- **Deployment**: Follow `supabase/DEPLOYMENT_CHECKLIST.md`
- **Supabase Support**: https://supabase.com/dashboard/support

## 🎉 Next Steps

1. ✅ Run migrations (10 min)
2. ✅ Test locally (5 min)
3. ✅ Deploy to Render (10 min)
4. 📊 Set up monitoring
5. 👥 Collect user feedback
6. 🔄 Start auto-improvement

---

**Time to Production: 1-2 hours**

**Break-even Point: 100 AI requests**

**Built for Enterprise Scale**
