from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.models.all_models import Template

class TemplateRecommendationEngine:
    """
    AI-powered template recommendation based on user context.
    Always recommend top 3 templates. Never leave users with blank slate.
    """
    
    def recommend_templates(
        self,
        db: Session,
        target_role: str,
        experience_level: str,
        country: str
    ) -> List[Dict[str, Any]]:
        """
        Returns top 3 recommended templates with reasoning.
        """
        all_templates = db.query(Template).filter(Template.is_active == True).all()
        
        scored_templates = []
        for template in all_templates:
            score = self._calculate_match_score(
                template,
                target_role,
                experience_level,
                country
            )
            scored_templates.append({
                "template": template,
                "score": score,
                "reasoning": self._generate_reasoning(template, target_role, experience_level)
            })
        
        # Sort by score and return top 3
        scored_templates.sort(key=lambda x: x["score"], reverse=True)
        return scored_templates[:3]
    
    def _calculate_match_score(
        self,
        template: Template,
        target_role: str,
        experience_level: str,
        country: str
    ) -> int:
        """
        Scoring logic based on user context.
        """
        score = 50  # Base score
        
        config = template.config_json
        
        # Role matching
        if target_role.lower() in [r.lower() for r in config.get("target_roles", [])]:
            score += 30
        
        # Experience level
        if experience_level == "Fresher" and template.category == "Fresher":
            score += 25
        elif experience_level in ["Mid-Level", "Senior"] and template.category in ["Developer", "Management"]:
            score += 20
        
        # Country-specific rules
        if country in ["US", "CA", "UK"] and config.get("regional_rules", {}).get("no_photo"):
            score += 15
        
        # ATS score
        score += config.get("ats_score", 0) // 5
        
        return min(score, 100)
    
    def _generate_reasoning(
        self,
        template: Template,
        target_role: str,
        experience_level: str
    ) -> str:
        """
        Human-readable explanation for why this template was recommended.
        """
        config = template.config_json
        
        reasons = []
        
        if target_role.lower() in [r.lower() for r in config.get("target_roles", [])]:
            reasons.append(f"Optimized for {target_role} roles")
        
        if config.get("ats_score", 0) >= 95:
            reasons.append("Highest ATS compatibility")
        
        if template.category == "Fresher" and experience_level == "Fresher":
            reasons.append("Designed for fresh graduates")
        
        return " • ".join(reasons) if reasons else "Versatile and reliable"

template_recommender = TemplateRecommendationEngine()
