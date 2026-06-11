-- c:\Mood_Market\migrations\002_add_columns.sql
-- Incremental schema migrations

-- Alter tables to add new columns incrementally
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS metadata JSONB;
ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Add partial index on api_logs for debugging error rates
CREATE INDEX IF NOT EXISTS idx_api_logs_errors 
ON api_logs (status_code, time DESC) 
WHERE status_code >= 400;
