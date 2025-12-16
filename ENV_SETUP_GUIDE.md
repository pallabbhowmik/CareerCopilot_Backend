# CareerCopilot AI Environment Setup

# Backend environment variables (.env file in backend/)
DATABASE_URL="postgresql://user:password@host:6543/database?sslmode=require"
SECRET_KEY="generate-a-secure-random-key-min-32-characters-long"
OPENAI_API_KEY="sk-proj-your-openai-api-key-here"

# Optional
PROJECT_NAME="CareerCopilot AI"
API_V1_STR="/api/v1"
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://your-frontend-domain.vercel.app"]

# Supabase (if using Supabase features beyond PostgreSQL)
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_KEY="your-supabase-anon-key"
SUPABASE_JWT_SECRET="your-supabase-jwt-secret"

# Frontend environment variables (.env.local file in frontend/)
NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"

# For production:
# NEXT_PUBLIC_API_URL="https://your-backend-domain.onrender.com/api/v1"

# =====================================
# HOW TO GET THESE VALUES:
# =====================================

# 1. DATABASE_URL (Supabase):
#    - Go to https://supabase.com/dashboard
#    - Create new project
#    - Go to Settings > Database
#    - Copy "Connection string" (use Connection Pooler mode for production)
#    - Replace [YOUR-PASSWORD] with your actual password

# 2. SECRET_KEY:
#    - Generate random key:
#      python -c "import secrets; print(secrets.token_urlsafe(32))"
#    - Or use: openssl rand -hex 32

# 3. OPENAI_API_KEY:
#    - Go to https://platform.openai.com/api-keys
#    - Create new secret key
#    - Copy key (starts with sk-proj- or sk-)

# 4. SUPABASE_URL & SUPABASE_KEY:
#    - Go to Supabase project Settings > API
#    - Copy "Project URL" and "anon public" key

# =====================================
# QUICK START:
# =====================================

# Backend:
cd backend
cp .env.example .env  # Edit with your values
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend:
cd frontend
cp .env.example .env.local  # Edit with your values
npm install
npm run dev

# =====================================
# DEPLOYMENT CHECKLIST:
# =====================================

# Backend (Render):
# ✓ Set all environment variables in Render dashboard
# ✓ Use Supabase connection pooler (port 6543)
# ✓ Add frontend domain to BACKEND_CORS_ORIGINS

# Frontend (Vercel):
# ✓ Set NEXT_PUBLIC_API_URL to backend URL
# ✓ Deploy from main branch
# ✓ Auto-deploy on push enabled

# Database (Supabase):
# ✓ Enable connection pooling
# ✓ Configure Row Level Security (optional)
# ✓ Set up database backups
