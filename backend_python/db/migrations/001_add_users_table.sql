-- Migration: Add users table for rate limiting and RBAC
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user', 'read_only')),
    monthly_quota_tokens INTEGER DEFAULT 100000,
    tokens_used INTEGER DEFAULT 0,
    quota_reset_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

