-- Migration 003: Multi-tenancy foundation
-- Adds hoa_id to all tables, creates hoas table, enables RLS

BEGIN;

-- 1. Create hoas table
CREATE TABLE IF NOT EXISTS hoas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email_address VARCHAR(500),
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Insert default HOA for existing data
INSERT INTO hoas (id, name, slug)
VALUES ('00000000-0000-0000-0000-000000000001', 'Default HOA', 'default')
ON CONFLICT (slug) DO NOTHING;

-- 3. Add hoa_id columns (nullable first for backward compat)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);
ALTER TABLE emails ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);
ALTER TABLE residents ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);
ALTER TABLE maintenance_log ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);
ALTER TABLE financials ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);
ALTER TABLE admin_answers ADD COLUMN IF NOT EXISTS hoa_id UUID REFERENCES hoas(id);

-- 4. Backfill all existing rows with default HOA
UPDATE documents SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;
UPDATE document_chunks SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;
UPDATE emails SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;
UPDATE residents SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;
UPDATE maintenance_log SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;
UPDATE financials SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;
UPDATE audit_log SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;
UPDATE admin_answers SET hoa_id = '00000000-0000-0000-0000-000000000001' WHERE hoa_id IS NULL;

-- 5. Make hoa_id NOT NULL
ALTER TABLE documents ALTER COLUMN hoa_id SET NOT NULL;
ALTER TABLE document_chunks ALTER COLUMN hoa_id SET NOT NULL;
ALTER TABLE emails ALTER COLUMN hoa_id SET NOT NULL;
ALTER TABLE residents ALTER COLUMN hoa_id SET NOT NULL;
ALTER TABLE maintenance_log ALTER COLUMN hoa_id SET NOT NULL;
ALTER TABLE financials ALTER COLUMN hoa_id SET NOT NULL;
ALTER TABLE audit_log ALTER COLUMN hoa_id SET NOT NULL;
ALTER TABLE admin_answers ALTER COLUMN hoa_id SET NOT NULL;

-- 6. Drop old unique constraint on residents.email, replace with composite
ALTER TABLE residents DROP CONSTRAINT IF EXISTS residents_email_key;
ALTER TABLE residents ADD CONSTRAINT residents_hoa_email_unique UNIQUE (hoa_id, email);

-- 7. Add composite indexes for tenant-scoped queries
CREATE INDEX IF NOT EXISTS idx_documents_hoa ON documents(hoa_id);
CREATE INDEX IF NOT EXISTS idx_documents_hoa_category ON documents(hoa_id, category);
CREATE INDEX IF NOT EXISTS idx_document_chunks_hoa ON document_chunks(hoa_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_emails_hoa ON emails(hoa_id);
CREATE INDEX IF NOT EXISTS idx_emails_hoa_sender ON emails(hoa_id, sender);
CREATE INDEX IF NOT EXISTS idx_residents_hoa ON residents(hoa_id);
CREATE INDEX IF NOT EXISTS idx_residents_hoa_authorized ON residents(hoa_id, email) WHERE is_authorized = TRUE;
CREATE INDEX IF NOT EXISTS idx_maintenance_hoa ON maintenance_log(hoa_id);
CREATE INDEX IF NOT EXISTS idx_financials_hoa ON financials(hoa_id);
CREATE INDEX IF NOT EXISTS idx_audit_hoa ON audit_log(hoa_id);
CREATE INDEX IF NOT EXISTS idx_audit_hoa_created ON audit_log(hoa_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_answers_hoa ON admin_answers(hoa_id);

-- 8. Enable Row-Level Security as safety net
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE residents ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE financials ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_answers ENABLE ROW LEVEL SECURITY;

-- RLS policies: allow access when app.current_hoa_id is set
-- The app sets this via SET LOCAL before queries
CREATE POLICY documents_tenant ON documents
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

CREATE POLICY document_chunks_tenant ON document_chunks
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

CREATE POLICY emails_tenant ON emails
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

CREATE POLICY residents_tenant ON residents
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

CREATE POLICY maintenance_tenant ON maintenance_log
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

CREATE POLICY financials_tenant ON financials
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

CREATE POLICY audit_tenant ON audit_log
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

CREATE POLICY admin_answers_tenant ON admin_answers
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid)
    WITH CHECK (hoa_id = current_setting('app.current_hoa_id', true)::uuid);

-- Bypass RLS for the app's superuser role (used by migrations/admin)
-- The housekeep user needs to bypass RLS for normal operations
-- since we filter by hoa_id in application code
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE document_chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE emails FORCE ROW LEVEL SECURITY;
ALTER TABLE residents FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_log FORCE ROW LEVEL SECURITY;
ALTER TABLE financials FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
ALTER TABLE admin_answers FORCE ROW LEVEL SECURITY;

-- Grant bypass to the app user (RLS is a safety net, not primary isolation)
ALTER ROLE housekeep BYPASSRLS;

COMMIT;
