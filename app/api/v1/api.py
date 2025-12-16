from fastapi import APIRouter
from app.api.v1.endpoints import auth, resumes, jobs, analysis, templates, analytics, chat, applications

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])


