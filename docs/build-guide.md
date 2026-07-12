# HouseKeep AI — Technical Build Guide

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Runtime** | Python 3.12+ | Best ecosystem for AI/ML, Gmail API client libraries, document processing |
| **LLM** | Google Vertex AI (Gemini 2.5 Flash) | Cost-effective, strong multimodal/OCR, native GCP integration |
| **Embedding Model** | Google text-embedding-004 via Vertex AI | 768-dimensional vectors, $0.000025 per 1K characters |
| **Email Integration** | Gmail API (OAuth2) | Full programmatic access to threads, attachments, and push notifications |
| **Database** | PostgreSQL 16 + pgvector | Single database for structured data and vector embeddings, no external service |
| **Document Processing** | Gemini 2.5 Flash (multimodal) | OCR + classification + metadata extraction in a single API call |
| **Text Extraction** | PyPDF2 / pdfplumber | Extract text from non-scanned PDFs before sending to Gemini for classification |
| **Web Framework** | FastAPI | Lightweight, async, auto-generated OpenAPI docs |
| **Web Frontend** | HTML/CSS/JS with Jinja2 templates (or lightweight React) | Minimal frontend — chat interface, document browser, admin panel |
| **Reverse Proxy** | Caddy 2 | Automatic TLS via Let's Encrypt, simple Caddyfile config |
| **Hosting** | Single GCE VM (e2-micro) + Docker Compose | Free-tier eligible; public IPv4 is the main fixed cost |
| **File Storage** | Local disk (Docker volume) | Attachments stored on VM, no external storage service |
| **Auth** | Google OAuth2 | Residents sign in with their Google account, email maps to authorization |

---

## Gmail API Integration

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (e.g., "housekeep-ai")
3. Enable the following APIs:
   - Gmail API
   - Cloud Pub/Sub API (for email push notifications)
   - Vertex AI API (for Gemini and embeddings)

### Step 2: Configure OAuth2 Consent Screen

1. Navigate to APIs & Services > OAuth consent screen
2. Choose "External" user type (or "Internal" if using Google Workspace)
3. Fill in app name ("HouseKeep AI"), support email, and authorized domains
4. Add scopes:
   - `https://www.googleapis.com/auth/gmail.readonly` — Read emails and attachments
   - `https://www.googleapis.com/auth/gmail.send` — Send AI-generated responses
   - `https://www.googleapis.com/auth/gmail.modify` — Mark emails as read, apply labels
5. Add the HOA admin's email as a test user (required during development)

### Step 3: Generate OAuth2 Credentials

1. Navigate to APIs & Services > Credentials
2. Create an OAuth 2.0 Client ID (type: Web application)
3. Set authorized redirect URI to `http://localhost:8080/oauth/callback` (for initial setup)
4. Download the client configuration — this gives you the **Client ID** and **Client Secret**

### Step 4: Admin Authorization Flow

This is a one-time action performed by the HOA administrator:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]

flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
credentials = flow.run_local_server(port=8080)

# Save the refresh token — this is what we store
print(f"Refresh token: {credentials.refresh_token}")
```

The admin visits the URL, signs into the HOA Gmail account, clicks "Allow," and the app receives a **refresh token**. This token is stored securely as an environment variable on the VM and grants ongoing access without requiring the admin to re-authenticate.

### Step 5: Ongoing Access

With the refresh token, the app can:

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

credentials = Credentials(
    token=None,
    refresh_token=GMAIL_REFRESH_TOKEN,
    client_id=GMAIL_CLIENT_ID,
    client_secret=GMAIL_CLIENT_SECRET,
    token_uri='https://oauth2.googleapis.com/token',
)

gmail = build('gmail', 'v1', credentials=credentials)
```

### Key Gmail API Methods

| Method | Purpose |
|--------|---------|
| `messages.list` | List all messages matching a query (used for baseline ingestion) |
| `messages.get` | Fetch a single message with full content and attachment metadata |
| `attachments.get` | Download a specific attachment by ID |
| `messages.send` | Send an AI-generated response email |
| `users.watch` | Register for Pub/Sub push notifications when new emails arrive |
| `users.labels.list` | List Gmail labels for organizing processed emails |

### Baseline Ingestion

The initial bulk pull fetches all historical emails:

