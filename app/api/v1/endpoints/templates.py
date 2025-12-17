from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict
from uuid import UUID
import json
import os
from app.db.session import get_db
from app.models.all_models import Template

router = APIRouter()

class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    slug: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_ats_safe: bool = True
    recommended_for: List[str] = []
    config_json: Optional[Any] = None


# Helper to load initial templates
def load_initial_templates(db: Session):
    template_dir = "app/data/templates"
    if not os.path.exists(template_dir):
        return

    for filename in os.listdir(template_dir):
        if filename.endswith(".json"):
            with open(os.path.join(template_dir, filename), 'r') as f:
                data = json.load(f)
                # Check if exists
                existing = db.query(Template).filter(Template.name == data['name']).first()
                if not existing:
                    db_template = Template(
                        name=data['name'],
                        slug=data.get('slug', data['name'].lower().replace(' ', '-')),
                        category=data.get('category', 'General'),
                        description=data.get('description', ''),
                        config_json=data,
                        is_ats_safe=data.get('is_ats_safe', True),
                        is_active=True,
                        recommended_for=data.get('recommended_for', []),
                        preview_image_url=f"/static/templates/{filename.replace('.json', '.png')}"
                    )
                    db.add(db_template)
    db.commit()

@router.get("/")
def get_templates(db: Session = Depends(get_db)):
    # Auto-load for demo purposes
    load_initial_templates(db)
    return db.query(Template).filter(Template.is_active == True).all()

@router.get("/{template_id}")
def get_template(template_id: UUID, db: Session = Depends(get_db)):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

class RecommendationRequest(BaseModel):
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    country: Optional[str] = None

@router.post("/recommend")
def get_template_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db)
):
    """Get AI-recommended templates based on user context."""
    # Load all templates
    load_initial_templates(db)
    templates = db.query(Template).filter(Template.is_active == True).all()
    
    if not templates:
        return []
    
    # Simple recommendation logic based on role/experience
    role = (request.target_role or "").lower()
    experience = (request.experience_level or "").lower()
    
    # Score each template
    scored = []
    for t in templates:
        score = 0
        recommended_for = t.config_json.get("recommended_for", []) if t.config_json else []
        category = (t.category or "").lower()
        
        # Match by category keywords
        if "software" in role or "developer" in role or "engineer" in role:
            if "software" in category or "tech" in category:
                score += 30
        elif "data" in role or "analyst" in role:
            if "data" in category:
                score += 30
        elif "product" in role or "manager" in role:
            if "product" in category or "management" in category:
                score += 30
        elif "design" in role:
            if "design" in category:
                score += 30
        
        # Match by experience level
        if "fresher" in experience or "entry" in experience or "0-2" in experience:
            if "fresher" in str(recommended_for).lower() or "entry" in str(recommended_for).lower():
                score += 20
        elif "senior" in experience or "6+" in experience:
            if "senior" in str(recommended_for).lower() or "executive" in category:
                score += 20
        
        # ATS-safe templates get a bonus
        if t.is_ats_safe:
            score += 10
        
        scored.append((t, score))
    
    # Sort by score and return top 3
    scored.sort(key=lambda x: x[1], reverse=True)
    top_templates = [t for t, _ in scored[:3]]
    
    return top_templates
