# Supabase Integration Guide

## Quick Start

This guide shows how to integrate the Supabase-backed AI platform into your existing FastAPI application.

## Installation

```bash
cd backend
pip install supabase>=2.0.0
```

## Environment Setup

Add to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...  # Safe for frontend
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Backend only, SECRET!

# Existing config (keep these)
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
```

## Architecture

```
┌─────────────────────────────────────────────┐
│              FastAPI Endpoint               │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│           AI Orchestrator V2                │
│  • Prompt loading                           │
│  • Request/response logging                 │
│  • Validation & safety checks               │
│  • Cost tracking                            │
└───────┬─────────────────┬───────────────────┘
        │                 │
        ▼                 ▼
┌──────────────┐  ┌──────────────────────────┐
│  LLM Client  │  │    AI Repository         │
│  (OpenAI)    │  │    (Supabase)            │
└──────────────┘  └──────────────────────────┘
                            │
                            ▼
                  ┌──────────────────────────┐
                  │   Supabase Database      │
                  │   • ai_prompts           │
                  │   • ai_requests          │
                  │   • ai_responses         │
                  │   • ai_evaluations       │
                  └──────────────────────────┘
```

## Step-by-Step Integration

### Step 1: Update Existing Endpoints

Replace direct AI calls with orchestrator:

**Before (old way):**
```python
from app.services.ai_service import AIService

@router.post("/resume/analyze")
async def analyze_resume(resume_text: str):
    ai_service = AIService()
    result = await ai_service.analyze(resume_text)
    return {"analysis": result}
```

**After (Supabase-backed):**
```python
from app.services.ai_orchestrator_v2 import AIOrchestrator, AIRequestMetadata
from uuid import UUID