```python
async def ingest_all_emails(gmail_service):
    """One-time baseline ingestion of all historical emails."""
    page_token = None
    total_processed = 0

    while True:
        results = gmail_service.users().messages().list(
            userId='me',
            pageToken=page_token,
            maxResults=500
        ).execute()

        messages = results.get('messages', [])
        for msg_meta in messages:
            msg = gmail_service.users().messages().get(
                userId='me',
                id=msg_meta['id'],
                format='full'
            ).execute()
            await process_email(msg)
            total_processed += 1

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return total_processed
```

After the baseline, new emails are processed incrementally via Pub/Sub push notifications.

### Push Notifications (Pub/Sub Watch)

```python
def setup_email_watch(gmail_service):
    """Register for push notifications on new emails."""
    request = {
        'labelIds': ['INBOX'],
        'topicName': 'projects/housekeep-ai/topics/gmail-notifications'
    }
    gmail_service.users().watch(userId='me', body=request).execute()
    # Watch expires after 7 days — set up a cron to re-register
```

When a new email arrives, Google sends a notification to the Pub/Sub topic, which triggers the HouseKeep app to fetch and process the new message.

---

## Document Classification & OCR

### Approach: Gemini Multimodal

Rather than using a separate OCR service, we send documents directly to Gemini 2.5 Flash. For scanned PDFs and images, Gemini performs OCR, classification, and metadata extraction in a single API call.

### For Scanned PDFs / Images (OCR Required)

```python
import json

from google import genai
from google.genai import types

client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT_ID,
    location="us-central1",
)

def classify_scanned_document(file_bytes: bytes, mime_type: str) -> dict:
    """OCR + classify a scanned document in one Gemini call."""
    document_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[CLASSIFICATION_PROMPT, document_part],
        config=types.GenerateContentConfig(
            max_output_tokens=512,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    return json.loads(response.text)
```

### For Text-Based PDFs (No OCR Needed)

```python
import pdfplumber

def classify_text_document(pdf_path: str) -> dict:
    """Extract text from PDF, then classify with Gemini."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[CLASSIFICATION_PROMPT, f"Document text:\n{text}"],
        config=types.GenerateContentConfig(
            max_output_tokens=512,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    return json.loads(response.text)
```

### Classification Prompt

```python
CLASSIFICATION_PROMPT = """
Classify this HOA document into one of the following categories and subcategories.
Extract all applicable metadata fields. Return valid JSON only.

Categories and subcategories:
- Governing: CC&Rs, TIC Agreement, Bylaws, House Rules
- Financial: Budget, Reserve Study, Assessment, Invoice/Receipt, Tax
- Meeting: Minutes, Agenda, Resolution
- Maintenance: Work Order, Inspection, Photo/Evidence, Contractor Bid
- Insurance: Policy, Claim
- Legal: Attorney, Dispute, Lien/Violation
- Ownership: Roster, Deed/Title, Lease
- Vendor: Contract, Warranty
- Correspondence: Newsletter, Notice, Thread

Return format:
{
  "category": "...",
  "subcategory": "...",
  "confidence": 0.0-1.0,
  "title": "...",
  "metadata": {
    // All applicable fields for this document type
  }
}
"""
```

### Cost

- Gemini 2.5 Flash: usage-based Vertex AI pricing; thinking is disabled to control output cost
- A typical document classification: ~1K-5K input tokens = $0.0001-0.0005 per document
- Baseline ingestion of 1,000 documents: ~$0.10-0.50 total

---

## Embedding Generation & RAG Pipeline

### How Embeddings Work

Embeddings convert text into 768-dimensional numerical vectors. Similar texts produce similar vectors, enabling semantic search — "roof leak" matches "water damage on ceiling" even without shared keywords.

### Chunking Strategy

```python
def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split document into overlapping chunks for embedding."""
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap  # Overlap to preserve context at boundaries

    return chunks
```

### Generating Embeddings

```python
from vertexai.language_models import TextEmbeddingModel

embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

def embed_text(text: str) -> list[float]:
    """Generate a 768-dimensional embedding vector."""
    embeddings = embedding_model.get_embeddings([text])
    return embeddings[0].values  # list of 768 floats
```

### Storing in pgvector

```python
import asyncpg

async def store_chunk(conn, document_id: str, chunk_text: str, chunk_index: int):
    embedding = embed_text(chunk_text)
    await conn.execute("""
        INSERT INTO document_chunks (document_id, chunk_text, chunk_index, embedding)
        VALUES ($1, $2, $3, $4)
    """, document_id, chunk_text, chunk_index, embedding)
```

### RAG Query Flow

When a user asks a question:

