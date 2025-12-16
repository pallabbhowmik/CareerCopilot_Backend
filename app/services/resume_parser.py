import re
import json
from typing import Dict, Any, List
from fastapi import UploadFile
import PyPDF2
from docx import Document
from app.services.llm_engine import ai_service

async def parse_resume_file(file: UploadFile) -> Dict[str, Any]:
    """
    Parses PDF/DOCX resume and extracts structured data.
    Returns normalized JSON structure.
    """
    # Extract text from file
    text = ""
    file_extension = file.filename.split(".")[-1].lower()
    
    content = await file.read()
    
    if file_extension == "pdf":
        text = extract_text_from_pdf(content)
    elif file_extension in ["docx", "doc"]:
        text = extract_text_from_docx(content)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
    
    # Use AI to extract structured data
    structured_data = await ai_service.extract_resume_info(text)
    
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
    headers = {
        "experience": ["experience", "work history", "employment", "professional experience"],
        "education": ["education", "academic background"],
        "skills": ["skills", "technical skills", "core competencies"],
        "projects": ["projects", "personal projects"],
        "summary": ["summary", "professional summary", "objective"]
    }
    
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

