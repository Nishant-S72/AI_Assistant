-- Database schema for AI Chief-of-Staff POC

-- Contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    tone_pref TEXT DEFAULT 'warm',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    channel TEXT NOT NULL, -- 'email', 'whatsapp', etc.
    thread_id TEXT NOT NULL,
    sender TEXT NOT NULL, -- 'contact' or 'assistant'
    body TEXT NOT NULL,
    raw JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_contact_id ON messages(contact_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Suggestions table
CREATE TABLE IF NOT EXISTS suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    retrieved_ids JSONB DEFAULT '[]'::jsonb,
    model_response TEXT NOT NULL,
    final_text TEXT,
    edited BOOLEAN DEFAULT FALSE,
    edit_diff TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suggestions_message_id ON suggestions(message_id);

-- Events table (audit log)
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL, -- 'suggestion_generated', 'message_sent', 'policy_escalated', etc.
    correlation_id TEXT,
    request_path TEXT,
    user_id TEXT,
    prompt_ref TEXT, -- path to gzipped prompt file
    retrieved_ids JSONB DEFAULT '[]'::jsonb,
    raw_model_response TEXT,
    final_text TEXT,
    latency_ms INTEGER,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    due_at TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'cancelled'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_contact_id ON tasks(contact_id);

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

