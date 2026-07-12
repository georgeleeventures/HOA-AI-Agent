# HouseKeep AI — Data Ontology

## Overview

Every document that HouseKeep AI ingests — whether it's an email attachment, a forwarded file, a scanned PDF, or a photo — is classified with a **category**, **subcategory**, and a set of **extracted metadata fields**. This taxonomy is the backbone of how documents are stored, searched, and presented to users.

The classification is performed automatically by the AI (Gemini 2.5 Flash) at ingestion time. Each document is analyzed and returned as structured JSON with category, subcategory, confidence score, and all applicable metadata fields.

---

## Classification Taxonomy

### Governing Documents

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| CC&Rs | Covenants, conditions, and restrictions | Effective date, amendment history, section index, key restrictions |
| TIC Agreement | Tenancy-in-common agreements | Ownership percentages per unit, parties, unit assignments, voting rights |
| Bylaws | Association bylaws, amendments | Voting thresholds, meeting requirements, officer roles, amendment dates |
| House Rules | Rules, policies, restrictions, guidelines | Specific rules by topic (pets, noise, parking, modifications, rentals) |

### Financial

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Budget | Annual/quarterly operating budgets | Line items, totals, fiscal year, variance from prior year |
| Reserve Study | Reserve fund analysis, projections | Current balance, projected needs, useful life estimates, funding plan |
| Assessment | HOA dues notices, special assessments | Amount, due date, unit, payment instructions, assessment type |
| Invoice/Receipt | Contractor invoices, payment receipts | Vendor name, amount, date, service description, unit (if applicable) |
| Tax | Property tax documents, HOA tax returns | Tax year, amounts, parcel numbers, filing status |

### Meeting

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Minutes | Board meeting minutes | Date, attendees, motions made, vote outcomes, action items, follow-ups |
| Agenda | Upcoming meeting agendas | Date, time, location, topics, expected attendees |
| Resolution | Board resolutions, formal votes | Resolution text, vote count (for/against/abstain), effective date |

### Maintenance

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Work Order | Repair requests, work descriptions | Unit, issue type, priority level, status, assigned contractor, completion date |
| Inspection | Inspection reports (fire, structural, pest, elevator) | Inspector name/company, date, findings, pass/fail, next inspection due |
| Photo/Evidence | Photos of damage, repairs, before/after shots | Date taken, location/unit, description, linked work order |
| Contractor Bid | Proposals, estimates, quotes | Vendor, scope of work, cost breakdown, timeline, expiration date |

### Insurance

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Policy | Insurance policies (liability, property, D&O) | Provider, policy number, coverage type, coverage limits, premium, expiration date |
| Claim | Insurance claims, adjuster correspondence | Claim number, incident date, incident description, status, payout amount |

### Legal

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Attorney | Legal correspondence, opinions, advice | Attorney/firm name, subject matter, date, advice summary |
| Dispute | Dispute records, formal complaints | Parties involved, nature of dispute, status, resolution (if any) |
| Lien/Violation | Lien notices, violation letters, fines | Unit, violation type, amount owed, deadline, cure instructions |

### Ownership

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Roster | Owner/tenant contact lists | Name, unit, email, phone, ownership percentage, move-in date |
| Deed/Title | Deeds, title documents, transfer records | Owner name, unit, recorded date, ownership percentage, recording number |
| Lease | Rental/lease agreements | Tenant name, unit, lease term, rent amount, landlord |

### Vendor

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Contract | Service contracts, maintenance agreements | Vendor, scope, term start/end, cost, auto-renewal terms, renewal date |
| Warranty | Warranties for completed work or equipment | Item/system, vendor, warranty start, expiration date, coverage scope |

### Correspondence

| Subcategory | Examples | Key Metadata Extracted |
|------------|----------|----------------------|
| Newsletter | HOA newsletters, community announcements | Date, topics covered, author |
| Notice | General notices to residents, rule reminders | Subject, date, action required (if any), deadline |
| Thread | Email thread (non-document conversation) | Participants, topic summary, date range, key decisions or outcomes |

---

## Classification Process

