-- Migration: Create scheduler-related tables
-- EventMirror: Mirror of calendar events for quick reads
CREATE TABLE IF NOT EXISTS event_mirror (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    external_event_id VARCHAR(255) NOT NULL,  -- ID from Google/Outlook
    calendar_provider VARCHAR(50) NOT NULL,  -- 'google', 'outlook'
    calendar_id VARCHAR(255) NOT NULL,         -- Calendar ID from provider
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    timezone VARCHAR(100),
    location TEXT,
    attendees JSONB DEFAULT '[]'::jsonb,      -- Array of {email, name, status}
    recurrence_rule TEXT,                      -- RRULE string
    status VARCHAR(50) DEFAULT 'confirmed',    -- confirmed, tentative, cancelled
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, calendar_provider, external_event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_mirror_user_id ON event_mirror(user_id);
CREATE INDEX IF NOT EXISTS idx_event_mirror_start_time ON event_mirror(start_time);
CREATE INDEX IF NOT EXISTS idx_event_mirror_provider ON event_mirror(calendar_provider, external_event_id);

-- CalendarConnection: OAuth tokens for calendar providers
CREATE TABLE IF NOT EXISTS calendar_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,             -- 'google', 'outlook'
    calendar_id VARCHAR(255) NOT NULL,         -- Primary calendar ID
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    scope TEXT,                                 -- OAuth scopes granted
    email VARCHAR(255),                         -- User's email from provider
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_calendar_connections_user_id ON calendar_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_connections_provider ON calendar_connections(provider);

-- Reminders: Scheduled reminders/alarms
CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    event_id UUID REFERENCES event_mirror(id) ON DELETE CASCADE,
    reminder_type VARCHAR(50) NOT NULL,         -- 'email', 'slack', 'in_app', 'sms'
    trigger_time TIMESTAMPTZ NOT NULL,         -- When to send reminder
    message TEXT,
    status VARCHAR(50) DEFAULT 'pending',      -- pending, sent, cancelled, failed
    retry_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    error_message TEXT,
    apscheduler_job_id VARCHAR(255),           -- APScheduler job ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_event_id ON reminders(event_id);
CREATE INDEX IF NOT EXISTS idx_reminders_trigger_time ON reminders(trigger_time);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);

-- Update users table to add role and timezone (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'role') THEN
        ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'timezone') THEN
        ALTER TABLE users ADD COLUMN timezone VARCHAR(100) DEFAULT 'UTC';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);


