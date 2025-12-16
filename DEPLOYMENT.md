# CareerCopilot AI - Deployment Guide

## 1. Database (PostgreSQL)
- Provision a PostgreSQL instance (e.g., AWS RDS, Supabase, or DigitalOcean Managed DB).
- Set `DATABASE_URL` in your environment variables.
- Run migrations (using Alembic, if configured, or `Base.metadata.create_all` for initial setup).

## 2. Backend (FastAPI)
- **Dockerize:** Create a `Dockerfile` for the backend.
  ```dockerfile
  FROM python:3.10-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- **Environment Variables:**
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `OPENAI_API_KEY`
- **Deploy:** Use a platform like Render, Railway, or AWS App Runner.

## 3. Frontend (Next.js)
- **Build:** `npm run build`
- **Environment Variables:**
  - `NEXT_PUBLIC_API_URL` (Point to your deployed backend URL)
- **Deploy:** Vercel is recommended for Next.js.
  - Connect your GitHub repo.
  - Set environment variables in Vercel dashboard.
  - Deploy.

## 4. CI/CD
- Set up GitHub Actions to run tests and linting on push.
- Auto-deploy to staging on merge to `main`.
