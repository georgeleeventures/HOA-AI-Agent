-- HouseKeep AI Database Schema

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents: all ingested files and their classifications
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT,
    raw_text TEXT,
    metadata JSONB DEFAULT '{}',
    source_email_id VARCHAR(255),
    source_filename VARCHAR(500),
    file_type VARCHAR(50),
    file_path VARCHAR(1000),
    confidence_score FLOAT,
    needs_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Document chunks with embeddings for vector search
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Emails: all processed emails
CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gmail_id VARCHAR(255) UNIQUE NOT NULL,
    thread_id VARCHAR(255),
    sender VARCHAR(500),
    recipients TEXT[],
    subject VARCHAR(1000),
    body_text TEXT,
    summary TEXT,
    has_attachments BOOLEAN DEFAULT FALSE,
    is_processed BOOLEAN DEFAULT FALSE,
    received_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Residents: authorized users and their roles
CREATE TABLE residents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(500) UNIQUE NOT NULL,
    name VARCHAR(500),
    unit VARCHAR(50),
    role VARCHAR(50) DEFAULT 'resident',
    ownership_pct FLOAT,
    is_authorized BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Maintenance log
CREATE TABLE maintenance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit VARCHAR(50),
    description TEXT,
    issue_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'reported',
    photos JSONB DEFAULT '[]',
    contractor VARCHAR(500),
    cost DECIMAL(10, 2),
    reported_by VARCHAR(500),
    source_email_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Financial records
CREATE TABLE financials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100),
    description TEXT,
    amount DECIMAL(10, 2),
    transaction_date DATE,
    vendor VARCHAR(500),
    document_id UUID REFERENCES documents(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit log: every interaction
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email VARCHAR(500),
    channel VARCHAR(50),
    action VARCHAR(100),
    query TEXT,
    response_summary TEXT,
    full_response TEXT,
    confidence VARCHAR(20),
    avg_similarity_score FLOAT,
    thread_id VARCHAR(255),
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason VARCHAR(100),
    admin_notes TEXT,
    reviewed_by VARCHAR(500),
    reviewed_at TIMESTAMP,
    response_time_ms INTEGER,
    documents_cited JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Admin answer overrides (FAQ system)
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

-- Indexes
CREATE INDEX idx_doc_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_documents_category ON documents(category, subcategory);
CREATE INDEX idx_documents_content ON documents USING gin(to_tsvector('english', content));
CREATE INDEX idx_emails_thread ON emails(thread_id);
CREATE INDEX idx_emails_sender ON emails(sender);
CREATE INDEX idx_emails_gmail_id ON emails(gmail_id);
CREATE INDEX idx_residents_email ON residents(email);
CREATE INDEX idx_maintenance_unit ON maintenance_log(unit);
CREATE INDEX idx_audit_user ON audit_log(user_email);
CREATE INDEX idx_audit_created ON audit_log(created_at);
CREATE INDEX idx_audit_flagged ON audit_log(is_flagged) WHERE is_flagged = TRUE;
CREATE INDEX idx_audit_confidence ON audit_log(confidence);
CREATE INDEX idx_audit_channel ON audit_log(channel);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_thread ON audit_log(thread_id);
CREATE INDEX idx_admin_answers_embedding ON admin_answers USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
CREATE INDEX idx_admin_answers_active ON admin_answers(is_active) WHERE is_active = TRUE;
