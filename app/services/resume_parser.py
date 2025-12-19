import re
import json
from typing import Dict, Any, List
from fastapi import UploadFile
import PyPDF2
from docx import Document
from app.services.llm_engine import ai_service


SECTION_HEADERS = {
    "experience": ["experience", "work history", "employment", "professional experience"],
    "education": ["education", "academic background"],
    "skills": ["skills", "technical skills", "core competencies", "core skills"],
    "projects": ["projects", "personal projects"],
    "summary": ["summary", "professional summary", "objective", "profile"],
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
    website = _extract_website(joined)

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

    # Summary
    summary = (sections.get("summary") or "").strip()
    if not summary:
        # fallback: first ~2 lines after the first heading
        summary_candidates: List[str] = []
        for ln in lines[:80]:
            if _is_heading(ln):
                continue
            if len(ln) < 40:
                continue
            summary_candidates.append(ln)
            if len(summary_candidates) >= 2:
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

    # Experience bullets
    exp_text = sections.get("experience") or ""
    exp_lines = _split_lines(exp_text) if exp_text else []
    bullets: List[str] = []
    for ln in exp_lines:
        if _is_heading(ln):
            continue
        cleaned = _clean_bullet(ln)
        if not cleaned:
            continue
        # Prefer bullet-like lines or strong sentence lines
        if re.match(r"^[\-•●◆■◦*]", ln.strip()):
            bullets.append(cleaned)
        elif len(cleaned) >= 45 and re.search(r"\b(led|built|designed|improved|reduced|increased|implemented|optimized|migrated|developed|engineered)\b", cleaned, re.IGNORECASE):
            bullets.append(cleaned)

    if not bullets and exp_lines:
        # fallback: take any sentence-like lines
        for ln in exp_lines:
            cleaned = _clean_bullet(ln)
            if len(cleaned) >= 40:
                bullets.append(cleaned)

    bullets = bullets[:25]

    experience: List[Dict[str, Any]] = []
    if bullets:
        # We keep a single aggregated experience entry (no company/date parsing) to power the editor.
        experience.append(
            {
                "company": "",
                "role": "",
                "start_date": "",
                "end_date": "",
                "location": "",
                "bullets": bullets,
                "is_current": False,
            }
        )

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "location": "",
        "website": website,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": [],
        "projects": [],
        "certifications": [],
        "languages": [],
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
    
    # Extract structured data
    # Prefer LLM when configured, but never fall back to mock content.
    structured_data: Dict[str, Any]
    if getattr(ai_service, "client", None):
        structured_data = await ai_service.extract_resume_info(text)
        if _looks_like_mock(structured_data):
            structured_data = heuristic_extract_resume_info(text)
    else:
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
        "sections_order": ["personal_info", "summary", "experience", "education", "skills"],
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

