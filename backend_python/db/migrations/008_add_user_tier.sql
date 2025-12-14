-- Migration: Add tier field to users table for Assist vs Pro gating
-- Assist ($500): Draft, summarize, classify, suggest - NO execution
-- Pro ($1000): Everything + auto-send, calendar, tasks, workflows

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'tier') THEN
        ALTER TABLE users ADD COLUMN tier VARCHAR(50) DEFAULT 'assist';
        -- Add constraint to ensure valid tier values
        ALTER TABLE users ADD CONSTRAINT check_tier CHECK (tier IN ('assist', 'pro'));
        -- Add index for faster tier lookups
        CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);
    END IF;
END $$;

-- Update existing users to 'assist' if tier is NULL
UPDATE users SET tier = 'assist' WHERE tier IS NULL;

