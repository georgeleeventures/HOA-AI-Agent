-- Migration 004: Email provider abstraction
-- Adds provider-agnostic columns to emails table

BEGIN;

ALTER TABLE emails ADD COLUMN IF NOT EXISTS message_id VARCHAR(255);
ALTER TABLE emails ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'gmail';
ALTER TABLE emails ADD COLUMN IF NOT EXISTS in_reply_to VARCHAR(500);
ALTER TABLE emails ADD COLUMN IF NOT EXISTS email_references TEXT[];

CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_provider ON emails(provider);

COMMIT;
