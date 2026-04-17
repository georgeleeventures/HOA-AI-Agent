# HouseKeep AI — Multi-Tenancy Guide

## Overview

HouseKeep AI supports multiple HOAs in a single deployment. Each HOA has isolated data — documents, residents, emails, audit logs — enforced at both the application and database level.

## How Isolation Works

### 1. Application Layer

Every SQL query includes `WHERE hoa_id = $N`. The `hoa_id` is resolved from:
- **Web requests**: subdomain in the `Host` header (via `TenantMiddleware`)
- **Email webhooks**: `To:` address (e.g., `board@twinpeaks.housekeep.click`)
- **Session cookie**: stored after login, includes `hoa_id` and `hoa_slug`

### 2. Database Layer (RLS Safety Net)

PostgreSQL Row-Level Security is enabled on all tenant-scoped tables. If a query accidentally omits `hoa_id`, RLS prevents data leakage:

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_tenant ON documents
    USING (hoa_id = current_setting('app.current_hoa_id', true)::uuid);
```

The app user has `BYPASSRLS` for normal operations — RLS is a last-resort safety net, not the primary isolation mechanism.

## Subdomain Routing

Each HOA gets a subdomain: `{slug}.housekeep.click`

The `TenantMiddleware` (`app/tenant.py`) extracts the slug from the `Host` header:

| Host | Slug | Result |
|------|------|--------|
| `twinpeaks.housekeep.click` | `twinpeaks` | HOA resolved |
| `housekeep.click` | None | Landing page |
| `localhost:8000` | None | Dev fallback |
| `twinpeaks.localhost` | `twinpeaks` | Local dev |

## Session Management

After Google OAuth login, the session cookie contains:
```json
{
  "id": "resident-uuid",
  "email": "george@gmail.com",
  "name": "George Lee",
  "unit": "1",
  "role": "admin",
  "hoa_id": "hoa-uuid",
  "hoa_slug": "twinpeaks"
}
```

All API endpoints read `hoa_id` from the session: `user.get("hoa_id")`.

## Database Migration

Run `scripts/migrations/003_multi_tenancy.sql` on an existing database:

```bash
# Via Docker on the VM
cd /opt/housekeep && sudo docker compose exec -T postgres \
  psql -U housekeep housekeep < /path/to/003_multi_tenancy.sql
```

The migration:
1. Creates `hoas` table
2. Inserts a default HOA for existing data
3. Adds `hoa_id` to all 8 tables (nullable → backfill → NOT NULL)
4. Updates unique constraints (residents: `UNIQUE(hoa_id, email)`)
5. Adds composite indexes
6. Enables RLS with tenant policies

## HOA Onboarding

Use the management CLI:

```bash
# Create a new HOA
python scripts/manage.py create-hoa \
  --name "Twin Peaks HOA" \
  --slug twinpeaks \
  --admin-email george@gmail.com \
  --admin-name "George Lee"

# List all HOAs
python scripts/manage.py list-hoas
```

This creates the HOA record and the first admin resident. The admin can then invite other residents via the dashboard.

## Testing Tenant Isolation

1. Create two HOAs (A and B)
2. Add documents to HOA A
3. Log in as HOA B admin
4. Query for documents → should return zero results
5. Verify via SQL: `SELECT * FROM documents WHERE hoa_id = 'hoa-b-id'` returns nothing

Tests in `tests/test_tenant.py` verify slug extraction logic.
