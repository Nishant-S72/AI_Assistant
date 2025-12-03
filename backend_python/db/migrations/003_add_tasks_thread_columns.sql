-- Migration: Add thread_id and message_id to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS thread_id TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS message_id TEXT;

CREATE INDEX IF NOT EXISTS idx_tasks_thread_id ON tasks(thread_id);
CREATE INDEX IF NOT EXISTS idx_tasks_message_id ON tasks(message_id);

