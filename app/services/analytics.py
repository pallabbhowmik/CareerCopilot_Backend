from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.all_models import Application, Resume

class AnalyticsService:
    def __init__(self):
        pass

    def get_user_stats(self, db: Session, user_id: int):
        """
        Get application stats for a user.
        """
        total_applications = db.query(Application).filter(Application.user_id == user_id).count()
        interviews = db.query(Application).filter(Application.user_id == user_id, Application.status == "interview").count()
        offers = db.query(Application).filter(Application.user_id == user_id, Application.status == "offer").count()
        
        return {
            "total_applications": total_applications,
            "interviews": interviews,
            "offers": offers,
            "conversion_rate": (interviews / total_applications * 100) if total_applications > 0 else 0
        }

    def get_ab_test_results(self, db: Session, user_id: int):
        """
        Compare performance of different resume variants.
        """
        # Group by resume_id (or variant_group_id if implemented fully)
        results = db.query(
            Resume.title,
            func.count(Application.id).label("apps"),
            func.sum(func.case((Application.status == 'interview', 1), else_=0)).label("interviews")
        ).join(Application).filter(Resume.user_id == user_id).group_by(Resume.id).all()
        
        return [
            {
                "resume_title": r.title,
                "applications": r.apps,
                "interviews": r.interviews,
                "success_rate": (r.interviews / r.apps * 100) if r.apps > 0 else 0
            }
            for r in results
        ]

analytics_service = AnalyticsService()
