-- Migration: Create comprehensive calendar events and reminders tables
-- This extends the scheduler tables with a standalone local calendar system

-- Events table: Standalone local calendar events (works without Google)
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    video_link TEXT,  -- e.g., Zoom/Meet URL
    start TIMESTAMPTZ NOT NULL,
    "end" TIMESTAMPTZ NOT NULL,
    all_day BOOLEAN DEFAULT FALSE,
    color VARCHAR(50) DEFAULT '#4285F4',  -- hex color or semantic name
    timezone VARCHAR(100) DEFAULT 'UTC',
    recurrence_rule TEXT,  -- iCal RRULE format (e.g., FREQ=WEEKLY;BYDAY=MO)
    attendees_json JSONB DEFAULT '[]'::jsonb,  -- Array of {email, name, status?}
    source VARCHAR(50) DEFAULT 'local',  -- 'local' | 'google'
    source_event_id VARCHAR(255),  -- Google event id if synced
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_time_range CHECK ("end" > start)
);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start);
CREATE INDEX IF NOT EXISTS idx_events_end ON events("end");
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source, source_event_id);
CREATE INDEX IF NOT EXISTS idx_events_user_start ON events(user_id, start);

-- Reminders table: Standalone reminders (can be tied to events or standalone)
-- Note: This extends the existing reminders table from migration 006
-- If reminders table already exists, we'll add missing columns
DO $$ 
BEGIN
    -- Add columns to existing reminders table if they don't exist
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'reminders') THEN
        -- Add minutes_before if it doesn't exist (for relative reminders)
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reminders' AND column_name = 'minutes_before') THEN
            ALTER TABLE reminders ADD COLUMN minutes_before INTEGER;
        END IF;
        
        -- Add when (absolute datetime) if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reminders' AND column_name = 'when') THEN
            ALTER TABLE reminders ADD COLUMN "when" TIMESTAMPTZ;
        END IF;
        
        -- Add repeat_rule if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reminders' AND column_name = 'repeat_rule') THEN
            ALTER TABLE reminders ADD COLUMN repeat_rule TEXT;
        END IF;
        
        -- Make event_id nullable for standalone reminders
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reminders' AND column_name = 'event_id') THEN
            -- Check if constraint exists and drop if needed
            ALTER TABLE reminders ALTER COLUMN event_id DROP NOT NULL;
        END IF;
    END IF;
END $$;

-- If reminders table doesn't exist, create it with all fields
CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,  -- Nullable for standalone reminders
    minutes_before INTEGER,  -- Relative reminder (e.g., 10 minutes before event)
    "when" TIMESTAMPTZ,  -- Absolute reminder time
    channel VARCHAR(50) NOT NULL DEFAULT 'inapp',  -- 'inapp' | 'email' | 'slack'
    repeat_rule TEXT,  -- Optional repeat rule
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT reminder_time_check CHECK (
        (minutes_before IS NOT NULL) OR ("when" IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_event_id ON reminders(event_id);
CREATE INDEX IF NOT EXISTS idx_reminders_when ON reminders("when");
CREATE INDEX IF NOT EXISTS idx_reminders_delivered ON reminders(delivered);

-- Add user_id foreign key constraint if users table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        -- Add foreign key constraints if they don't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE table_name = 'events' AND constraint_name = 'fk_events_user_id'
        ) THEN
            ALTER TABLE events ADD CONSTRAINT fk_events_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE table_name = 'reminders' AND constraint_name = 'fk_reminders_user_id'
        ) THEN
            ALTER TABLE reminders ADD CONSTRAINT fk_reminders_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        END IF;
    END IF;
END $$;

