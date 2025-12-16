from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.resume_parser import parse_resume_file
from app.models.all_models import Resume

router = APIRouter()

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # 1. Save file (mock)
    # 2. Parse file
    parsed_data = await parse_resume_file(file)
    
    # 3. Save to DB (mock user_id 1)
    db_resume = Resume(
        user_id=1,
        title=file.filename,
        content_structured=parsed_data,
        file_path=f"uploads/{file.filename}"
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    
    return db_resume

@router.get("/")
def get_resumes(db: Session = Depends(get_db)):
    return db.query(Resume).filter(Resume.user_id == 1).all()
