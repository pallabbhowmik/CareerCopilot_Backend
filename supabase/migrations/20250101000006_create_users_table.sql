-- =====================================================
-- Create users table for authentication
-- This is the simple auth table used by the FastAPI endpoints
-- Separate from user_profiles which is for the AI platform
-- =====================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- User profile fields
    target_role VARCHAR(255),
    experience_level VARCHAR(50),
    country VARCHAR(100),
    career_goal TEXT,
    onboarding_completed BOOLEAN DEFAULT FALSE
);

-- Index for faster email lookups
CREATE INDEX idx_users_email ON users(email);

-- Insert a test user (optional, for testing)
-- Password is: testpassword123
-- INSERT INTO users (email, hashed_password, full_name, is_active, onboarding_completed)
-- VALUES ('test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzQVQp1pLS', 'Test User', true, false);
