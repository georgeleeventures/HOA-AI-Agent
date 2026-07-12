# HouseKeep AI — Hosting & Deployment Guide

## Hosting Strategy

HouseKeep AI runs on a **single Google Compute Engine e2-micro VM** with all services orchestrated via Docker Compose. In `us-central1`, this machine is eligible for GCP's monthly Free Tier when the billing account has not used its e2-micro allowance elsewhere.

**Why GCP:** Native Vertex AI/Gemini integration, Gmail API is a Google product, same ecosystem and Terraform patterns as existing infrastructure.

**Why a single VM (not managed services):** Cloud SQL + Cloud Run + Cloud Storage would cost 3-5x more with significantly more Terraform and configuration. For a single HOA with ~20 residents asking a few questions a day, the auto-scaling, auto-backup, and auto-patching benefits of managed services don't justify the cost or complexity. The upgrade path is clean — PostgreSQL is PostgreSQL whether it's on a VM or Cloud SQL, so migrating later is just a connection string change.

---

## Cost Breakdown

```
Monthly Cost (single HOA, approximately 200-1,000 questions):
├── GCE VM (e2-micro)                 $0     (Free Tier)
├── Standard persistent disk          $0     (within 30 GB account allowance)
├── Vertex AI / Gemini 2.5 Flash      ~$0.14-0.69
├── Vertex AI / embeddings            <$0.01 for a small HOA corpus
├── Static external IPv4              ~$3.65
├── GCS compressed backups            $0     (within 5 GB US allowance)
└── HouseKeep total                    ~$3.80-4.50
```

The current billing account also hosts an n8n e2-small VM. HouseKeep's 20 GB
disk and n8n's 10 GB disk consume the full 30 GB standard-disk allowance, so
do not add another persistent disk or snapshot when optimizing for Free Tier.
Domain registration and Resend charges are outside GCP.

Gemini thinking is disabled for RAG requests. Generation is limited to one
concurrent request, 768 output tokens, and 10,000 context characters. A $5
monthly budget monitors Vertex AI spend; the existing project-wide budget
continues to cover shared n8n and Compute Engine costs.

---

## Infrastructure (Terraform)

All infrastructure is defined in the `infra/` directory.

### `infra/main.tf` — Provider and APIs

```hcl
terraform {
  required_version = ">= 1.5"

  backend "gcs" {
    bucket = "housekeep-tf-state"
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "gmail.googleapis.com",
    "aiplatform.googleapis.com",
    "pubsub.googleapis.com",
    "iam.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}
```

### `infra/housekeep.tf` — VM, Firewall, IP

```hcl
# Service account
resource "google_service_account" "housekeep_vm" {
  account_id   = "housekeep-vm"
  display_name = "HouseKeep VM Service Account"
}

resource "google_project_iam_member" "logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.housekeep_vm.email}"
}

resource "google_project_iam_member" "vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.housekeep_vm.email}"
}

# Optional static IP
resource "google_compute_address" "housekeep" {
  count = var.use_static_ip ? 1 : 0
  name  = "housekeep-ip"
}

# Compute instance
resource "google_compute_instance" "housekeep" {
  name         = "housekeep-server"
  machine_type = var.machine_type  # default: e2-micro
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 20  # GB
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = var.use_static_ip ? google_compute_address.housekeep[0].address : null
    }
  }

  service_account {
    email  = google_service_account.housekeep_vm.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    domain          = var.domain
    postgres_password = var.postgres_password
  }

  metadata_startup_script = file("${path.module}/../setup.sh")

  tags = ["housekeep", "http-server", "https-server"]
}

# Firewall rules
resource "google_compute_firewall" "housekeep_web" {
  name    = "housekeep-allow-web"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["housekeep"]
}

resource "google_compute_firewall" "housekeep_ssh" {
  name    = "housekeep-allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["housekeep"]
}

# Pub/Sub topic for Gmail push notifications
resource "google_pubsub_topic" "gmail_notifications" {
  name = "gmail-notifications"
}

resource "google_pubsub_subscription" "gmail_push" {
  name  = "gmail-push-subscription"
  topic = google_pubsub_topic.gmail_notifications.name

  push_config {
    push_endpoint = "https://${var.domain}/webhooks/gmail"
  }

  ack_deadline_seconds = 20
}
```

