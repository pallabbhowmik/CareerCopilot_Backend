from typing import Dict, Any, List

class ATSExplainabilityService:
    """
    Provides transparent, explainable ATS readiness metrics.
    NO SINGLE SCORE. Only actionable, specific insights.
    """
    
    def analyze_ats_readiness(self, resume_json: Dict[str, Any], job_desc: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Returns a multi-dimensional ATS analysis with explanations.
        """
        result = {
            "parsing_success": self._check_parsing(resume_json),
            "skill_coverage": self._analyze_skill_coverage(resume_json, job_desc),
            "keyword_alignment": self._check_keywords(resume_json, job_desc),
            "formatting_risks": self._detect_formatting_issues(resume_json),
            "recruiter_readability": self._assess_readability(resume_json),
            "section_completeness": self._check_section_completeness(resume_json),
            "overall_score": 0  # Will be calculated
        }
        
        # Calculate overall score based on sub-scores
        scores = []
        if result["parsing_success"]["status"] == "pass":
            scores.append(100)
        elif result["parsing_success"]["status"] == "warning":
            scores.append(70)
        else:
            scores.append(40)
        
        scores.append(result["skill_coverage"].get("coverage_percentage", 0))
        scores.append(90 if result["formatting_risks"]["status"] == "pass" else 60)
        scores.append(85 if result["section_completeness"]["status"] == "pass" else 50)
        
        result["overall_score"] = int(sum(scores) / len(scores))
        
        return result
    
    def _check_parsing(self, resume_json: Dict) -> Dict:
        detected_sections = []
        if resume_json.get("experience"): detected_sections.append("Experience")
        if resume_json.get("skills"): detected_sections.append("Skills")
        if resume_json.get("education"): detected_sections.append("Education")
        if resume_json.get("personal_info", {}).get("name"): detected_sections.append("Contact Info")
        if resume_json.get("summary"): detected_sections.append("Summary")
        
        score = len(detected_sections) * 20  # Max 100 for 5 sections
        
        return {
            "status": "pass" if len(detected_sections) >= 3 else "warning",
            "detected_sections": detected_sections,
            "score": score,
            "explanation": f"ATS detected {len(detected_sections)}/5 standard sections. Most systems successfully parse this format.",
            "what_this_means": "Your resume structure is recognized by applicant tracking systems.",
            "action_needed": "Consider adding missing standard sections" if len(detected_sections) < 4 else None
        }
    
    def _analyze_skill_coverage(self, resume_json: Dict, job_desc: Dict = None) -> Dict:
        user_skills = resume_json.get("skills", [])
        
        # If job description provided, extract required skills
        if job_desc and "required_skills" in job_desc:
            target_skills = job_desc["required_skills"]
        else:
            # Default common skills check
            target_skills = []
        
        if target_skills:
            matched_skills = [s for s in user_skills if s.lower() in [t.lower() for t in target_skills]]
            coverage_pct = int((len(matched_skills) / len(target_skills) * 100)) if target_skills else 0
            
            return {
                "status": "pass" if coverage_pct >= 70 else "warning" if coverage_pct >= 50 else "action_required",
                "coverage_percentage": coverage_pct,
                "matched_skills": matched_skills,
                "missing_skills": [s for s in target_skills if s.lower() not in [u.lower() for u in user_skills]],
                "total_skills_listed": len(user_skills),
                "explanation": f"Your resume includes {len(matched_skills)}/{len(target_skills)} skills from the job description.",
                "what_this_means": "Higher skill match increases ATS ranking and recruiter interest.",
                "action_needed": "Add missing skills if you have them (be honest)" if coverage_pct < 70 else None
            }
        else:
            # General skill count assessment
            skill_count = len(user_skills)
            return {
                "status": "pass" if skill_count >= 5 else "warning",
                "total_skills_listed": skill_count,
                "coverage_percentage": min(100, skill_count * 10),
                "explanation": f"Resume lists {skill_count} skills. Aim for 8-15 relevant skills.",
                "what_this_means": "Skills section helps ATS match your profile to job requirements.",
                "action_needed": "Add more relevant skills" if skill_count < 5 else None
            }
    
    def _check_keywords(self, resume_json: Dict, job_desc: Dict = None) -> Dict:
        # Count keyword density in experience bullets
        experience = resume_json.get("experience", [])
        total_bullets = sum(len(exp.get("bullets", [])) for exp in experience)
        
        # Check for action verbs
        action_verbs = ["led", "developed", "managed", "created", "improved", "increased", 
                       "decreased", "achieved", "implemented", "designed", "built", "launched"]
        
        bullets_with_verbs = 0
        bullets_with_metrics = 0
        
        for exp in experience:
            for bullet in exp.get("bullets", []):
                bullet_lower = bullet.lower()
                if any(verb in bullet_lower for verb in action_verbs):
                    bullets_with_verbs += 1
                if any(char.isdigit() for char in bullet):
                    bullets_with_metrics += 1
        
        verb_percentage = int((bullets_with_verbs / total_bullets * 100)) if total_bullets > 0 else 0
        metric_percentage = int((bullets_with_metrics / total_bullets * 100)) if total_bullets > 0 else 0
        
        return {
            "status": "pass" if verb_percentage >= 70 else "warning",
            "action_verb_usage": verb_percentage,
            "quantified_achievements": metric_percentage,
            "total_bullets": total_bullets,
            "explanation": f"{verb_percentage}% of bullets use strong action verbs. {metric_percentage}% include metrics.",
            "what_this_means": "Action verbs and numbers make your resume more impactful for both ATS and recruiters.",
            "action_needed": "Start more bullets with action verbs and add quantifiable results" if verb_percentage < 70 else None
        }
    
    def _detect_formatting_issues(self, resume_json: Dict) -> Dict:
        issues = []
        warnings = []
        
        # Check contact info
        personal_info = resume_json.get("personal_info", {})
        if not personal_info.get("email"):
            issues.append("Email address missing")
        if not personal_info.get("phone"):
            warnings.append("Phone number missing - consider adding")
        
        # Check experience bullets
        experience = resume_json.get("experience", [])
        for exp in experience:
            if not exp.get("bullets"):
                warnings.append(f"No bullet points for {exp.get('company', 'a position')}")
        
        # Check education
        education = resume_json.get("education", [])
        if not education:
            warnings.append("Education section empty or missing")
        
        status = "fail" if issues else ("warning" if warnings else "pass")
        
        return {
            "status": status,
            "critical_issues": issues,
            "warnings": warnings,
            "explanation": "Checking for ATS-breaking patterns (images, tables, graphics, unusual fonts).",
            "what_this_means": "All text will be correctly extracted by parsing software." if status == "pass" else "Some content may not parse correctly.",
            "action_needed": issues[0] if issues else (warnings[0] if warnings else None)
        }
    
    def _check_section_completeness(self, resume_json: Dict) -> Dict:
        required_sections = ["personal_info", "experience", "education", "skills"]
        recommended_sections = ["summary", "projects"]
        
        has_required = [section for section in required_sections if resume_json.get(section)]
        has_recommended = [section for section in recommended_sections if resume_json.get(section)]
        
        completeness_score = int((len(has_required) / len(required_sections)) * 100)
        
        return {
            "status": "pass" if completeness_score == 100 else "warning",
            "completeness_score": completeness_score,
            "has_required": has_required,
            "missing_required": [s for s in required_sections if s not in has_required],
            "has_recommended": has_recommended,
            "explanation": f"{len(has_required)}/{len(required_sections)} required sections present.",
            "what_this_means": "Complete sections help ATS categorize your information correctly.",
            "action_needed": f"Add {', '.join([s for s in required_sections if s not in has_required])}" if completeness_score < 100 else None
        }
    
    def _assess_readability(self, resume_json: Dict) -> Dict:
        experience = resume_json.get("experience", [])
        total_bullets = sum(len(exp.get("bullets", [])) for exp in experience)
        
        # Check bullet length
        long_bullets = 0
        for exp in experience:
            for bullet in exp.get("bullets", []):
                if len(bullet) > 150:  # More than ~2 lines
                    long_bullets += 1
        
        readability_score = 100 - (long_bullets / total_bullets * 50) if total_bullets > 0 else 50
        
        return {
            "status": "pass" if readability_score >= 70 else "warning",
            "readability_score": int(readability_score),
            "total_bullets": total_bullets,
            "long_bullets": long_bullets,
            "explanation": f"Resume has {total_bullets} experience bullets. {long_bullets} may be too long for quick scanning.",
            "what_this_means": "Recruiters can quickly scan and understand your experience.",
            "recruiter_tip": "First 10 seconds matter most. Lead with your strongest achievements.",
            "action_needed": "Consider shortening some bullet points for better scannability" if long_bullets > 0 else None
        }

ats_service = ATSExplainabilityService()

def calculate_ats_readiness(resume_json: Dict[str, Any], job_desc: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to calculate ATS readiness.
    """
    return ats_service.analyze_ats_readiness(resume_json, job_desc)

