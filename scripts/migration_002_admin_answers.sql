-- Migration 002: Admin answer overrides (FAQ system)
-- Allows admins to create authoritative answers for recurring questions

CREATE TABLE admin_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_pattern TEXT NOT NULL,
    answer TEXT NOT NULL,
    keywords TEXT[],
    embedding vector(768),
    source_audit_id UUID REFERENCES audit_log(id),
    created_by VARCHAR(500) NOT NULL,
    updated_by VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_admin_answers_embedding ON admin_answers
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
CREATE INDEX idx_admin_answers_active ON admin_answers(is_active)
    WHERE is_active = TRUE;