### `infra/variables.tf`

```hcl
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "GCE machine type"
  type        = string
  default     = "e2-micro"
}

variable "domain" {
  description = "Domain name for the HouseKeep instance"
  type        = string
}

variable "use_static_ip" {
  description = "Whether to reserve a static IP"
  type        = bool
  default     = false
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}
```

### `infra/outputs.tf`

```hcl
output "vm_external_ip" {
  value = google_compute_instance.housekeep.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  value = "gcloud compute ssh housekeep-server --zone=${var.zone}"
}
```

---

## Docker Compose

### `docker-compose.yml`

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
    depends_on:
      - housekeep

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

### `Caddyfile`

```
{$DOMAIN} {
    reverse_proxy housekeep:8000
}
```

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.env.example`

```bash
# PostgreSQL
POSTGRES_PASSWORD=change-me-to-a-secure-password
DATABASE_URL=postgresql://housekeep:${POSTGRES_PASSWORD}@postgres:5432/housekeep

# Gmail API (from Google Cloud Console)
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token

# Google Cloud / Vertex AI
GCP_PROJECT_ID=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1

# Application
DOMAIN=housekeep.yourhoa.com
APP_SECRET_KEY=change-me-to-a-random-string
```

---

## Startup Script (`setup.sh`)

This runs automatically on the VM's first boot via Terraform's `metadata_startup_script`:

```bash
#!/bin/bash
set -e

SETUP_MARKER="/opt/housekeep/.setup-complete"

# Skip if already set up (e.g., on reboot)
if [ -f "$SETUP_MARKER" ]; then
    echo "Setup already complete, starting services..."
    cd /opt/housekeep
    docker compose up -d
    exit 0
fi

echo "=== HouseKeep AI: First-time setup ==="

# Install Docker
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Enable unattended security upgrades
apt-get install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

# Create application directory
mkdir -p /opt/housekeep
cd /opt/housekeep

