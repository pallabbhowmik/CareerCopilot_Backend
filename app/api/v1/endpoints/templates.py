from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
import os
from app.db.session import get_db
from app.models.all_models import Template

router = APIRouter()

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
                        category=data['category'],
                        config_json=data,
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
def get_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
