-- Calendar Events table
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern TEXT, -- 'daily', 'weekly', 'monthly', 'yearly'
    recurrence_end_date TIMESTAMP, -- When recurring events should stop
    recurrence_interval INTEGER DEFAULT 1, -- Every N days/weeks/months
    location TEXT,
    attendees JSONB DEFAULT '[]'::jsonb, -- Array of contact IDs or email addresses
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_start_time ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_recurring ON calendar_events(is_recurring);
CREATE INDEX IF NOT EXISTS idx_calendar_events_date_range ON calendar_events(start_time, end_time);

