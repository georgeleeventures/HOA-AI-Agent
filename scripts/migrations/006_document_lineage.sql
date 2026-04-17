-- Migration 006: Document versioning and lineage tracking

BEGIN;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS supersedes_id UUID REFERENCES documents(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS effective_date DATE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS expiration_date DATE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT TRUE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS lineage_group UUID;

CREATE INDEX IF NOT EXISTS idx_documents_current ON documents(hoa_id, category) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_documents_lineage ON documents(lineage_group);
CREATE INDEX IF NOT EXISTS idx_documents_supersedes ON documents(supersedes_id);

COMMIT;
