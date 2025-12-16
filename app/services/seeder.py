from sqlalchemy.orm import Session
import json
import os
from app.models.all_models import Template

def seed_templates(db: Session):
    """
    Seeds the database with initial templates from the data directory.
    """
    # Adjust path to be relative to the running application
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "templates")
    
    if not os.path.exists(template_dir):
        print(f"Template directory not found: {template_dir}")
        return

    print(f"Seeding templates from: {template_dir}")
    
    for filename in os.listdir(template_dir):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(template_dir, filename), 'r') as f:
                    data = json.load(f)
                    # Check if exists
                    existing = db.query(Template).filter(Template.name == data['name']).first()
                    if not existing:
                        print(f"Creating template: {data['name']}")
                        db_template = Template(
                            name=data['name'],
                            category=data['category'],
                            config_json=data,
                            preview_image_url=f"/static/templates/{filename.replace('.json', '.png')}"
                        )
                        db.add(db_template)
                    else:
                        print(f"Template already exists: {data['name']}")
            except Exception as e:
                print(f"Error seeding {filename}: {e}")
                
    db.commit()
