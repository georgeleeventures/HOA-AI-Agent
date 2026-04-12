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
PROJECT_ID=$(curl -s -H "Metadata-Flavor: Google" \
    http://metadata.google.internal/computeMetadata/v1/project/project-id)

# Generate .env file
cat > .env <<EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://housekeep:${POSTGRES_PASSWORD}@postgres:5432/housekeep
DOMAIN=${DOMAIN}
GCP_PROJECT_ID=${PROJECT_ID}
VERTEX_AI_LOCATION=us-central1
APP_SECRET_KEY=$(openssl rand -hex 32)
EOF

# Generate Caddyfile
# If DOMAIN is empty or "ip-only", use :80 for plain HTTP access via IP
if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "ip-only" ]; then
    cat > Caddyfile <<EOF
:80 {
    reverse_proxy housekeep:8000
}
EOF
else
    cat > Caddyfile <<EOF
${DOMAIN} {
    reverse_proxy housekeep:8000
}
EOF
fi

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
    build: ./app-src
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
      - ./init_db.sql:/docker-entrypoint-initdb.d/init.sql
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

# Start services (build first)
docker compose up -d --build

# Mark setup as complete
touch "$SETUP_MARKER"
echo "=== HouseKeep AI: Setup complete ==="
