import re
import json
from typing import Dict, Any, List
from fastapi import UploadFile
import PyPDF2
from docx import Document
from app.services.llm_engine import ai_service


SECTION_HEADERS = {
    "experience": ["experience", "work history", "employment", "professional experience", "work experience"],
    "education": ["education", "academic background", "academic qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "core skills", "technical competencies"],
    "projects": ["projects", "personal projects", "side projects", "portfolio"],
    "summary": ["summary", "professional summary", "objective", "profile", "about me"],
    "certifications": ["certifications", "certificates", "licenses", "credentials"],
    "languages": ["languages", "language proficiency"],
    "awards": ["awards", "honors", "achievements", "recognition"],
    "publications": ["publications", "research", "papers"],
}


def _is_heading(line: str) -> bool:
    t = (line or "").strip()
    if not t:
        return False
    low = t.lower()
    if any(low == h for group in SECTION_HEADERS.values() for h in group):
        return True
    # Common ATS headings
    if low in {"core skills", "core competencies", "professional experience", "work experience", "contact", "languages", "awards", "certifications"}:
        return True
    # All-caps short lines are usually headings
    letters = re.sub(r"[^A-Za-z]", "", t)
    if letters and t.upper() == t and len(t) <= 40:
        return True
    return False


def _clean_bullet(line: str) -> str:
    t = (line or "").strip()
    t = re.sub(r"^[\-•●◆■◦*\u2022]+\s*", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _extract_linkedin(text: str) -> str:
    m = re.search(r"(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9\-_%/]+", text, re.IGNORECASE)
    return m.group(0) if m else ""


def _extract_github(text: str) -> str:
    """Extract GitHub profile URL."""
    m = re.search(r"(https?://)?(www\.)?github\.com/[A-Za-z0-9\-_]+", text, re.IGNORECASE)
    return m.group(0) if m else ""


def _extract_website(text: str) -> str:
    m = re.search(r"(https?://)?(www\.)?[A-Za-z0-9\-]+\.[A-Za-z]{2,}(/[A-Za-z0-9\-._~:/?#[\]@!$&'()*+,;=%]*)?", text)
    if not m:
        return ""
    url = m.group(0)
    # avoid returning emails
    if "@" in url:
        return ""
    return url


def _split_lines(text: str) -> List[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln and ln.strip()]


def _extract_location(text: str) -> str:
    """Extract location from resume (city, state/country format)."""
    # Pattern: City, State/Country (e.g., "San Francisco, CA" or "Mumbai, India")
    location_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    match = re.search(location_pattern, text)
    if match:
        return match.group(0)
    return ""


def _extract_dates(line: str) -> tuple:
    """Extract start_date and end_date from a line."""
    # Patterns: "Jan 2020 - Present", "2020-2023", "January 2020 to Dec 2023"
    # Format 1: Month Year - Month Year or Present
    month_year_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})'
    matches = re.findall(month_year_pattern, line, re.IGNORECASE)
    
    if matches:
        start_date = f"{matches[0][0]} {matches[0][1]}" if matches else ""
        end_date = f"{matches[1][0]} {matches[1][1]}" if len(matches) > 1 else ""
        if not end_date and re.search(r'\bpresent\b', line, re.IGNORECASE):
            end_date = "Present"
        return (start_date, end_date)
    
    # Format 2: YYYY - YYYY or YYYY-YYYY
    year_pattern = r'(\d{4})\s*[\-–—to]+\s*(\d{4}|Present)'
    year_match = re.search(year_pattern, line, re.IGNORECASE)
    if year_match:
        return (year_match.group(1), year_match.group(2))
    
    # Format 3: Single year or "Present"
    if re.search(r'\bpresent\b', line, re.IGNORECASE):
        year_match = re.search(r'(\d{4})', line)
        if year_match:
            return (year_match.group(1), "Present")
    
    return ("", "")


def _looks_like_mock(ai_output: Dict[str, Any]) -> bool:
    try:
        name = (ai_output.get("name") or "").strip().lower()
        email = (ai_output.get("email") or "").strip().lower()
        summary = (ai_output.get("summary") or "").strip().lower()
        return (
            name in {"sample user", "john doe"}
            or email in {"user@example.com", "john@example.com"}
            or summary == "experienced professional seeking new opportunities."
        )
    except Exception:
        return False


