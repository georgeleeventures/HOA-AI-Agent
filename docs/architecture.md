# HouseKeep AI — Architecture Guide

## Overview

HouseKeep AI is a multi-tenant, email-first AI agent for HOA management. Residents and board members email questions or forward documents; HouseKeep classifies, stores, and answers using RAG (Retrieval-Augmented Generation) powered by Google Vertex AI.

```
                    ┌─────────────────────────────┐
                    │   Resident / Board Member    │
                    └──────┬──────────────┬────────┘
                           │              │
                    Email (Resend)    Web Dashboard
                           │         (Google OAuth)
                           ▼              │
                  ┌────────────────┐      │
                  │ Resend Webhook │      │
                  │ /webhooks/email│      │
                  └───────┬────────┘      │
                          │               ▼
                  ┌───────▼───────────────────────┐
                  │         FastAPI App            │
                  │  ┌──────────────────────────┐  │
                  │  │   Tenant Middleware       │  │
                  │  │   (subdomain → hoa_id)   │  │
                  │  └──────────┬───────────────┘  │
                  │             │                   │
                  │  ┌──────────▼───────────────┐  │
                  │  │    Email Handler          │  │
                  │  │  - Intent Classification │  │
                  │  │  - Auth Verification     │  │
                  │  └──┬────────┬────────┬─────┘  │
                  │     │        │        │        │
                  │  Question  Doc Fwd  Thread CC  │
                  │     │        │        │        │
                  │  ┌──▼──┐ ┌──▼──────┐ │        │
                  │  │ RAG │ │Doc Proc │ │        │
                  │  │Pipeline│Classify│ │        │
                  │  └──┬──┘ │+ Embed │ │        │
                  │     │    └────┬────┘ │        │
                  │     │         │      │        │
                  │  ┌──▼─────────▼──────▼──────┐ │
                  │  │      PostgreSQL 16        │ │
                  │  │  + pgvector (HNSW index)  │ │
                  │  └──────────────────────────┘ │
                  └───────────────────────────────┘
```

## Multi-Tenancy

Every row in every table has an `hoa_id` foreign key referencing the `hoas` table. Tenant isolation is enforced at two levels:

1. **Application layer**: All SQL queries include `WHERE hoa_id = $N`
2. **Database layer**: PostgreSQL Row-Level Security (RLS) as a safety net

### Tenant Resolution

- **Web requests**: Subdomain extracted from `Host` header by `TenantMiddleware` (e.g., `twinpeaks.housekeep.click` → HOA slug `twinpeaks`)
- **Email webhooks**: HOA determined from the `To:` address (e.g., `board@twinpeaks.housekeep.click`)

### Tables with `hoa_id`

| Table | Purpose |
|-------|---------|
| `hoas` | HOA registry (name, slug, email, settings) |
| `documents` | Ingested files with classification |
| `document_chunks` | Vector embeddings for semantic search |
| `emails` | Processed email records |
| `residents` | Authorized users per HOA |
| `maintenance_log` | Work orders and repairs |
| `financials` | Expenses and revenue |
| `audit_log` | Complete interaction history |
| `admin_answers` | FAQ overrides per HOA |

## Email Pipeline

### Provider Abstraction

```
app/email/
├── provider.py         # Abstract EmailProvider interface
├── models.py           # ParsedEmail, Attachment dataclasses
├── resend_provider.py  # Resend API implementation
├── gmail.py            # Gmail API adapter (backward compat)
└── webhook.py          # Resend inbound webhook
```

### Inbound Flow (Resend)

1. Email arrives at `board@{slug}.housekeep.click`
2. Resend sends `email.received` webhook event to `/webhooks/email/{secret}`
3. Webhook fetches full email content (body + attachments) via Resend API
4. HOA resolved from `To:` address → `hoa_id`
5. Sender verified against `residents` table (must be `is_authorized = TRUE`)
6. Intent classified: question, document_forward, thread_cc, or correction
7. Routed to appropriate handler

### Outbound Flow

Replies sent via Resend API with `In-Reply-To` and `References` headers for proper threading.

## Document Processing

### Text Extraction

| File Type | Method |
|-----------|--------|
| PDF (text) | pdfplumber |
| PDF (scanned) | Gemini 2.5 Flash OCR |
| Images | Gemini multimodal OCR |
| DOCX, XLSX | Direct text read |
| Unknown MIME | Infer from file extension |

### Classification

Gemini 2.5 Flash classifies documents into 9 categories / 28 subcategories (see `docs/data-ontology.md`). Thinking is disabled and output is capped for predictable cost and latency. Returns: category, subcategory, confidence (0-1), title, metadata.

### Versioning

Documents support lineage tracking:
- `version` — integer version number
- `supersedes_id` — FK to previous version
- `lineage_group` — UUID grouping all versions
- `is_current` — only current versions searched by default
- `effective_date` / `expiration_date` — for temporal queries

## RAG Pipeline

