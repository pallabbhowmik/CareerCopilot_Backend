import json
import os
from typing import List, Dict, Any
from app.core.config import settings

# OpenAI client
try:
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
except ImportError:
    client = None

class AIService:
    def __init__(self):
        self.client = client
        self.model = "gpt-4o-mini"  # Cost-effective model

    async def extract_resume_info(self, text: str) -> Dict[str, Any]:
        """
        Uses LLM to extract structured data from resume text.
        """
        if not self.client:
            # Return mock data if OpenAI not configured
            return self._mock_resume_extraction(text)
        
        prompt = f"""
You are a resume parser. Extract the following information from the resume text and return ONLY valid JSON.

Extract:
1. Personal Info: name, email, phone, linkedin, location, website
2. Summary: professional summary or objective (if present)
3. Skills: array of technical and soft skills
4. Experience: array of jobs with:
   - company (string)
   - role (string)
   - start_date (string, format: "YYYY-MM" or "Month YYYY")
   - end_date (string or "Present")
   - location (string, optional)
   - bullets (array of achievement/responsibility strings)
   - is_current (boolean)
5. Education: array with institution, degree, field, dates, gpa, location
6. Projects: array with name, description, tech_stack, bullets
7. Certifications: array of strings
8. Languages: array of strings

Return ONLY the JSON object, no markdown formatting, no explanations.

Resume Text:
{text[:4000]}

JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise resume parser that outputs only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._mock_resume_extraction(text)

    async def analyze_job_match(self, resume_json: Dict, job_desc: str) -> Dict[str, Any]:
        """
        Compares resume JSON against Job Description text.
        Returns gap analysis and recommendations.
        """
        if not self.client:
            return self._mock_job_match()
        
        prompt = f"""
You are a career advisor analyzing job fit. Compare the resume against this job description.

Resume Summary:
- Skills: {', '.join(resume_json.get('skills', [])[:20])}
- Experience: {len(resume_json.get('experience', []))} roles
- Latest Role: {resume_json.get('experience', [{}])[0].get('role', 'N/A') if resume_json.get('experience') else 'N/A'}

Job Description:
{job_desc[:2000]}

Return JSON with:
{{
  "match_score": <0-100>,
  "matching_skills": [<skills from resume that match JD>],
  "missing_skills": [<skills in JD not in resume>],
  "experience_fit": "<brief analysis of experience level fit>",
  "recommendations": [<3-5 specific actionable suggestions>],
  "confidence": "<high/medium/low>"
}}

JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a career advisor providing honest, constructive feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._mock_job_match()

    async def improve_bullet_point(self, bullet: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rewrites a bullet point to be more impactful.
        Returns improved version with explanation.
        """
        if not self.client:
            return {
                "original": bullet,
                "improved": bullet,
                "explanation": "OpenAI API not configured",
                "score_before": 50,
                "score_after": 50
            }
        
        prompt = f"""
You are a professional resume writer. Improve this bullet point to be more impactful.

Original Bullet:
"{bullet}"

Context:
- Role: {context.get('role', 'Unknown')}
- Company: {context.get('company', 'Unknown')}

Make it:
1. Start with a strong action verb
2. Include specific metrics/numbers if possible
3. Show impact/results
4. Be concise (1-2 lines)
5. Use past tense (unless current role)

Return JSON:
{{
  "improved": "<improved bullet point>",
  "explanation": "<brief explanation of changes>",
  "score_before": <0-100>,
  "score_after": <0-100>,
  "improvements": ["<specific improvement 1>", "<improvement 2>"]
}}

JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a resume writing expert who improves bullet points."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["original"] = bullet
            return result
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {
                "original": bullet,
                "improved": bullet,
                "explanation": f"Error: {str(e)}",
                "score_before": 50,
                "score_after": 50
            }

    async def generate_career_advice(self, user_context: Dict[str, Any], question: str) -> str:
        """
        Career Copilot Chat - context-aware conversational AI.
        """
        if not self.client:
            return "I'm sorry, I need an OpenAI API key configured to provide personalized career advice."
        
        system_prompt = f"""
You are CareerCopilot, a calm, trustworthy, and intelligent career advisor.

User Context:
- Target Role: {user_context.get('target_role', 'Not specified')}
- Experience Level: {user_context.get('experience_level', 'Not specified')}
- Location: {user_context.get('country', 'Not specified')}
- Career Goal: {user_context.get('career_goal', 'Not specified')}

Guidelines:
- Be honest and realistic, not overly optimistic
- Provide specific, actionable advice
- Explain your reasoning
- Use simple, clear language
- Be encouraging but truthful
- Focus on what the user can control
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"I apologize, I'm experiencing technical difficulties: {str(e)}"

    def _mock_resume_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback mock data when OpenAI is not available."""
        return {
            "name": "Sample User",
            "email": "user@example.com",
            "phone": "",
            "linkedin": "",
            "location": "",
            "website": "",
            "summary": "Experienced professional seeking new opportunities.",
            "skills": ["Python", "JavaScript", "Problem Solving", "Communication"],
            "experience": [
                {
                    "company": "Tech Company",
                    "role": "Software Engineer",
                    "start_date": "2020-01",
                    "end_date": "Present",
                    "location": "Remote",
                    "bullets": [
                        "Developed web applications",
                        "Collaborated with cross-functional teams"
                    ],
                    "is_current": True
                }
            ],
            "education": [
                {
                    "institution": "University",
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "start_date": "2016",
                    "end_date": "2020",
                    "gpa": "",
                    "location": ""
                }
            ],
            "projects": [],
            "certifications": [],
            "languages": ["English"]
        }

    def _mock_job_match(self) -> Dict[str, Any]:
        """Fallback mock data for job matching."""
        return {
            "match_score": 75,
            "matching_skills": ["Python", "JavaScript"],
            "missing_skills": ["Docker", "Kubernetes"],
            "experience_fit": "Your experience level appears to match the job requirements.",
            "recommendations": [
                "Consider adding containerization skills to your resume",
                "Highlight relevant project experience",
                "Tailor your summary to match job description keywords"
            ],
            "confidence": "medium"
        }

ai_service = AIService()

