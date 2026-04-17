-- Migration 005: Replace IVFFlat with HNSW vector indexes
-- HNSW works at any dataset size without tuning

BEGIN;

DROP INDEX IF EXISTS idx_doc_chunks_embedding;
CREATE INDEX idx_doc_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);

DROP INDEX IF EXISTS idx_admin_answers_embedding;
CREATE INDEX idx_admin_answers_embedding ON admin_answers
    USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);

COMMIT;
