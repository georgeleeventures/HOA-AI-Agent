-- Migration 007: Contractor marketplace tables

BEGIN;

CREATE TABLE IF NOT EXISTS contractors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(500) NOT NULL,
    contact_name VARCHAR(500),
    email VARCHAR(500) UNIQUE NOT NULL,
    phone VARCHAR(50),
    license_number VARCHAR(100),
    service_types TEXT[],
    coverage_zipcodes TEXT[],
    bio TEXT,
    website VARCHAR(500),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS work_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hoa_id UUID REFERENCES hoas(id) NOT NULL,
    maintenance_log_id UUID REFERENCES maintenance_log(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    service_type VARCHAR(100),
    urgency VARCHAR(50) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'open',
    budget_range_low DECIMAL(10,2),
    budget_range_high DECIMAL(10,2),
    photos JSONB DEFAULT '[]',
    created_by VARCHAR(500),
    awarded_to UUID REFERENCES contractors(id),
    awarded_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_request_id UUID REFERENCES work_requests(id) NOT NULL,
    contractor_id UUID REFERENCES contractors(id) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    estimated_days INTEGER,
    proposal TEXT,
    status VARCHAR(50) DEFAULT 'submitted',
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(work_request_id, contractor_id)
);

CREATE TABLE IF NOT EXISTS referral_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_request_id UUID REFERENCES work_requests(id),
    contractor_id UUID REFERENCES contractors(id),
    hoa_id UUID REFERENCES hoas(id),
    referral_type VARCHAR(50),
    fee_amount DECIMAL(10,2),
    is_paid BOOLEAN DEFAULT FALSE,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_work_requests_hoa ON work_requests(hoa_id);
CREATE INDEX IF NOT EXISTS idx_work_requests_status ON work_requests(status);
CREATE INDEX IF NOT EXISTS idx_work_requests_service ON work_requests(service_type);
CREATE INDEX IF NOT EXISTS idx_bids_work_request ON bids(work_request_id);
CREATE INDEX IF NOT EXISTS idx_bids_contractor ON bids(contractor_id);
CREATE INDEX IF NOT EXISTS idx_contractors_service ON contractors USING gin(service_types);
CREATE INDEX IF NOT EXISTS idx_contractors_zip ON contractors USING gin(coverage_zipcodes);
CREATE INDEX IF NOT EXISTS idx_referral_hoa ON referral_tracking(hoa_id);

COMMIT;
