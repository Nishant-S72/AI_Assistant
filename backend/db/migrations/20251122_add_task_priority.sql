-- Migration: Add priority column to tasks table
-- Date: 2025-11-22

-- Add priority column if it doesn't exist
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'tasks' AND column_name = 'priority'
  ) THEN
    ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'P2';
    
    -- Backfill overdue tasks as P0
    UPDATE tasks 
    SET priority = 'P0'
    WHERE due_at IS NOT NULL 
      AND due_at <= NOW() 
      AND status = 'pending';
    
    -- Create index for priority
    CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
    
    RAISE NOTICE 'Added priority column to tasks table';
  ELSE
    RAISE NOTICE 'Priority column already exists';
  END IF;
END $$;