def heuristic_extract_resume_info(raw_text: str) -> Dict[str, Any]:
    """Heuristic resume extraction from raw text (no LLM).

    Goal: produce *real* fields from the uploaded resume even when OPENAI_API_KEY is not set.
    """
    text = raw_text or ""
    lines = _split_lines(text)
    joined = "\n".join(lines)

    email = extract_email(joined)
    phone = extract_phone(joined)
    linkedin = _extract_linkedin(joined)
    github = _extract_github(joined)
    website = _extract_website(joined)
    location = _extract_location(joined)

    # Name heuristics:
    # 1) line before email
    # 2) first plausible 2-4 word alphabetic line that's not a heading
    name = ""
    if email:
        for i, ln in enumerate(lines):
            if email.lower() in ln.lower():
                # previous non-heading
                for j in range(i - 1, max(-1, i - 6), -1):
                    if j < 0:
                        break
                    cand = lines[j]
                    if _is_heading(cand):
                        continue
                    if re.search(r"\d", cand):
                        continue
                    if 2 <= len(cand.split()) <= 5:
                        name = cand.strip()
                        break
                break

    if not name:
        for ln in lines[:40]:
            if _is_heading(ln):
                continue
            if email and email.lower() in ln.lower():
                continue
            if phone and phone in ln:
                continue
            if re.search(r"\d", ln):
                continue
            words = [w for w in re.split(r"\s+", ln.strip()) if w]
            if not (2 <= len(words) <= 5):
                continue
            if not all(re.match(r"^[A-Za-z.'-]+$", w) for w in words):
                continue
            name = ln.strip()
            break

    sections = extract_sections(text)

    # Summary: extract clean professional summary, skip location/date lines
    summary = (sections.get("summary") or "").strip()
    if summary:
        # Clean up summary: remove location/date lines
        summary_lines = _split_lines(summary)
        clean_summary = []
        for ln in summary_lines:
            # Skip lines with dates like "Jan 2022" or "2022-Present"
            if re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b", ln, re.IGNORECASE):
                continue
            # Skip lines with location patterns like "City, Country |"
            if re.search(r"\w+,\s*\w+\s*\|", ln):
                continue
            # Skip very short lines (likely headers/dates)
            if len(ln) < 20:
                continue
            # Keep substantial summary lines
            if len(ln) >= 40:
                clean_summary.append(ln)
        summary = " ".join(clean_summary).strip()
    
    if not summary:
        # fallback: first ~2-3 substantial lines that look like summary
        summary_candidates: List[str] = []
        for ln in lines[:80]:
            if _is_heading(ln):
                continue
            if len(ln) < 40:
                continue
            # Skip date/location patterns
            if re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b", ln, re.IGNORECASE):
                continue
            if re.search(r"\w+,\s*\w+\s*\|", ln):
                continue
            summary_candidates.append(ln)
            if len(summary_candidates) >= 3:
                break
        summary = " ".join(summary_candidates).strip()

    # Skills
    skills_text = sections.get("skills") or ""
    skills: List[str] = []
    if skills_text:
        # split on commas/newlines/bullets
        raw_skills = re.split(r"[\n,|/]+", skills_text)
        for s in raw_skills:
            item = _clean_bullet(s)
            if not item:
                continue
            if len(item) > 40:
                continue
            skills.append(item)

    # Fallback skills: mine from 'CORE SKILLS' block if extract_sections missed it
    if not skills:
        for ln in lines:
            low = ln.lower()
            if "languages" in low and "databases" in low:
                # e.g. Languages & Databases: Java, C#, SQL
                parts = ln.split(":", 1)
                if len(parts) == 2:
                    for s in parts[1].split(","):
                        item = _clean_bullet(s)
                        if item:
                            skills.append(item)
            if low.startswith("tools") and ":" in ln:
                parts = ln.split(":", 1)
                if len(parts) == 2:
                    for s in parts[1].split(","):
                        item = _clean_bullet(s)
                        if item:
                            skills.append(item)

    # Deduplicate skills
    dedup = []
    seen = set()
    for s in skills:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(s)
    skills = dedup[:30]

    # Experience: parse by company/role with bullets
    exp_text = sections.get("experience") or ""
    experience: List[Dict[str, Any]] = []
    
    if exp_text:
        exp_lines = _split_lines(exp_text)
        current_company = ""
        current_role = ""
        current_location = ""
        current_start_date = ""
        current_end_date = ""
        current_bullets: List[str] = []
        
        action_verbs = r"\b(built|developed|led|designed|implemented|improved|reduced|increased|optimized|migrated|engineered|created|managed|coordinated|established|delivered|achieved|accelerated|innovated|integrated|automated|scaled|streamlined|enhanced)\b"
        
        for ln in exp_lines:
            # Skip headings
            if _is_heading(ln):
                continue
            
            # Check if line is a company/role header (has dates like "2022-Present" or "Jan 2022")
            has_date = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}|present)\b", ln, re.IGNORECASE)
            has_location = re.search(r"\w+,\s*\w+", ln)
            
            # If line has dates and is short-ish, likely a job header
            if has_date and len(ln) < 150:
                # Save previous job if exists
                if current_bullets:
                    experience.append({
                        "company": current_company,
                        "role": current_role,
                        "start_date": current_start_date,
                        "end_date": current_end_date,
                        "location": current_location,
                        "bullets": current_bullets[:15],
                        "is_current": "present" in current_end_date.lower()
                    })
                
                # Extract dates from current line
                current_start_date, current_end_date = _extract_dates(ln)
                
                # Parse new job header
                # Pattern: "Company — Role" or "Role at Company" or just "Company"
                parts = re.split(r"[—–-]{2,}|\sat\s", ln)
                if len(parts) >= 2:
                    current_company = parts[0].strip()
                    current_role = parts[1].split("|")[0].strip()
                else:
                    # Try to extract company (before location/date)
                    if has_location:
                        current_company = re.split(r"[,|]", ln)[0].strip()
                    else:
                        current_company = ln.split("|")[0].strip()
                    current_role = ""
                
                if has_location:
                    loc_match = re.search(r"([\w\s]+,\s*[\w\s]+)", ln)
                    if loc_match:
                        current_location = loc_match.group(1).strip()
                
                current_dates = ln
                current_bullets = []
                continue
            
            # Otherwise, it's a bullet point
            cleaned = _clean_bullet(ln)
            if not cleaned:
                continue
            
            # Filter out non-bullet lines (too short, no action verbs)
            if len(cleaned) < 30:
                continue
            
            # Must have action verb or be a bullet-formatted line
            is_bullet = re.match(r"^[\-•●◆■◦*]", ln.strip())
            has_action = re.search(action_verbs, cleaned, re.IGNORECASE)
            
            if is_bullet or has_action:
                current_bullets.append(cleaned)
        
        # Save last job
        if current_bullets:
            experience.append({
                "company": current_company,
                "role": current_role,
                "start_date": current_start_date,
                "end_date": current_end_date,
                "location": current_location,
                "bullets": current_bullets[:15],
                "is_current": "present" in current_end_date.lower() if current_end_date else False
            })
    
    # Fallback: if no structured experience found, extract all bullets generically
    if not experience and exp_text:
        exp_lines = _split_lines(exp_text)
        bullets: List[str] = []
        for ln in exp_lines:
            if _is_heading(ln):
                continue
            cleaned = _clean_bullet(ln)
            if len(cleaned) >= 40:
                bullets.append(cleaned)
        
        if bullets:
            experience.append({
                "company": "",
                "role": "",
                "start_date": "",
                "end_date": "",
                "location": "",
                "bullets": bullets[:25],
                "is_current": False
            })

    # Education parsing
    education: List[Dict[str, Any]] = []
    edu_text = sections.get("education") or ""
    if edu_text:
        edu_lines = _split_lines(edu_text)
        current_institution = ""
        current_degree = ""
        current_field = ""
        current_location = ""
        start_date = ""
        end_date = ""
        gpa = ""
        
        for ln in edu_lines:
            if _is_heading(ln):
                continue
            
            # Check if line has dates (likely institution header)
            dates = _extract_dates(ln)
            if dates[0]:
                # Save previous education entry
                if current_institution or current_degree:
                    education.append({
                        "institution": current_institution,
                        "degree": current_degree,
                        "field": current_field,
                        "start_date": start_date,
                        "end_date": end_date,
                        "gpa": gpa,
                        "location": current_location
                    })
                
                # Parse new education entry
                start_date, end_date = dates
                # Extract institution (usually before location or dates)
                parts = re.split(r'[,|]', ln)
                current_institution = parts[0].strip() if parts else ln.strip()
                
                # Try to extract location
                loc_match = re.search(r'([\w\s]+,\s*[\w\s]+)', ln)
                if loc_match:
                    current_location = loc_match.group(1).strip()
                
                current_degree = ""
                current_field = ""
                gpa = ""
                continue
            
            # Check for GPA
            gpa_match = re.search(r'GPA:?\s*(\d+\.\d+|\d+/\d+)', ln, re.IGNORECASE)
            if gpa_match:
                gpa = gpa_match.group(1)
                continue
            
            # Check for degree patterns (Bachelor, Master, PhD, etc.)
            degree_keywords = r'\b(Bachelor|Master|MBA|PhD|B\.S\.|M\.S\.|B\.A\.|M\.A\.|B\.Tech|M\.Tech|B\.E\.|M\.E\.)\b'
            if re.search(degree_keywords, ln, re.IGNORECASE):
                # This line likely contains degree and field
                current_degree = ln.strip()
                # Try to split degree and field (e.g., "Bachelor of Science in Computer Science")
                if " in " in ln.lower():
                    parts = re.split(r'\s+in\s+', ln, flags=re.IGNORECASE)
                    current_degree = parts[0].strip()
                    current_field = parts[1].strip() if len(parts) > 1 else ""
                continue
        
        # Save last education entry
        if current_institution or current_degree:
            education.append({
                "institution": current_institution,
                "degree": current_degree,
                "field": current_field,
                "start_date": start_date,
                "end_date": end_date,
                "gpa": gpa,
                "location": current_location
            })
    
    # Projects parsing
    projects: List[Dict[str, Any]] = []
    projects_text = sections.get("projects") or ""
    if projects_text:
        project_lines = _split_lines(projects_text)
        current_project = ""
        current_description = []
        current_tech = []
        
        for ln in project_lines:
            if _is_heading(ln):
                continue
            
            # Project name is usually bold/standalone short line or has dates
            if len(ln) < 100 and not ln.startswith(("•", "-", "●")) and current_project and current_description:
                # Save previous project
                projects.append({
                    "name": current_project,
                    "description": " ".join(current_description),
                    "technologies": current_tech,
                    "link": ""
                })
                current_project = ln.strip()
                current_description = []
                current_tech = []
                continue
            
            if not current_project:
                current_project = ln.strip()
                continue
            
            # Check for tech stack line
            if "technologies" in ln.lower() or "tech stack" in ln.lower() or "built with" in ln.lower():
                # Extract technologies
                tech_part = re.split(r':', ln, 1)
                if len(tech_part) > 1:
                    current_tech = [t.strip() for t in re.split(r'[,|/]', tech_part[1]) if t.strip()]
                continue
            
            # Otherwise it's description
            cleaned = _clean_bullet(ln)
            if cleaned and len(cleaned) > 15:
                current_description.append(cleaned)
        
        # Save last project
        if current_project:
            projects.append({
                "name": current_project,
                "description": " ".join(current_description),
                "technologies": current_tech,
                "link": ""
            })
    
    # Certifications parsing
    certifications: List[Dict[str, Any]] = []
    cert_text = sections.get("certifications") or ""
    if cert_text:
        cert_lines = _split_lines(cert_text)
        for ln in cert_lines:
            if _is_heading(ln):
                continue
            cleaned = _clean_bullet(ln)
            if cleaned and len(cleaned) > 5:
                # Extract cert name and issuer
                # Pattern: "Cert Name - Issuer" or "Cert Name, Issuer"
                parts = re.split(r'[-–—,|]', cleaned, 1)
                cert_name = parts[0].strip()
                issuer = parts[1].strip() if len(parts) > 1 else ""
                
                # Try to extract date
                dates = _extract_dates(ln)
                issue_date = dates[1] if dates[1] else dates[0] if dates[0] else ""
                
                certifications.append({
                    "name": cert_name,
                    "issuer": issuer,
                    "issue_date": issue_date,
                    "credential_id": ""
                })
    
    # Languages parsing
    languages: List[str] = []
    lang_text = sections.get("languages") or ""
    if lang_text:
        # Split on common delimiters
        lang_items = re.split(r'[,\n|/]+', lang_text)
        for item in lang_items:
            cleaned = _clean_bullet(item)
            # Remove proficiency levels
            cleaned = re.sub(r'\(.*?\)', '', cleaned).strip()
            cleaned = re.sub(r'\b(native|fluent|proficient|intermediate|basic|elementary)\b', '', cleaned, flags=re.IGNORECASE).strip()
            if cleaned and len(cleaned) > 2 and len(cleaned) < 30:
                languages.append(cleaned)
    
    # Awards/Honors parsing (bonus)
    awards: List[str] = []
    awards_text = sections.get("awards") or ""
    if awards_text:
        award_lines = _split_lines(awards_text)
        for ln in award_lines:
            if _is_heading(ln):
                continue
            cleaned = _clean_bullet(ln)
            if cleaned and len(cleaned) > 5:
                awards.append(cleaned)

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "location": location,
        "website": website,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "projects": projects,
        "certifications": certifications,
        "languages": languages,
        "awards": awards,
    }

