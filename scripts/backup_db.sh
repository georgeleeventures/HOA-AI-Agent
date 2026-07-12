#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="${HOUSEKEEP_COMPOSE_DIR:-/opt/housekeep}"

if [[ -f "${COMPOSE_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${COMPOSE_DIR}/.env"
    set +a
fi

: "${HOUSEKEEP_BACKUP_BUCKET:?HOUSEKEEP_BACKUP_BUCKET must be set}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$(mktemp "/tmp/housekeep-${timestamp}-XXXXXX.sql.gz")"
trap 'rm -f "${backup_file}"' EXIT

cd "${COMPOSE_DIR}"
docker compose exec -T postgres pg_dump -U housekeep -d housekeep \
    | gzip -9 > "${backup_file}"

gcloud storage cp \
    "${backup_file}" \
    "${HOUSEKEEP_BACKUP_BUCKET%/}/housekeep-${timestamp}.sql.gz"

echo "HouseKeep backup uploaded: housekeep-${timestamp}.sql.gz"
