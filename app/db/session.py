from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create engine with connection pooling optimized for Supabase
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "connect_timeout": 10,
        "options": "-c timezone=utc"
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
