-- ============================================================================
-- MEETME MIGRATION 002: Native Gmail SMTP & Consolidated Reminders
-- ============================================================================

-- 1. Upgrade email_logs with task_ids array, email_type, message_id, idempotency_key, and retry tracking
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'email_logs' AND column_name = 'task_ids') THEN
        ALTER TABLE email_logs ADD COLUMN task_ids JSONB DEFAULT '[]'::jsonb;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'email_logs' AND column_name = 'email_type') THEN
        ALTER TABLE email_logs ADD COLUMN email_type VARCHAR(100) DEFAULT 'TASK_ASSIGNMENT';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'email_logs' AND column_name = 'message_id') THEN
        ALTER TABLE email_logs ADD COLUMN message_id VARCHAR(255);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'email_logs' AND column_name = 'idempotency_key') THEN
        ALTER TABLE email_logs ADD COLUMN idempotency_key VARCHAR(255);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'email_logs' AND column_name = 'retry_count') THEN
        ALTER TABLE email_logs ADD COLUMN retry_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- 2. Upgrade reminders with task_ids for consolidated batches
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reminders' AND column_name = 'task_ids') THEN
        ALTER TABLE reminders ADD COLUMN task_ids JSONB DEFAULT '[]'::jsonb;
    END IF;
END $$;

-- 3. Set default provider for email_logs to 'Gmail SMTP'
ALTER TABLE email_logs ALTER COLUMN provider SET DEFAULT 'Gmail SMTP';

-- 4. Create performance indexes
CREATE INDEX IF NOT EXISTS idx_email_logs_idempotency_key ON email_logs(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_email_logs_email_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_status_sent_at ON email_logs(status, sent_at);
CREATE INDEX IF NOT EXISTS idx_reminders_status_scheduled_at ON reminders(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_reminders_email_type ON reminders(email_address, reminder_type);

-- 5. Row Level Security policies (reuse workspace security)
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'email_logs' AND policyname = 'Allow public read-write for email_logs') THEN
        CREATE POLICY "Allow public read-write for email_logs" ON email_logs FOR ALL USING (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'reminders' AND policyname = 'Allow public read-write for reminders') THEN
        CREATE POLICY "Allow public read-write for reminders" ON reminders FOR ALL USING (true);
    END IF;
END $$;