1. **Embed the question** using the same `text-embedding-004` model
2. **Vector search** in pgvector for the top-K most similar chunks
3. **Assemble context** from the matched chunks + their source document metadata
4. **Generate answer** with Gemini, grounded in the retrieved context

```python
async def answer_question(conn, question: str) -> str:
    # 1. Embed the question
    question_embedding = embed_text(question)

    # 2. Vector search for top 5 relevant chunks
    rows = await conn.fetch("""
        SELECT dc.chunk_text, d.title, d.category, d.subcategory
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        ORDER BY dc.embedding <=> $1  -- cosine distance
        LIMIT 5
    """, question_embedding)

    # 3. Assemble context
    context = "\n\n".join([
        f"[{r['category']} > {r['subcategory']} — {r['title']}]\n{r['chunk_text']}"
        for r in rows
    ])

    # 4. Generate answer with Gemini
    response = model.generate_content([
        f"""Answer the following question using ONLY the provided context.
        Cite the source document for each claim. If the answer is not in the
        context, say "I don't have information about that in our records."

        Context:
        {context}

        Question: {question}"""
    ])

    return response.text
```

---

## System Architecture

All services run on a single GCE VM via Docker Compose:

```
┌──────────────────── GCE VM (free-tier e2-micro) ────────────────────┐
│                                                                     │
│  Docker Compose                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐ │  │
│  │  │   Caddy 2     │  │  HouseKeep    │  │  PostgreSQL 16     │ │  │
│  │  │  (reverse     │  │  (Python/     │  │  + pgvector        │ │  │
│  │  │   proxy)      │──│   FastAPI)    │──│  (all data +       │ │  │
│  │  │  :80, :443    │  │  :8000        │  │   embeddings)      │ │  │
│  │  └──────────────┘  └───────┬───────┘  └────────────────────┘ │  │
│  │                            │                                  │  │
│  │           ┌────────────────┼────────────────┐                 │  │
│  │           │                │                │                 │  │
│  │     Gmail API       Vertex AI API     Local Disk              │  │
│  │     (read/send      (Gemini Flash     (attachments            │  │
│  │      emails)         + embeddings)     stored as files)       │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Docker Volumes: postgres_data, housekeep_attachments, caddy_data   │
└─────────────────────────────────────────────────────────────────────┘
```

**Three containers, one VM, one `docker-compose.yml`:**

