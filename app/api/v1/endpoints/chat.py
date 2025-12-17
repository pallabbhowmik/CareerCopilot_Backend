from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.all_models import UserProfile
from app.api.v1.endpoints.auth import get_current_user
from app.services.llm_engine import ai_service

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []

class ChatResponse(BaseModel):
    response: str
    suggestions: list = []

@router.post("/chat", response_model=ChatResponse)
async def career_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Career Copilot Chat - context-aware career advice.
    """
    user_context = {
        "target_role": current_user.target_role,
        "experience_level": current_user.experience_level,
        "country": current_user.country,
        "career_goal": current_user.career_goal
    }
    
    response = await ai_service.generate_career_advice(user_context, request.message)
    
    # Generate follow-up suggestions based on context
    suggestions = []
    if "resume" in request.message.lower():
        suggestions.append("Can you review my resume's ATS readiness?")
        suggestions.append("How can I improve my bullet points?")
    elif "interview" in request.message.lower():
        suggestions.append("What are common interview questions for my role?")
        suggestions.append("How should I prepare for behavioral interviews?")
    elif "career" in request.message.lower() or "switch" in request.message.lower():
        suggestions.append("What skills should I learn for this transition?")
        suggestions.append("How long does a career switch typically take?")
    else:
        suggestions.append("How can I improve my resume?")
        suggestions.append("What's my biggest career challenge right now?")
    
    return ChatResponse(
        response=response,
        suggestions=suggestions[:3]
    )
