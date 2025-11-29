-- Migration: Add source field to calendar_events for Google/simulated tracking
-- This migration adds a source column to track whether events come from Google Calendar or are simulated

ALTER TABLE calendar_events 
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'simulated',
ADD COLUMN IF NOT EXISTS google_event_id TEXT,
ADD COLUMN IF NOT EXISTS created_by TEXT;

CREATE INDEX IF NOT EXISTS idx_calendar_events_source ON calendar_events(source);
CREATE INDEX IF NOT EXISTS idx_calendar_events_google_id ON calendar_events(google_event_id);

