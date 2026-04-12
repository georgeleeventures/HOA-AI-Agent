# HouseKeep AI

An email-first AI agent for HOA (Homeowners Association) management. HouseKeep ingests your HOA's historical emails and documents, builds a searchable knowledge base, and lets residents and administrators ask questions via email or a simple web dashboard.

## Documentation

| Document | Description |
|----------|-------------|
| [Product One-Pager](docs/one-pager.md) | High-level product overview, target users, and value proposition |
| [Technical Build Guide](docs/build-guide.md) | Architecture, tech stack, Gmail API integration, RAG pipeline, database schema, build phases |
| [Data Ontology](docs/data-ontology.md) | Document classification taxonomy — categories, subcategories, and metadata fields |
| [Hosting & Deployment](docs/deployment.md) | GCP infrastructure, Terraform, Docker Compose, startup script, backup strategy |
| [Security Model](docs/security.md) | Threat model, email authentication, role-based access, data privacy, audit logging |
| [Sample Questions](docs/sample-questions.md) | Comprehensive question catalog organized by role (resident, board member, secretary, treasurer) |
| [User Guide](docs/user-guide.md) | Non-technical guide for residents and administrators |

## Tech Stack

- **Runtime:** Python 3.12+ / FastAPI
- **AI:** Google Vertex AI (Gemini 2.0 Flash + text-embedding-004)
- **Email:** Gmail API (OAuth2) with Pub/Sub push notifications
- **Database:** PostgreSQL 16 + pgvector
- **Hosting:** Single GCE VM (e2-micro, ~$7/mo) with Docker Compose
- **Reverse Proxy:** Caddy 2 (auto-TLS)

## Estimated Cost

~$16-29/month per HOA (VM + Vertex AI API usage + Pub/Sub).