async def parse_resume_file(file: UploadFile) -> Dict[str, Any]:
    """
    Parses PDF/DOCX resume and extracts structured data.
    Returns normalized JSON structure.
    """
    # Extract text from file
    text = ""
    filename = file.filename or ""
    file_extension = filename.split(".")[-1].lower() if "." in filename else ""
    
    content = await file.read()
    # Reset cursor so downstream code can read/save the file again
    try:
        await file.seek(0)
    except Exception:
        pass
    
    if file_extension == "pdf":
        text = extract_text_from_pdf(content)
    elif file_extension in ["docx", "doc"]:
        text = extract_text_from_docx(content)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
    
    # Always use heuristic extraction (real content from PDF).
    # If OpenAI is configured, we can enhance it later, but we start with real data.
    structured_data = heuristic_extract_resume_info(text)
    
    # Post-process and normalize
    normalized_data = normalize_resume_structure(structured_data, text)
    
    return normalized_data

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import io
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error parsing PDF: {str(e)}")

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        import io
        docx_file = io.BytesIO(content)
        doc = Document(docx_file)
        
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error parsing DOCX: {str(e)}")

def normalize_resume_structure(ai_output: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    """
    Normalizes AI output into CareerCopilot's standard structure.
    """
    return {
        "personal_info": {
            "name": ai_output.get("name", ""),
            "email": ai_output.get("email", ""),
            "phone": ai_output.get("phone", ""),
            "linkedin": ai_output.get("linkedin", ""),
            "github": ai_output.get("github", ""),
            "location": ai_output.get("location", ""),
            "website": ai_output.get("website", "")
        },
        "summary": ai_output.get("summary", ""),
        "skills": ai_output.get("skills", []),
        "experience": ai_output.get("experience", []),
        "education": ai_output.get("education", []),
        "projects": ai_output.get("projects", []),
        "certifications": ai_output.get("certifications", []),
        "languages": ai_output.get("languages", []),
        "awards": ai_output.get("awards", []),
        "sections_order": ["personal_info", "summary", "experience", "education", "skills", "projects", "certifications", "languages", "awards"],
        "raw_text": raw_text[:5000]  # Store first 5000 chars for reference
    }

def extract_email(text: str) -> str:
    """Extract email using regex."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""

def extract_phone(text: str) -> str:
    """Extract phone number using regex."""
    phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
    match = re.search(phone_pattern, text)
    return match.group(0) if match else ""

def extract_sections(text: str) -> Dict[str, str]:
    """
    Heuristic section detection.
    Looks for common section headers.
    """
    sections = {}
    
    # Common section headers
    headers = SECTION_HEADERS
    
    lines = text.split("\n")
    current_section = None
    section_content = []
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Check if line is a section header
        for section_name, keywords in headers.items():
            if any(keyword == line_lower for keyword in keywords):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(section_content)
                
                current_section = section_name
                section_content = []
                break
        else:
            if current_section:
                section_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = "\n".join(section_content)
    
    return sections

