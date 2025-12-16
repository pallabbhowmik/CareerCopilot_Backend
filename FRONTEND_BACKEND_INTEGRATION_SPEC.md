# Frontend → Backend Integration Specification

## 📋 Table of Contents
1. [Feature-by-Feature Breakdown](#feature-by-feature-breakdown)
2. [AI Usage Guidelines](#ai-usage-guidelines)
3. [Endpoint Specifications](#endpoint-specifications)
4. [Build Order](#build-order)
5. [Safety Guarantees](#safety-guarantees)

---

## 🎯 Core Principle

**AI is used ONLY for interpretation, language improvement, and reasoning.**

**AI NEVER:**
- ❌ Decides outcomes
- ❌ Touches database directly
- ❌ Makes guarantees
- ❌ Runs in real-time self-improvement

---

## 1️⃣ AUTH (Signup / Login / OAuth / Reset)

### Frontend
```typescript
// Supabase Auth UI
import { Auth } from '@supabase/auth-ui-react'

// Providers: Email, Google, GitHub, LinkedIn
// Password reset & magic links handled by Supabase
```

### Backend
```python
# FastAPI JWT validation
from app.core.security import verify_token

@router.get("/protected")
async def protected_route(user_id: UUID = Depends(get_current_user_id)):
    # user_id extracted from JWT
    pass
```

### Database
```sql
-- Supabase auth.users (managed by Supabase)
-- Trigger creates user_profiles row automatically
```

### 🧠 AI Usage
**NONE** - Auth must be deterministic and fast.

### Endpoints
- `POST /v1/auth/signup` - Create account (handled by Supabase)
- `POST /v1/auth/login` - Login (handled by Supabase)
- `POST /v1/auth/reset` - Password reset (handled by Supabase)

---

## 2️⃣ ONBOARDING (Role, Goal, Country)

### Frontend
```typescript
// Simple form
const onboardingData = {
  role: "Software Engineer",
  experience_years: 5,
  country: "US",
  goal: "faang" // or "startup", "remote", etc.
}

await fetch('/api/v1/profile', {
  method: 'POST',
  body: JSON.stringify(onboardingData)
})
```

### Backend
```python
@router.post("/v1/profile")
async def create_profile(
    profile: ProfileCreate,
    user_id: UUID = Depends(get_current_user_id)
):
    # Save to user_profiles
    profile_repo = ProfileRepository()
    profile_repo.create_or_update(user_id, profile)
    return {"status": "success"}
```

### Database
```sql
-- user_profiles table
INSERT INTO user_profiles (user_id, role, experience_years, country, goal)
VALUES ($1, $2, $3, $4, $5);
```

### 🧠 AI Usage
**NONE** - Keep onboarding fast and predictable.

### Endpoints
- `POST /v1/profile` - Create/update profile
- `GET /v1/profile` - Get user profile

---

## 3️⃣ RESUME UPLOAD & PARSING

### Frontend
```typescript
// Upload PDF/DOCX
const formData = new FormData()
formData.append('file', resumeFile)

const response = await fetch('/api/v1/resumes/upload', {
  method: 'POST',
  body: formData
})

// Poll for parsing completion
const { resume_id } = await response.json()
await pollParsingStatus(resume_id)
```

### Backend
```python
@router.post("/v1/resumes/upload")
async def upload_resume(
    file: UploadFile,
    user_id: UUID = Depends(get_current_user_id)
):
    # 1. Save file to storage
    file_url = await storage.upload(file, user_id)
    
    # 2. Create resume record
    resume_id = resume_repo.create_resume(user_id, file_url)
    
    # 3. Parse resume (background task)
    await parse_resume_task.delay(resume_id)
    
    return {"resume_id": resume_id, "status": "parsing"}

async def parse_resume_task(resume_id: UUID):
    # Extract text
    text = extract_text_from_file(file_url)
    
    # Deterministic parsing
    sections = parse_sections(text)
    bullets = parse_bullets(text)
    
    # Compute signals
    for bullet in bullets:
        bullet.signals = compute_bullet_signals(bullet.text)
    
    # Save to database
    version_id = resume_repo.create_version(resume_id, sections, bullets)
    
    # OPTIONAL: Minimal AI for skill extraction only
    skills = await orchestrator.extract_skills(
        user_id=user_id,
        resume_text=text
    )
    resume_repo.add_skills(version_id, skills.structured_output)
```

### Database
```sql
-- Creates:
INSERT INTO resumes (user_id, name, file_url) VALUES ...;
INSERT INTO resume_versions (resume_id, version_number) VALUES ...;
INSERT INTO resume_sections (resume_version_id, section_type) VALUES ...;
INSERT INTO resume_bullets (section_id, bullet_text, signals) VALUES ...;
```

### 🧠 AI Usage
**Minimal** - Only for skill extraction if deterministic parser fails.
- Skill: `extract_skills`
- Why: Skills are hard to parse deterministically
- Fallback: Always validate with user

### Endpoints
- `POST /v1/resumes/upload` - Upload and trigger parsing
- `GET /v1/resumes/{id}/parsing-status` - Check progress
- `GET /v1/resumes/{id}/parsed` - Get parsed result

---

## 4️⃣ PARSING REVIEW SCREEN

### Frontend
```typescript
// Display parsed resume for user confirmation
const parsed = await fetch(`/api/v1/resumes/${resumeId}/parsed`)

// Highlight ambiguities
parsed.bullets.forEach(bullet => {
  if (bullet.parsing_confidence < 0.8) {
    highlightForReview(bullet)
  }
})
```

### Backend
```python
@router.get("/v1/resumes/{resume_id}/parsed")
async def get_parsed_resume(
    resume_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    # Fetch via optimized view
    resume = resume_repo.get_full_resume(resume_id)
    
    # RLS ensures user can only see their own data
    return resume
```

### Database
```sql
-- Uses materialized view for performance
SELECT * FROM current_resumes WHERE resume_id = $1;
```

### 🧠 AI Usage
**NONE** - User confirms correctness before AI feedback.

### Endpoints
- `GET /v1/resumes/{id}/parsed` - Get structured resume
- `PATCH /v1/resumes/{id}/bullets/{bullet_id}` - User corrections

---

## 5️⃣ RESUME EDITOR (CORE EXPERIENCE)

### Frontend
```typescript
// User clicks "Improve with AI" on a bullet
async function improveBullet(bulletId: string) {
  const response = await fetch(`/api/v1/resumes/bullets/${bulletId}/improve`, {
    method: 'POST'
  })
  
  const result = await response.json()
  
  // Show suggestion with explanation
  showSuggestion({
    original: result.original_text,
    improved: result.improved_text,
    explanation: result.explanation,
    signals: result.signals_used,
    confidence: result.confidence_score
  })
}

// Hover for explanation
async function explainBullet(bulletId: string) {
  const explanation = await fetch(`/api/v1/resumes/bullets/${bulletId}/explain`)
  showTooltip(explanation.text, explanation.signals)
}
```

### Backend
```python
@router.post("/v1/resumes/bullets/{bullet_id}/improve")
async def improve_bullet(
    bullet_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    # 1. Fetch bullet + context
    bullet = resume_repo.get_bullet(bullet_id)
    section = resume_repo.get_section(bullet.section_id)
    
    # 2. Call AI Orchestrator
    orchestrator = AIOrchestrator()
    response = await orchestrator.execute_skill(
        skill_name="improve_bullet",
        input_data={
            "original_text": bullet.bullet_text,
            "context": {
                "section_type": section.section_type,
                "current_signals": bullet.signals
            }
        },
        metadata=AIRequestMetadata(
            user_id=user_id,
            skill_name="improve_bullet",
            trace_id=f"bullet-{bullet_id}"
        )
    )
    
    # 3. Validate output
    if not response.validation_passed:
        raise HTTPException(400, "AI validation failed")
    
    # 4. Save explanation
    explanation_id = ai_repo.create_explanation(
        resume_version_id=section.resume_version_id,
        section_type="bullets",
        explanation_text=response.structured_output["explanation"],
        deterministic_signals=response.structured_output["signals_used"],
        confidence_level="high" if response.confidence_score > 0.8 else "medium",
        ai_response_id=response.response_id
    )
    
    # 5. Return suggestion (don't auto-apply)
    return {
        "original_text": bullet.bullet_text,
        "improved_text": response.structured_output["improved_text"],
        "explanation": response.structured_output["explanation"],
        "signals_used": response.structured_output["signals_used"],
        "confidence_score": response.confidence_score,
        "explanation_id": explanation_id,
        "request_id": response.request_id  # For user feedback
    }

@router.get("/v1/resumes/bullets/{bullet_id}/explain")
async def explain_bullet(
    bullet_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    # Return existing explanation or generate on-demand
    bullet = resume_repo.get_bullet(bullet_id)
    
    # Check for existing explanation
    explanations = ai_repo.get_explanations_for_resume(bullet.resume_version_id)
    existing = [e for e in explanations if bullet_id in e.get("bullet_ids", [])]
    
    if existing:
        return existing[0]
    
    # Generate new explanation
    response = await orchestrator.execute_skill(
        skill_name="explain_bullet_strength",
        input_data={"bullet_text": bullet.bullet_text, "signals": bullet.signals},
        metadata=AIRequestMetadata(user_id=user_id, skill_name="explain_bullet_strength")
    )
    
    return response.structured_output
```

### Database
```sql
-- Reads:
SELECT * FROM resume_bullets WHERE id = $1;
SELECT * FROM explanations WHERE resume_version_id = $1;

-- Writes (via AI Orchestrator):
INSERT INTO ai_requests (...) VALUES (...);
INSERT INTO ai_responses (...) VALUES (...);
INSERT INTO explanations (...) VALUES (...);
```

### 🧠 AI Usage
**Atomic, Explainable, Bullet-Level Only**

#### AI Skills Used:
1. **improve_bullet** - Suggest improved wording
   - Input: Original text + signals
   - Output: Improved text + explanation + signals_used
   - Temperature: 0.7
   - Model: GPT-4

2. **explain_bullet_strength** - Explain why bullet is strong/weak
   - Input: Bullet text + signals
   - Output: User-facing explanation
   - Temperature: 0.3
   - Model: GPT-4

### Endpoints
- `POST /v1/resumes/bullets/{id}/improve` - Get AI improvement suggestion
- `GET /v1/resumes/bullets/{id}/explain` - Get explanation
- `PATCH /v1/resumes/bullets/{id}` - User applies suggestion
- `POST /v1/ai/feedback` - User rates AI suggestion

---

## 6️⃣ RESUME HEATMAP

### Frontend
```typescript
// Visual overlay showing strong/weak areas
const heatmap = await fetch(`/api/v1/resumes/${resumeId}/heatmap`)

heatmap.sections.forEach(section => {
  renderHeatmap(section.id, {
    score: section.score,        // 0-100
    color: getHeatColor(section.score),
    summary: section.summary     // AI-generated summary
  })
})
```

### Backend
```python
@router.get("/v1/resumes/{resume_id}/heatmap")
async def get_resume_heatmap(
    resume_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    # 1. Compute heatmap from deterministic scores
    resume = resume_repo.get_full_resume(resume_id)
    
    heatmap = compute_heatmap_deterministic(resume)
    # Score based on:
    # - Signal density
    # - Metrics presence
    # - Action verb strength
    # - Length appropriateness
    
    # 2. OPTIONAL: AI summarization only
    if should_generate_summary(resume):
        summary_response = await orchestrator.execute_skill(
            skill_name="summarize_section_quality",
            input_data={
                "section_type": section.section_type,
                "deterministic_score": section.score,
                "signals": section.signals
            },
            metadata=AIRequestMetadata(user_id=user_id, skill_name="summarize_section_quality")
        )
        section.summary = summary_response.structured_output["summary"]
    
    return heatmap
```

### 🧠 AI Usage
**Optional Summarization Only**
- Skill: `summarize_section_quality`
- Deterministic engine decides scores
- AI only translates scores into user-friendly language

### Endpoints
- `GET /v1/resumes/{id}/heatmap` - Get visual quality map

---

## 7️⃣ TEMPLATE SELECTION (50+ ATS-SAFE)

### Frontend
```typescript
// AI recommends top 3, user can explore all
const recommendations = await fetch('/api/v1/templates/recommend', {
  method: 'POST',
  body: JSON.stringify({
    role: userProfile.role,
    country: userProfile.country,
    experience_years: userProfile.experience_years
  })
})

// User selects template
await applyTemplate(resumeId, templateId)
```

### Backend
```python
@router.post("/v1/templates/recommend")
async def recommend_templates(
    criteria: TemplateRecommendationCriteria,
    user_id: UUID = Depends(get_current_user_id)
):
    # Call AI for recommendation
    response = await orchestrator.execute_skill(
        skill_name="recommend_template",
        input_data={
            "role": criteria.role,
            "country": criteria.country,
            "experience_years": criteria.experience_years,
            "available_templates": get_all_templates()
        },
        metadata=AIRequestMetadata(user_id=user_id, skill_name="recommend_template")
    )
    
    return {
        "recommended": response.structured_output["top_3"],
        "all_templates": get_all_templates(),
        "reasoning": response.structured_output["reasoning"]
    }

@router.get("/v1/templates")
async def list_templates():
    # Templates are deterministic configs
    return template_repo.list_all()

@router.post("/v1/resumes/{resume_id}/apply-template/{template_id}")
async def apply_template(
    resume_id: UUID,
    template_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    # Apply template config to resume
    template = template_repo.get(template_id)
    resume_repo.update_template(resume_id, template)
    return {"status": "applied"}
```

### 🧠 AI Usage
**Recommendation Only**
- Skill: `recommend_template`
- Templates themselves are deterministic JSON configs
- AI suggests which ones fit user best

### Endpoints
- `GET /v1/templates` - List all templates
- `POST /v1/templates/recommend` - Get AI recommendations
- `POST /v1/resumes/{id}/apply-template/{template_id}` - Apply template

---

## 8️⃣ ATS READINESS (EXPLAINABLE)

### Frontend
```typescript
// NO single score - show sections with explanations
const atsAnalysis = await fetch(`/api/v1/resumes/${resumeId}/ats-analysis`)

// Display results by category
atsAnalysis.categories.forEach(category => {
  renderATSCategory({
    name: category.name,               // "Format", "Keywords", "Structure"
    status: category.status,           // "pass", "warning", "fail"
    explanation: category.explanation, // AI-generated explanation
    deterministic_checks: category.checks // What was actually tested
  })
})
```

### Backend
```python
@router.get("/v1/resumes/{resume_id}/ats-analysis")
async def analyze_ats_readiness(
    resume_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    resume = resume_repo.get_full_resume(resume_id)
    
    # 1. Run deterministic ATS simulation
    ats_results = run_ats_simulation(resume)
    # Checks:
    # - File format compatibility
    # - Font safety
    # - Section header recognition
    # - Bullet point parsing
    # - Date format parsing
    # - Contact info extraction
    # - etc.
    
    # 2. Call AI for explanation of each result
    explanations = []
    for check in ats_results:
        if check.needs_explanation:
            response = await orchestrator.execute_skill(
                skill_name="explain_ats_risk",
                input_data={
                    "check_name": check.name,
                    "result": check.result,
                    "context": check.context
                },
                metadata=AIRequestMetadata(user_id=user_id, skill_name="explain_ats_risk")
            )
            explanations.append({
                "category": check.category,
                "status": check.result,
                "explanation": response.structured_output["explanation"],
                "fix_suggestion": response.structured_output["fix_suggestion"],
                "deterministic_checks": check.details
            })
    
    # 3. Save to database
    ats_evaluation_id = ats_repo.save_evaluation(resume_id, ats_results, explanations)
    
    return {
        "categories": explanations,
        "overall_readiness": calculate_overall_readiness(ats_results),
        "evaluation_id": ats_evaluation_id
    }
```

### Database
```sql
-- Create ats_evaluations table if not exists
INSERT INTO ats_evaluations (resume_version_id, results, overall_score) VALUES (...);
INSERT INTO explanations (resume_version_id, explanation_text, deterministic_signals) VALUES (...);
```

### 🧠 AI Usage
**Interpretation & Wording**
- Skill: `explain_ats_risk`
- Deterministic engine decides pass/fail
- AI explains what it means and how to fix

### Endpoints
- `GET /v1/resumes/{id}/ats-analysis` - Get full ATS analysis

---

## 9️⃣ JOB DESCRIPTION MATCHING

### Frontend
```typescript
// User pastes job description
const matchAnalysis = await fetch('/api/v1/jobs/analyze', {
  method: 'POST',
  body: JSON.stringify({
    job_description: jdText,
    resume_id: resumeId
  })
})

// Display matched vs missing requirements
renderMatchResults(matchAnalysis)
```

### Backend
```python
@router.post("/v1/jobs/analyze")
async def analyze_job_match(
    request: JobMatchRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    # 1. Save job description
    job_id = job_repo.create_job(user_id, request.job_description)
    
    # 2. Extract required skills (deterministic + AI)
    required_skills = extract_required_skills(request.job_description)
    job_repo.save_skill_requirements(job_id, required_skills)
    
    # 3. Compare with resume skills
    resume = resume_repo.get_full_resume(request.resume_id)
    skill_gaps = calculate_skill_gaps(resume.skills, required_skills)
    
    # 4. Save skill gaps
    for gap in skill_gaps:
        skill_gap_repo.create(user_id, job_id, gap)
    
    # 5. Call AI for reasoning
    reasoning_response = await orchestrator.execute_skill(
        skill_name="explain_skill_gaps",
        input_data={
            "job_description": request.job_description,
            "resume_skills": resume.skills,
            "identified_gaps": skill_gaps
        },
        metadata=AIRequestMetadata(user_id=user_id, skill_name="explain_skill_gaps")
    )
    
    # 6. Calculate ATS score using RPC
    ats_score = resume_repo.calculate_ats_score(resume.version_id, job_id)
    
    return {
        "job_id": job_id,
        "match_score": calculate_match_score(skill_gaps),
        "ats_score": ats_score,
        "matched_skills": [s for s in resume.skills if s not in skill_gaps],
        "missing_skills": skill_gaps,
        "reasoning": reasoning_response.structured_output,
        "suggestions": reasoning_response.structured_output["prioritized_actions"]
    }
```

### Database
```sql
INSERT INTO job_descriptions (user_id, title, description) VALUES (...);
INSERT INTO job_skill_requirements (job_id, skill_id, minimum_proficiency) VALUES (...);
INSERT INTO skill_gaps (user_id, job_id, skill_id, gap_severity) VALUES (...);

-- Use RPC for ATS calculation
SELECT calculate_ats_score($resume_version_id, $job_id);
```

### 🧠 AI Usage
**Explain Gaps & Prioritization**
- Skill: `explain_skill_gaps`
- Deterministic: Which skills are missing
- AI: Why they matter, how to address, priority order
- No false guarantees

### Endpoints
- `POST /v1/jobs/analyze` - Analyze job-resume match
- `GET /v1/jobs/{id}/gaps` - Get skill gaps
- `GET /v1/jobs/{id}/suggestions` - Get improvement suggestions

---

## 🔟 CAREER COPILOT CHAT

### Frontend
```typescript
// Context-aware chat interface
async function sendChatMessage(message: string) {
  const response = await fetch('/api/v1/copilot/chat', {
    method: 'POST',
    body: JSON.stringify({
      message: message,
      context: {
        resume_id: currentResumeId,
        recent_jobs: recentJobSearches
      }
    })
  })
  
  return response.json()
}
```

### Backend
```python
@router.post("/v1/copilot/chat")
async def copilot_chat(
    request: CopilotChatRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    # 1. Gather context
    context = await gather_user_context(
        user_id=user_id,
        resume_id=request.context.get("resume_id"),
        recent_jobs=request.context.get("recent_jobs", [])
    )
    
    # 2. Route to appropriate AI skill
    response = await orchestrator.execute_skill(
        skill_name="career_advisor",
        input_data={
            "user_question": request.message,
            "user_profile": context.profile,
            "resume_summary": context.resume_summary,
            "skill_gaps": context.skill_gaps,
            "market_context": context.market_data
        },
        metadata=AIRequestMetadata(
            user_id=user_id,
            skill_name="career_advisor",
            trace_id=f"chat-{uuid4()}"
        )
    )
    
    # 3. Validate tone & safety
    if not response.safety_check_passed:
        logger.warning(f"Unsafe chat response for user {user_id}")
        return {"message": "I need to rephrase that. Let me try again."}
    
    # 4. Return structured response
    return {
        "message": response.structured_output["response_text"],
        "suggestions": response.structured_output.get("action_items", []),
        "confidence": response.confidence_score,
        "sources": response.structured_output.get("sources", []),
        "request_id": response.request_id
    }
```

### 🧠 AI Usage
**Highest-Level Reasoning**
- Skill: `career_advisor`
- Strong guardrails on tone
- No guarantees or predictions
- Calm, professional advice only
- Always link to deterministic data

### Endpoints
- `POST /v1/copilot/chat` - Send message, get advice
- `GET /v1/copilot/history` - Get chat history (optional)

---

## 1️⃣1️⃣ EXPORT (PDF / DOCX)

### Frontend
```typescript
// Show export checklist first
const checklist = await fetch(`/api/v1/resumes/${resumeId}/export-checklist`)

if (checklist.all_passed) {
  // Generate PDF/DOCX
  const file = await fetch(`/api/v1/resumes/${resumeId}/export?format=pdf`)
  downloadFile(file)
}
```

### Backend
```python
@router.get("/v1/resumes/{resume_id}/export-checklist")
async def export_checklist(
    resume_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    resume = resume_repo.get_full_resume(resume_id)
    
    # Run deterministic checks
    checks = [
        check_contact_info_present(resume),
        check_no_template_placeholders(resume),
        check_bullet_lengths(resume),
        check_date_formatting(resume),
        check_ats_compatibility(resume)
    ]
    
    return {
        "checks": checks,
        "all_passed": all(c.passed for c in checks),
        "warnings": [c for c in checks if not c.passed]
    }

@router.get("/v1/resumes/{resume_id}/export")
async def export_resume(
    resume_id: UUID,
    format: str = "pdf",  # or "docx"
    user_id: UUID = Depends(get_current_user_id)
):
    # 1. Get resume
    resume = resume_repo.get_full_resume(resume_id)
    
    # 2. Validate ATS safety
    if not validate_export_ready(resume):
        raise HTTPException(400, "Resume not ready for export")
    
    # 3. Generate file (deterministic)
    if format == "pdf":
        file_data = generate_pdf(resume)
    else:
        file_data = generate_docx(resume)
    
    # 4. Save export metadata
    export_repo.save_export(resume_id, format)
    
    return StreamingResponse(
        io.BytesIO(file_data),
        media_type="application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=resume.{format}"}
    )
```

### 🧠 AI Usage
**NONE** - Export must be deterministic and reliable.

### Endpoints
- `GET /v1/resumes/{id}/export-checklist` - Pre-export validation
- `GET /v1/resumes/{id}/export?format=pdf` - Download PDF
- `GET /v1/resumes/{id}/export?format=docx` - Download DOCX

---

## 🔁 AI Skills Summary

### Skills Created (Add to migration 20250101000005_additional_prompts.sql)

1. **improve_bullet** - Suggest bullet improvements
2. **explain_bullet_strength** - Explain bullet quality
3. **summarize_section_quality** - Summarize heatmap scores
4. **recommend_template** - Recommend templates
5. **explain_ats_risk** - Explain ATS warnings
6. **explain_skill_gaps** - Explain missing skills
7. **career_advisor** - Career copilot chat

### Existing Skills (from 20250101000004_seed_prompts.sql)

1. **analyze_resume** - Comprehensive analysis
2. **generate_bullets** - STAR-format generation
3. **extract_skills** - Skill extraction
4. **match_job** - Job matching
5. **optimize_summary** - Summary optimization

---

## 🏗️ BUILD ORDER (CRITICAL)

### Phase 1: Foundation (Week 1-2)
1. ✅ Auth + RLS (already done)
2. ✅ Database schema (already done)
3. 🔲 Resume upload endpoint
4. 🔲 Resume parser service
5. 🔲 Resume editor CRUD

### Phase 2: AI Integration (Week 3-4)
1. 🔲 Bullet improvement (skill: improve_bullet)
2. 🔲 Bullet explanation (skill: explain_bullet_strength)
3. 🔲 Add feedback collection
4. 🔲 Test with 10 users

### Phase 3: Explainability (Week 5-6)
1. 🔲 Resume heatmap (deterministic + AI summary)
2. 🔲 ATS analysis (deterministic checks + AI explanations)
3. 🔲 Export with validation

### Phase 4: Job Matching (Week 7-8)
1. 🔲 JD parsing and storage
2. 🔲 Skill gap calculation (deterministic)
3. 🔲 AI reasoning for gaps (skill: explain_skill_gaps)

### Phase 5: Advanced Features (Week 9-10)
1. 🔲 Template recommendation (skill: recommend_template)
2. 🔲 Career copilot chat (skill: career_advisor)
3. 🔲 Dashboard with analytics

### Phase 6: Auto-Improvement (Week 11-12)
1. 🔲 Collect 1000+ evaluations
2. 🔲 Generate first prompt candidate
3. 🔲 Run A/B test
4. 🔲 Deploy improved prompt

---

## 🔒 Safety Guarantees

### What AI NEVER Does
1. ❌ Decides outcomes (scores, matches, readiness)
2. ❌ Writes directly to database
3. ❌ Makes guarantees or predictions
4. ❌ Runs in real-time self-improvement
5. ❌ Modifies production prompts

### What AI ONLY Does
1. ✅ Interprets signals
2. ✅ Improves language
3. ✅ Provides reasoning
4. ✅ Generates explanations
5. ✅ Suggests actions

### Every AI Call
1. ✅ Logged to ai_requests
2. ✅ Validated before return
3. ✅ Safety-checked
4. ✅ Has confidence score
5. ✅ Linked to deterministic signals
6. ✅ User can provide feedback

---

## 📊 Success Metrics

### Technical
- **Latency**: < 3s per AI call
- **Validation Rate**: > 95%
- **Safety**: 100% pass
- **Uptime**: 99.9%

### Business
- **User Satisfaction**: > 4.0/5.0
- **Feature Adoption**: > 80% try AI features
- **Trust Score**: > 85% trust AI suggestions
- **Cost**: < $0.10 per user per session

### AI Quality
- **Prompt Success Rate**: > 90%
- **Weekly Improvement**: +2-5% quality
- **False Positives**: < 5%
- **User Corrections**: < 10%

---

## 🎯 Next Steps

1. **Review this spec** with frontend team
2. **Create endpoint stubs** for all routes
3. **Implement Phase 1** (foundation)
4. **Test auth + RLS** thoroughly
5. **Begin Phase 2** (AI integration)

**Questions?** Check:
- [Supabase Setup](supabase/README.md)
- [Integration Guide](supabase/INTEGRATION_GUIDE.md)
- [Quick Reference](QUICK_REFERENCE.md)