1. **Document arrives** — Either as an email attachment, a forwarded file, or extracted from an email thread.

2. **Text extraction** — If the document is a text-based PDF or email body, text is extracted directly using `pdfplumber` or `PyPDF2`. If it's a scanned PDF, image, or photo, it's sent to Gemini 2.5 Flash as a multimodal input for OCR.

3. **AI classification** — The extracted text (or raw image for scanned docs) is sent to Gemini with the classification prompt:

   ```
   Classify this document into one of the following categories and subcategories.
   Extract all applicable metadata fields. Return as JSON.

   Categories: Governing, Financial, Meeting, Maintenance, Insurance, Legal,
   Ownership, Vendor, Correspondence

   [Full subcategory and metadata field definitions provided]
   ```

4. **Structured response** — Gemini returns JSON:
   ```json
   {
     "category": "Governing",
     "subcategory": "House Rules",
     "confidence": 0.94,
     "title": "Tony Park Ridge HOA House Rules - Revised 2024",
     "metadata": {
       "effective_date": "2024-03-15",
       "topics": ["pets", "noise", "parking", "exterior_modifications"],
       "key_rules": [
         "No pets over 25 lbs without board approval",
         "Quiet hours 10pm-8am",
         "No exterior modifications without written approval"
       ]
     }
   }
   ```

5. **Storage** — The document, its extracted text, classification, and metadata are stored in PostgreSQL. The text is chunked and embedded for vector search.

---

## Handling Ambiguity

### Multi-Category Documents
Some documents span categories — for example, board meeting minutes that include a budget vote. In these cases:
- The document is classified under its **primary type** (Meeting > Minutes)
- Cross-references are stored in metadata (e.g., `"related_categories": ["Financial > Budget"]`)
- The full text is searchable regardless of classification, so budget-related queries will still surface meeting minutes that discuss budgets

### Unknown or Unclassifiable Documents
- If Gemini cannot confidently classify a document (confidence < 0.7), it is assigned to **Correspondence > Notice** as a default
- The document is flagged with `needs_review: true`
- Admins can review and reclassify flagged documents via the web dashboard

### Low-Confidence Classifications
- Confidence scores between 0.7 and 0.85 are accepted but logged for periodic review
- Confidence scores above 0.85 are accepted without flagging
- All classifications can be manually overridden by an admin

### Duplicate Detection
- Documents with high text similarity to existing documents are flagged as potential duplicates
- The system keeps both but links them, letting the admin decide which to keep as the canonical version

---

## PostgreSQL Schema

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT,                          -- Full extracted text
    raw_text TEXT,                         -- Original OCR output (before cleaning)
    metadata JSONB DEFAULT '{}',          -- All extracted metadata fields
    source_email_id VARCHAR(255),         -- Gmail message ID (if from email)
    source_filename VARCHAR(500),         -- Original filename (if attachment)
    file_type VARCHAR(50),               -- pdf, jpg, png, docx, etc.
    file_path VARCHAR(1000),             -- Path to stored file on disk
    confidence_score FLOAT,              -- AI classification confidence (0-1)
    needs_review BOOLEAN DEFAULT FALSE,  -- Flagged for admin review
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,        -- Order within the document
    embedding vector(768),               -- text-embedding-004 output
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for vector similarity search
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for filtering by category
CREATE INDEX idx_documents_category ON documents(category, subcategory);

-- Index for full-text search
CREATE INDEX idx_documents_content ON documents USING gin(to_tsvector('english', content));
```

---

## Category Summary

| Category | Subcategory Count | Sensitivity Level | Access |
|----------|------------------|-------------------|--------|
| Governing | 4 | Medium | All authorized residents |
| Financial | 5 | High | Board members and admin only (summaries available to residents) |
| Meeting | 3 | Medium | All authorized residents |
| Maintenance | 4 | Low | All authorized residents |
| Insurance | 2 | High | Board members and admin only |
| Legal | 3 | High | Board members and admin only |
| Ownership | 3 | High | Admin only (residents can see their own record) |
| Vendor | 2 | Medium | Board members and admin only |
| Correspondence | 3 | Low | All authorized residents |
