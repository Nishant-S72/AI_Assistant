-- Migration: Add reminder and postpone functionality to tasks
-- JIRA-like task management features

-- Add reminder fields to tasks table
DO $$ 
BEGIN
    -- Add reminder_enabled flag
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'reminder_enabled') THEN
        ALTER TABLE tasks ADD COLUMN reminder_enabled BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add reminder_minutes_before (e.g., 60 = 1 hour before due date)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'reminder_minutes_before') THEN
        ALTER TABLE tasks ADD COLUMN reminder_minutes_before INTEGER DEFAULT 60;
    END IF;
    
    -- Add reminder_sent flag
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'reminder_sent') THEN
        ALTER TABLE tasks ADD COLUMN reminder_sent BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add reminder_sent_at timestamp
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'reminder_sent_at') THEN
        ALTER TABLE tasks ADD COLUMN reminder_sent_at TIMESTAMPTZ;
    END IF;
    
    -- Add postponed_until (for postpone functionality)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'postponed_until') THEN
        ALTER TABLE tasks ADD COLUMN postponed_until TIMESTAMPTZ;
    END IF;
    
    -- Add cancelled_at timestamp
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'cancelled_at') THEN
        ALTER TABLE tasks ADD COLUMN cancelled_at TIMESTAMPTZ;
    END IF;
    
    -- Add cancelled_reason
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'cancelled_reason') THEN
        ALTER TABLE tasks ADD COLUMN cancelled_reason TEXT;
    END IF;
    
    -- Add completed_at timestamp
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'completed_at') THEN
        ALTER TABLE tasks ADD COLUMN completed_at TIMESTAMPTZ;
    END IF;
END $$;

-- Create index for reminder queries
CREATE INDEX IF NOT EXISTS idx_tasks_reminder_enabled ON tasks(reminder_enabled, due_at) WHERE reminder_enabled = TRUE AND status = 'pending';
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks(due_at) WHERE status = 'pending';

