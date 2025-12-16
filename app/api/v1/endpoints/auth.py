from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
# In a real app, implement actual JWT logic here

router = APIRouter()

@router.post("/login")
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    # Mock login
    if form_data.username == "test@example.com" and form_data.password == "password":
        return {"access_token": "fake-jwt-token", "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect email or password")

@router.post("/signup")
def signup():
    return {"msg": "Signup endpoint"}
