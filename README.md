# CareerCopilot AI

## Overview
CareerCopilot AI is a production-ready career optimization platform designed to help users get more interviews by improving resumes, skills, and job alignment. Unlike generic resume builders, this platform focuses on outcome-driven results, explainable AI recommendations, and honest limitations.

## Tech Stack
- **Frontend:** Next.js 14 (App Router), Tailwind CSS, TypeScript
- **Backend:** FastAPI (Python), Pydantic
- **Database:** PostgreSQL
- **AI:** Modular LLM Service Layer (OpenAI/Anthropic compatible)
- **Auth:** OAuth2 with JWT

## Project Structure
```
/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/            # API Endpoints
│   │   ├── core/           # Config, Security
│   │   ├── db/             # Database Session & Base
│   │   ├── models/         # SQLAlchemy Models
│   │   ├── schemas/        # Pydantic Schemas
│   │   ├── services/       # Business Logic (AI, Parsing)
│   │   └── main.py         # Entry Point
│   └── requirements.txt
├── frontend/                # Next.js Frontend
│   ├── src/
│   │   ├── app/            # App Router Pages
│   │   ├── components/     # Reusable UI Components
│   │   └── lib/            # Utilities & API Clients
│   ├── package.json
│   └── tailwind.config.ts
└── README.md
```

## Setup Instructions

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL

### Backend Setup
1. Navigate to `backend`:
   ```bash
   cd backend
   ```
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to `frontend`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run development server:
   ```bash
   npm run dev
   ```

## Features
- **Resume Engine:** Parse and normalize resumes into structured JSON.
- **Job Analyzer:** Extract core skills and requirements from JDs.
- **Gap Analysis:** Compare resume vs. job description.
- **Career Chat:** Conversational AI for career advice.
- **Template System:** 50+ ATS-safe templates with JSON configuration.
- **Analytics:** A/B testing for resume variants and application tracking.
- **Export Engine:** Generate PDF/DOCX from structured data.