# Pull configuration from VM metadata
DOMAIN=$(curl -s -H "Metadata-Flavor: Google" \
    http://metadata.google.internal/computeMetadata/v1/instance/attributes/domain)
POSTGRES_PASSWORD=$(curl -s -H "Metadata-Flavor: Google" \
    http://metadata.google.internal/computeMetadata/v1/instance/attributes/postgres_password)
EXTERNAL_IP=$(curl -s -H "Metadata-Flavor: Google" \
    http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)

# Generate .env file
cat > .env <<EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://housekeep:${POSTGRES_PASSWORD}@postgres:5432/housekeep
DOMAIN=${DOMAIN}
GCP_PROJECT_ID=$(curl -s -H "Metadata-Flavor: Google" \
    http://metadata.google.internal/computeMetadata/v1/project/project-id)
VERTEX_AI_LOCATION=us-central1
APP_SECRET_KEY=$(openssl rand -hex 32)
EOF

# Generate Caddyfile
cat > Caddyfile <<EOF
${DOMAIN} {
    reverse_proxy housekeep:8000
}
EOF

# Generate docker-compose.yml
cat > docker-compose.yml <<'COMPOSE'
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
    depends_on:
      - housekeep

  housekeep:
    image: housekeep-ai:latest
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
    env_file:
      - .env
    environment:
      POSTGRES_DB: housekeep
      POSTGRES_USER: housekeep
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
COMPOSE

# Start services
docker compose up -d

# Mark setup as complete
touch "$SETUP_MARKER"
echo "=== HouseKeep AI: Setup complete ==="
```

---

## Backup Strategy

Since we're not using Cloud SQL, we manage our own compressed database backups.
The production bucket is in `us-central1`, blocks public access, and deletes
objects after 30 days so backups remain well below the free storage allowance.

### Backup Script

The repository script `scripts/backup_db.sh` streams a PostgreSQL dump to a
temporary compressed file, uploads it with `gcloud storage cp`, and always
removes the local file. Set `HOUSEKEEP_BACKUP_BUCKET` to the destination URI.

### Cron Entry

```bash
# Run daily at 03:15 UTC
15 3 * * * root HOUSEKEEP_BACKUP_BUCKET=gs://sheer-dumb-luck-housekeep-backups /opt/housekeep/app-src/scripts/backup_db.sh >> /var/log/housekeep-backup.log 2>&1
```

### Setup

```bash
# The deployed cron definition is installed from:
sudo install -m 0644 scripts/housekeep-backup.cron /etc/cron.d/housekeep-backup
```

### Restoring from Backup

```bash
# Download the latest backup
gcloud storage cp gs://sheer-dumb-luck-housekeep-backups/housekeep_TIMESTAMP.sql.gz /tmp/housekeep.sql.gz

# Restore
gunzip < /tmp/housekeep.sql.gz | \
    docker compose exec -T postgres psql -U housekeep housekeep
```

---

## Deployment Steps

### First-Time Deployment

```bash
# 1. Initialize and apply Terraform
cd infra
terraform init
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars

# 2. Note the VM external IP from Terraform output
# 3. Point your domain's DNS A record to this IP

# 4. SSH into the VM
gcloud compute ssh housekeep-server --zone=us-central1-a

# 5. Run the Gmail OAuth2 flow to get the refresh token
# (This is done once, interactively on the VM)
python3 /opt/housekeep/scripts/gmail_setup.py

# 6. Add the refresh token to .env
echo "GMAIL_REFRESH_TOKEN=<token>" >> /opt/housekeep/.env

# 7. Restart the app to pick up the new token
cd /opt/housekeep
docker compose restart housekeep

# 8. Trigger baseline ingestion
curl -X POST https://yourdomain.com/admin/ingest

# 9. Verify the web dashboard is accessible
# Visit https://yourdomain.com in a browser
```

### Updating the Application

```bash
# SSH into the VM
gcloud compute ssh housekeep-server --zone=us-central1-a

# Pull latest code and rebuild
cd /opt/housekeep
git pull
docker compose build housekeep
docker compose up -d housekeep
```

### Keeping the VM in the Free Tier

```bash
# Verify the machine remains an e2-micro in an eligible region.
gcloud compute instances describe housekeep-server \
    --zone=us-central1-a \
    --format='value(machineType.basename(),zone.basename())'
```

Do not resize this deployment to e2-small: that machine type is not covered by
the Compute Engine Free Tier.

---

## Tradeoffs vs. Managed Services

| Concern | Reality on e2-micro | When It Actually Matters |
|---------|-------------------|------------------------|
| **Scaling** | 2 shared vCPUs, 1 GB RAM. Fine for one HOA with moderate traffic. PostgreSQL, FastAPI, and Caddy are all lightweight. | Only if serving 10+ HOAs on one VM or doing heavy concurrent ingestion. Fix: upgrade VM size (5 minutes). |
| **Database backups** | Cron job runs `pg_dump` to GCS daily. ~5 lines of script. | If the disk dies and you have no backup. The cron job prevents this. |
| **High availability** | If the VM goes down, everything is down. Cloud Run auto-restarts, Cloud SQL has replicas. | For an HOA with 20 residents, a few minutes of downtime is not a crisis. |
| **Disk space** | 20 GB boot disk. | A few thousand emails and dozens of documents won't come close. Resize disk if needed (`gcloud compute disks resize`). |
| **Security patching** | `unattended-upgrades` installed by the startup script — automatic. | Non-issue once configured. |
| **SSL/TLS** | Caddy handles this automatically via Let's Encrypt. | Actually easier than configuring Cloud Run with a custom domain. |

**Migration path:** If scale demands it later, the migration is straightforward:
1. Export PostgreSQL: `pg_dump` on the VM
2. Import to Cloud SQL: `gcloud sql import`
3. Update the app's `DATABASE_URL` environment variable
4. Deploy the app to Cloud Run instead of the VM
5. The application code doesn't change — only the infrastructure config.