1. **Embed question** → 768-dim vector via Vertex AI text-embedding-004
2. **Check FAQ** → admin_answers table (distance < 0.25 = instant match)
3. **Vector search** → HNSW index on document_chunks, filtered by `hoa_id` and user role
4. **Confidence** → weighted score (70% best match + 30% average): high (<0.35), medium (<0.55), low
5. **Generate answer** → Gemini with context + role-appropriate prompt
6. **Citations** → source documents listed in response

### Chunking

Sentence-aware chunking (2000 chars target, 2-sentence overlap). Preserves sentence boundaries for better retrieval quality.

### Role-Based Access

| Role | Categories Visible |
|------|-------------------|
| resident | Governing, Meeting, Maintenance, Correspondence |
| board_member | All categories |
| admin | All categories + admin panel |

## Contractor Marketplace

### Tables

- `contractors` — company profiles, service types, coverage areas
- `work_requests` — maintenance needs published by HOA admins
- `bids` — contractor proposals on work requests
- `referral_tracking` — revenue tracking (5% referral fee on awarded bids)

### Flow

1. Maintenance issue detected (via email or admin dashboard)
2. HOA admin creates work request
3. Contractors browse open requests, submit bids
4. Admin reviews bids, awards to selected contractor
5. Referral fee tracked automatically

### API Endpoints

All under `/api/marketplace/`:
- `GET/POST /work-requests` — list/create work requests
- `GET /work-requests/{id}` — detail with bids
- `PUT /work-requests/{id}/award/{bid_id}` — award a bid
- `POST /contractors/register` — contractor registration
- `GET /contractors/open-requests` — browse open requests
- `POST /contractors/{id}/bid/{request_id}` — submit bid

## Authentication

### Dashboard (Google OAuth)

1. User clicks "Sign in with Google"
2. Redirected to Google OAuth consent screen
3. Code exchanged for access token
4. User email checked against `residents` table (scoped to HOA from subdomain)
5. Session cookie created (HTTPOnly, Secure, 7-day TTL)
6. Session contains: `id`, `email`, `name`, `unit`, `role`, `hoa_id`, `hoa_slug`

### Email Sender Verification

- SPF/DKIM/DMARC checked (bypassed in test mode)
- Sender must be in `residents` table with `is_authorized = TRUE` for the specific HOA

## Configuration

Environment variables (loaded via pydantic-settings from `.env`):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `GMAIL_CLIENT_ID` | Google OAuth client ID (dashboard login) |
| `GMAIL_CLIENT_SECRET` | Google OAuth client secret |
| `GCP_PROJECT_ID` | Vertex AI project |
| `VERTEX_AI_LOCATION` | Vertex AI region |
| `APP_SECRET_KEY` | Session cookie signing key |
| `RESEND_API_KEY` | Resend email provider API key |
| `EMAIL_PROVIDER` | `gmail` or `resend` |
| `EMAIL_WEBHOOK_SECRET` | Secret token for Resend webhook URL |
| `HOUSEKEEP_TEST_MODE` | Bypass DKIM/DMARC for testing |
| `DOMAIN` | Application domain |

## Deployment

Docker Compose stack on GCP Compute Engine:
- **Caddy** — reverse proxy, auto TLS (wildcard for `*.housekeep.click`)
- **HouseKeep** — FastAPI app (Python 3.12)
- **PostgreSQL 16** — with pgvector extension

### Database Migrations

Run in order:
```bash
scripts/init_db.sql                          # Base schema
scripts/migration_001_audit_enhancements.sql # Audit fields
scripts/migration_002_admin_answers.sql      # FAQ system
scripts/migrations/003_multi_tenancy.sql     # Multi-tenant (hoa_id)
scripts/migrations/004_email_provider.sql    # Email provider columns
scripts/migrations/005_hnsw_index.sql        # HNSW vector indexes
scripts/migrations/006_document_lineage.sql  # Document versioning
scripts/migrations/007_contractor_marketplace.sql # Marketplace tables
```

### HOA Onboarding

```bash
python scripts/manage.py create-hoa \
  --name "Twin Peaks HOA" \
  --slug twinpeaks \
  --admin-email george@gmail.com \
  --admin-name "George Lee"
```

## Testing

```bash
# Run all unit tests
pytest tests/ -v

# Run synthetic data dry-run
python -m scripts.testdata.run --dry-run

# Inject test emails into Gmail (testing)
python -m scripts.testdata.run --hoa-email test@gmail.com --method insert ...
```

Test coverage:
- `tests/test_chunking.py` — sentence-aware chunking (7 tests)
- `tests/test_confidence.py` — confidence computation + clarification logic (8 tests)
- `tests/test_processor.py` — MIME inference, null bytes, PDF/DOCX roundtrip (7 tests)
- `tests/test_tenant.py` — subdomain + email slug extraction (11 tests)
- `tests/test_scenarios.py` — synthetic data generation (9 tests)