@router.post("/resume/analyze")
async def analyze_resume(
    resume_text: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    orchestrator = AIOrchestrator()
    
    response = await orchestrator.analyze_resume(
        user_id=current_user_id,
        resume_text=resume_text,
        trace_id=f"analyze-{uuid4()}"
    )
    
    # All logging happens automatically!
    return {
        "analysis": response.structured_output,
        "confidence": response.confidence_score,
        "request_id": str(response.request_id)  # For tracking
    }
```

### Step 2: Create New AI-Powered Endpoints

Example: Bullet point generation

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.ai_orchestrator_v2 import AIOrchestrator, AIRequestMetadata
from app.repositories import AIRepository

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])

class BulletGenerationRequest(BaseModel):
    job_title: str
    company: str
    experience_description: str

class BulletGenerationResponse(BaseModel):
    bullets: list[dict]
    suggested_skills: list[str]
    request_id: str
    cost_usd: float

@router.post("/generate-bullets", response_model=BulletGenerationResponse)
async def generate_bullets(
    request: BulletGenerationRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Generate optimized resume bullet points"""
    orchestrator = AIOrchestrator()
    
    try:
        response = await orchestrator.generate_bullets(
            user_id=current_user_id,
            experience_description=request.experience_description,
            job_title=request.job_title,
            company=request.company
        )
        
        if not response.validation_passed:
            raise HTTPException(
                status_code=500,
                detail=f"AI validation failed: {response.validation_errors}"
            )
        
        return BulletGenerationResponse(
            bullets=response.structured_output["bullets"],
            suggested_skills=response.structured_output.get("suggested_skills", []),
            request_id=str(response.request_id),
            cost_usd=response.cost_usd
        )
        
    except Exception as e:
        # Error is already logged in Supabase by orchestrator
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 3: Add Observability Endpoints

Track AI usage and costs:

```python
from datetime import datetime, timedelta
from app.repositories import AIRepository

@router.get("/ai/stats")
async def get_ai_stats(
    current_user_id: UUID = Depends(get_current_user_id),
    days: int = 30
):
    """Get AI usage statistics for current user"""
    ai_repo = AIRepository()
    
    summary = ai_repo.get_ai_request_summary(
        user_id=current_user_id,
        start_date=datetime.now() - timedelta(days=days)
    )
    
    # Aggregate stats
    total_requests = sum(row["request_count"] for row in summary)
    total_cost = sum(row["total_cost_usd"] for row in summary)
    avg_latency = sum(row["avg_latency_ms"] * row["request_count"] for row in summary) / total_requests if total_requests > 0 else 0
    
    return {
        "period_days": days,
        "total_requests": total_requests,
        "total_cost_usd": round(total_cost, 4),
        "avg_latency_ms": round(avg_latency, 0),
        "by_skill": [
            {
                "skill_name": row["skill_name"],
                "requests": row["request_count"],
                "cost": round(row["total_cost_usd"], 4)
            }
            for row in summary
        ]
    }

@router.get("/ai/prompts")
async def list_prompts():
    """List all production AI prompts (transparency)"""
    ai_repo = AIRepository()
    prompts = ai_repo.list_prompts(status="production")
    
    return {
        "prompts": [
            {
                "skill_name": p["skill_name"],
                "version": p["version"],
                "model": p["model"],
                "success_rate": p.get("success_rate", 0),
                "avg_cost_usd": p.get("avg_cost_usd", 0),
                "deployed_at": p["deployed_at"]
            }
            for p in prompts
        ]
    }
```

### Step 4: Add Request Tracking to Existing Features

For existing resume operations, add explanations:

```python
from app.repositories import AIRepository

@router.post("/resume/{resume_id}/sections/{section_id}/bullets")
async def create_bullet(
    resume_id: UUID,
    section_id: UUID,
    bullet_text: str,
    ai_response_id: Optional[UUID] = None,  # NEW: Link to AI
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create resume bullet (potentially AI-generated)"""
    
    # Your existing logic to create bullet...
    bullet_id = resume_service.create_bullet(
        section_id=section_id,
        bullet_text=bullet_text,
        ai_response_id=ai_response_id  # Track AI provenance
    )
    
    # If AI-generated, create explanation
    if ai_response_id:
        ai_repo = AIRepository()
        
        # Get the AI response details
        request_data = ai_repo.get_request_with_response(ai_response_id)
        
        # Create explanation linking to deterministic signals
        explanation_id = ai_repo.create_explanation(
            resume_version_id=resume_version_id,
            section_type="bullets",
            explanation_text=f"Generated using AI based on your experience at {company}",
            deterministic_signals=[
                "action_verb:Led",
                "metric:45%",
                "star_format:complete"
            ],
            confidence_level="high",
            ai_response_id=ai_response_id
        )
    
    return {"bullet_id": str(bullet_id)}
```

### Step 5: Implement Feedback Loop

Allow users to rate AI suggestions:

```python
@router.post("/ai/feedback")
async def submit_ai_feedback(
    response_id: UUID,
    helpfulness_score: float,  # 0.0-1.0
    safety_score: float,
    consistency_score: float,
    notes: Optional[str] = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Submit feedback on AI response"""
    ai_repo = AIRepository()
    
    evaluation_id = ai_repo.create_evaluation(
        response_id=response_id,
        evaluator_type="human",
        helpfulness_score=helpfulness_score,
        safety_score=safety_score,
        consistency_score=consistency_score,
        evaluator_notes=notes
    )
    
    return {
        "evaluation_id": str(evaluation_id),
        "message": "Thank you for your feedback!"
    }
```

## Testing

### Unit Tests

```python
import pytest
from app.services.ai_orchestrator_v2 import AIOrchestrator, AIRequestMetadata
from app.repositories import AIRepository
from uuid import uuid4

@pytest.mark.asyncio
async def test_analyze_resume():
    """Test resume analysis with mocked AI"""
    orchestrator = AIOrchestrator()
    user_id = uuid4()
    
    response = await orchestrator.analyze_resume(
        user_id=user_id,
        resume_text="Software Engineer with 5 years Python experience...",
        trace_id="test-123"
    )
    
    assert response.validation_passed
    assert response.confidence_score > 0.5
    assert "overall_score" in response.structured_output
    assert response.cost_usd > 0

def test_ai_repository():
    """Test AI repository methods"""
    ai_repo = AIRepository()
    
    # Get production prompt
    prompt = ai_repo.get_production_prompt("analyze_resume")
    assert prompt is not None
    assert prompt["status"] == "production"
    assert prompt["skill_name"] == "analyze_resume"
    
    # Get request summary
    summary = ai_repo.get_ai_request_summary()
    assert isinstance(summary, list)
```

### Integration Tests

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_bullets_endpoint():
    """Test bullet generation endpoint"""
    response = client.post(
        "/api/v1/ai/generate-bullets",
        json={
            "job_title": "Senior Software Engineer",
            "company": "Tech Corp",
            "experience_description": "Led team of 5 engineers..."
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "bullets" in data
    assert len(data["bullets"]) >= 3
    assert "request_id" in data
    assert data["cost_usd"] > 0
```

## Migration Path

### Phase 1: Parallel Run (Week 1)
- Deploy Supabase schema
- Keep existing AI code
- Add new endpoints using orchestrator
- Test with subset of users

### Phase 2: Gradual Migration (Week 2-3)
- Migrate one endpoint at a time
- Compare outputs between old and new
- Monitor performance and costs
- Fix any issues

### Phase 3: Full Cutover (Week 4)
- Remove old AI code
- All requests through orchestrator
- Enable auto-improvement pipeline
- Set up monitoring dashboards

## Admin Operations

### Deploying New Prompts

```python
from app.repositories import AIRepository

# Create draft prompt
ai_repo = AIRepository()

new_prompt_id = ai_repo.client.table("ai_prompts").insert({
    "skill_name": "new_skill",
    "version": 1,
    "prompt_text": "...",
    "model": "gpt-4",
    "temperature": 0.7,
    "expected_output_schema": {...},
    "status": "draft"  # Start as draft
}).execute()

# Test extensively...

# Promote to production
ai_repo.client.table("ai_prompts").update({
    "status": "production",
    "deployed_at": "now()"
}).eq("id", new_prompt_id).execute()
```

### Monitoring Dashboard

```python
@router.get("/admin/ai/dashboard")
async def ai_dashboard(admin: bool = Depends(verify_admin)):
    """Admin dashboard for AI operations"""
    ai_repo = AIRepository()
    
    # Get overall metrics
    summary = ai_repo.get_ai_request_summary()
    performance = ai_repo.get_prompt_performance()
    candidates = ai_repo.get_promotable_candidates()
    
    return {
        "daily_stats": summary[:30],  # Last 30 days
        "prompt_performance": performance,
        "promotable_candidates": len(candidates),
        "total_cost_30d": sum(row["total_cost_usd"] for row in summary),
        "total_requests_30d": sum(row["request_count"] for row in summary)
    }
```

## Best Practices

### 1. Always Use Trace IDs
```python
trace_id = f"resume-analyze-{user_id}-{timestamp}"
```

### 2. Handle Validation Failures
```python
if not response.validation_passed:
    logger.error(f"AI validation failed: {response.validation_errors}")
    # Fall back to deterministic algorithm
    return fallback_analysis(resume_text)
```

### 3. Cost Monitoring
```python
if response.cost_usd > 0.50:  # Alert on expensive requests
    logger.warning(f"High-cost AI request: ${response.cost_usd}")
```

### 4. Confidence Thresholds
```python
if response.confidence_score < 0.6:
    return {
        "result": response.structured_output,
        "warning": "AI confidence is low - please review carefully"
    }
```

### 5. Security
```python
# NEVER expose service role key
# Use anon key for frontend
# Always validate user_id matches token
```

## Troubleshooting

### Error: "No prompt found"
```python
# Check prompt exists and is production
ai_repo = AIRepository()
prompt = ai_repo.get_production_prompt("skill_name")
if not prompt:
    # Run seed_prompts.sql migration
    pass
```

### Error: "RLS policy violation"
```python
# Using wrong Supabase client
# Backend should use service role:
from app.repositories import get_supabase
client = get_supabase()  # Service role, bypasses RLS
```

### High Latency
```python
# Check prompt performance
performance = ai_repo.get_prompt_performance()
slow_prompts = [p for p in performance if p["avg_latency_ms"] > 5000]
# Consider optimizing prompts or using GPT-3.5
```

## Next Steps

1. ✅ Deploy Supabase schema
2. ✅ Set environment variables
3. ✅ Test orchestrator with one endpoint
4. ⏳ Migrate existing endpoints one by one
5. ⏳ Set up monitoring dashboards
6. ⏳ Enable user feedback collection
7. ⏳ Start auto-improvement pipeline

## Support

Questions? Check:
- [Supabase Setup README](./README.md)
- [Migration Files](./migrations/)
- [AI Orchestrator Code](../app/services/ai_orchestrator_v2.py)
- [Repository Layer](../app/repositories/)