1. **Caddy** — Reverse proxy with automatic HTTPS (Let's Encrypt). Routes traffic to the FastAPI app.
2. **HouseKeep** — The Python/FastAPI application. Handles email processing, RAG queries, the web dashboard, and background ingestion tasks.
3. **PostgreSQL 16 + pgvector** — All structured data (documents, emails, residents, maintenance logs, financials) plus vector embeddings for semantic search.

---

## Build Phases

### Phase 1: Foundation (Core Ingestion)

| # | Module | Description |
|---|--------|-------------|
| 1 | Gmail Connector | OAuth2 setup, fetch all historical emails + attachments via Gmail API |
| 2 | Document Processor | Extract text from PDFs (pdfplumber), OCR scanned docs (Gemini multimodal), classify all documents against the taxonomy |
| 3 | Knowledge Base Builder | Chunk documents into ~500-token segments, generate embeddings via text-embedding-004, store in pgvector |
| 4 | RAG Pipeline | Accept a question, embed it, vector search for relevant chunks, generate a grounded answer with Gemini, return with source citations |

**Milestone:** Can connect to a Gmail account, ingest all history, and answer questions via a Python REPL or simple API endpoint.

### Phase 2: Email Agent

| # | Module | Description |
|---|--------|-------------|
| 5 | Email Listener | Gmail Pub/Sub watch for push notifications on new emails. Parse and route incoming messages. |
| 6 | Sender Authorization | Look up sender email in the authorized residents table. Verify SPF/DKIM/DMARC headers. Reject unauthorized senders gracefully. |
| 7 | Intent Classifier | Determine what the sender wants: asking a question, reporting maintenance, forwarding a document, or just a thread the agent is CC'd on. |
| 8 | Response Generator | RAG-powered response with document citations. Compose and send via Gmail API. |
| 9 | Thread Tracker | When CC'd on a thread, silently log the conversation without responding. Only respond when directly addressed. |

**Milestone:** The agent processes incoming emails, answers authorized questions, logs threads, and files forwarded documents — all automatically.

### Phase 3: Web Dashboard

| # | Module | Description |
|---|--------|-------------|
| 10 | Auth & Roles | Google OAuth2 login. Map user's Google email to authorized residents table. Enforce role-based access on every route. |
| 11 | Chat Interface | Simple chat UI for querying the RAG pipeline. Shows answers with source citations and suggested follow-up questions. |
| 12 | Document Browser | Browse documents by category/subcategory. Search, filter, and view individual documents. |
| 13 | Maintenance Timeline | Calendar or timeline view of maintenance events extracted from emails and work orders. |

**Milestone:** Residents and board members can log in, chat with the AI, browse categorized documents, and view maintenance history.

### Phase 4: Smart Features

| # | Module | Description |
|---|--------|-------------|
| 14 | Meeting Notes Summarizer | Auto-summarize forwarded meeting notes. Extract action items, decisions, and follow-ups. |
| 15 | Budget Tracker | Extract financial data from ingested documents. Track budget vs. actual, flag anomalies, project reserve fund balance. |
| 16 | Contractor Suggestions | When maintenance needs arise, suggest vetted local contractors. (Monetization feature.) |
| 17 | Compliance Checker | Answer "Can I do X?" questions by checking governing documents. Cite specific sections of CC&Rs, bylaws, and house rules. |

**Milestone:** Full-featured HOA AI assistant with meeting summarization, financial tracking, contractor recommendations, and compliance checking.

---

## Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

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
    processed BOOLEAN DEFAULT FALSE,
    received_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Residents: authorized users and their roles
CREATE TABLE residents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(500) UNIQUE NOT NULL,
    name VARCHAR(500),
    unit VARCHAR(50),
    role VARCHAR(50) DEFAULT 'resident',  -- resident, board_member, admin
    ownership_pct FLOAT,
    is_authorized BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Maintenance log: tracked maintenance events
CREATE TABLE maintenance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit VARCHAR(50),
    description TEXT,
    issue_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'reported',  -- reported, in_progress, completed
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
    channel VARCHAR(50),  -- email, web_chat
    action VARCHAR(100),  -- question, document_forward, thread_cc
    query TEXT,
    response_summary TEXT,
    documents_cited JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_documents_category ON documents(category, subcategory);
CREATE INDEX idx_documents_content ON documents USING gin(to_tsvector('english', content));
CREATE INDEX idx_emails_thread ON emails(thread_id);
CREATE INDEX idx_emails_sender ON emails(sender);
CREATE INDEX idx_residents_email ON residents(email);
CREATE INDEX idx_maintenance_unit ON maintenance_log(unit);
CREATE INDEX idx_audit_user ON audit_log(user_email);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

---

## Python Dependencies

### Core

```
# requirements.txt

# Web framework
fastapi==0.115.*
uvicorn[standard]==0.32.*
jinja2==3.1.*
python-multipart==0.0.*

# Gmail API
google-api-python-client==2.150.*
google-auth-oauthlib==1.2.*
google-auth-httplib2==0.2.*

# Vertex AI (Gemini + Embeddings)
google-cloud-aiplatform==1.72.*

# PostgreSQL
asyncpg==0.30.*
pgvector==0.3.*

# PDF processing
pdfplumber==0.11.*
PyPDF2==3.0.*

# Email parsing
python-dateutil==2.9.*

# Environment / config
python-dotenv==1.0.*
pydantic-settings==2.6.*

# Security
dkimpy==1.1.*
authheaders==0.16.*
```

---

## Docker Compose Reference

```yaml
version: "3.8"

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

  housekeep:
    build: .
    restart: unless-stopped
    expose:
      - "8000"
    env_file:
      - .env
    volumes:
      - housekeep_attachments:/app/attachments
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: housekeep
      POSTGRES_USER: housekeep
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U housekeep"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  caddy_data:
  caddy_config:
  housekeep_attachments:
  postgres_data:
```

### Caddyfile

```
{$DOMAIN} {
    reverse_proxy housekeep:8000
}
```

---

## Environment Variables

```bash
# .env

# PostgreSQL
POSTGRES_PASSWORD=<secure-random-password>
DATABASE_URL=postgresql://housekeep:${POSTGRES_PASSWORD}@postgres:5432/housekeep

# Gmail API
GMAIL_CLIENT_ID=<from-gcp-console>
GMAIL_CLIENT_SECRET=<from-gcp-console>
GMAIL_REFRESH_TOKEN=<from-oauth-flow>

# Google Cloud / Vertex AI
GCP_PROJECT_ID=housekeep-ai
VERTEX_AI_LOCATION=us-central1

# App
DOMAIN=housekeep.yourhoa.com
APP_SECRET_KEY=<secure-random-key>
```
