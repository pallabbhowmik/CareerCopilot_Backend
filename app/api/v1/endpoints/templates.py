from fastapi import APIRouter, HTTPException
from typing import List, Optional, Any
from pydantic import BaseModel
from uuid import UUID, uuid4
import json

router = APIRouter()

class TemplateResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_ats_safe: bool = True
    recommended_for: List[str] = []
    config_json: Optional[Any] = None
    preview_image_url: Optional[str] = None

# In-memory templates (no database required)
TEMPLATES = [
    {
        "id": str(uuid4()),
        "name": "Modern Professional",
        "slug": "modern-professional",
        "category": "Software Engineering",
        "description": "Clean, ATS-safe template ideal for software engineers and tech professionals",
        "is_ats_safe": True,
        "recommended_for": ["software engineer", "developer", "tech"],
        "config_json": {
            "font_family": "Inter",
            "font_size": 11,
            "line_height": 1.5,
            "margins": {"top": 0.5, "bottom": 0.5, "left": 0.75, "right": 0.75},
            "section_spacing": 0.15,
            "colors": {"primary": "#1a1a1a", "secondary": "#666666"},
        },
        "preview_image_url": None,
    },
    {
        "id": str(uuid4()),
        "name": "Executive Classic",
        "slug": "executive-classic",
        "category": "Management",
        "description": "Traditional format for senior roles and executive positions",
        "is_ats_safe": True,
        "recommended_for": ["manager", "director", "executive", "senior"],
        "config_json": {
            "font_family": "Georgia",
            "font_size": 11,
            "line_height": 1.6,
            "margins": {"top": 0.75, "bottom": 0.75, "left": 1, "right": 1},
            "section_spacing": 0.2,
            "colors": {"primary": "#000000", "secondary": "#555555"},
        },
        "preview_image_url": None,
    },
    {
        "id": str(uuid4()),
        "name": "Data Analyst",
        "slug": "data-analyst",
        "category": "Data Science",
        "description": "Optimized for data roles with emphasis on metrics and technical skills",
        "is_ats_safe": True,
        "recommended_for": ["data analyst", "data scientist", "analytics"],
        "config_json": {
            "font_family": "Arial",
            "font_size": 10.5,
            "line_height": 1.4,
            "margins": {"top": 0.6, "bottom": 0.6, "left": 0.75, "right": 0.75},
            "section_spacing": 0.15,
            "colors": {"primary": "#2c3e50", "secondary": "#7f8c8d"},
        },
        "preview_image_url": None,
    },
    {
        "id": str(uuid4()),
        "name": "Simple ATS-Safe",
        "slug": "simple-ats",
        "category": "General",
        "description": "Maximally ATS-compatible format with zero styling risks",
        "is_ats_safe": True,
        "recommended_for": ["entry level", "fresher", "any role"],
        "config_json": {
            "font_family": "Arial",
            "font_size": 11,
            "line_height": 1.5,
            "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1},
            "section_spacing": 0.2,
            "colors": {"primary": "#000000", "secondary": "#000000"},
        },
        "preview_image_url": None,
    },
]

@router.get("/", response_model=List[TemplateResponse])
def get_templates():
    """Get all available templates."""
    return TEMPLATES

@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(template_id: str):
    """Get a specific template by ID."""
    template = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

class RecommendationRequest(BaseModel):
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    country: Optional[str] = None

@router.post("/recommend", response_model=List[TemplateResponse])
def get_template_recommendations(request: RecommendationRequest):
    """Get AI-recommended templates based on user context."""
    role = (request.target_role or "").lower()
    experience = (request.experience_level or "").lower()
    
    # Score each template
    scored = []
    for t in TEMPLATES:
        score = 0
        recommended_for = [rf.lower() for rf in t.get("recommended_for", [])]
        category = (t.get("category") or "").lower()
        
        # Match by role keywords
        for keyword in ["software", "developer", "engineer", "tech"]:
            if keyword in role and (keyword in category or any(keyword in rf for rf in recommended_for)):
                score += 30
                break
        
        for keyword in ["data", "analyst", "analytics"]:
            if keyword in role and (keyword in category or any(keyword in rf for rf in recommended_for)):
                score += 30
                break
        
        for keyword in ["product", "manager", "management"]:
            if keyword in role and (keyword in category or any(keyword in rf for rf in recommended_for)):
                score += 30
                break
        
        # Match by experience level
        if any(kw in experience for kw in ["fresher", "entry", "0-2", "junior"]):
            if any(kw in rf for kw in ["entry", "fresher", "any"] for rf in recommended_for):
                score += 20
        elif any(kw in experience for kw in ["senior", "6+", "lead", "principal"]):
            if any(kw in rf for kw in ["senior", "executive", "director"] for rf in recommended_for):
                score += 20
        
        # ATS-safe bonus
        if t.get("is_ats_safe"):
            score += 10
        
        scored.append((t, score))
    
    # Sort by score and return top 3
    scored.sort(key=lambda x: x[1], reverse=True)
    top_templates = [t for t, _ in scored[:3]]
    
    return top_templates
