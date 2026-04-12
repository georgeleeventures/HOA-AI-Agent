-- Migration 001: Enhanced audit log for governance & observability
-- Adds confidence tracking, flagging, admin review, and response timing

ALTER TABLE audit_log ADD COLUMN full_response TEXT;
ALTER TABLE audit_log ADD COLUMN confidence VARCHAR(20);
ALTER TABLE audit_log ADD COLUMN avg_similarity_score FLOAT;
ALTER TABLE audit_log ADD COLUMN thread_id VARCHAR(255);
ALTER TABLE audit_log ADD COLUMN is_flagged BOOLEAN DEFAULT FALSE;
ALTER TABLE audit_log ADD COLUMN flag_reason VARCHAR(100);
ALTER TABLE audit_log ADD COLUMN admin_notes TEXT;
ALTER TABLE audit_log ADD COLUMN reviewed_by VARCHAR(500);
ALTER TABLE audit_log ADD COLUMN reviewed_at TIMESTAMP;
ALTER TABLE audit_log ADD COLUMN response_time_ms INTEGER;

CREATE INDEX idx_audit_flagged ON audit_log(is_flagged) WHERE is_flagged = TRUE;
CREATE INDEX idx_audit_confidence ON audit_log(confidence);
CREATE INDEX idx_audit_channel ON audit_log(channel);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_thread ON audit_log(thread_id);
