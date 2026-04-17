# HouseKeep AI — Contractor Marketplace

## Overview

The contractor marketplace connects HOAs with local service providers. When a maintenance issue is reported, HOA admins can create work requests. Contractors browse and bid on these requests. HouseKeep earns a referral fee when a contractor is selected.

## Revenue Model

- **Contractors register for free** (maximize supply)
- **Bidding is free** (encourage competitive pricing)
- **5% referral fee** when a contractor is awarded a job (tracked in `referral_tracking` table)
- **Payment**: manual invoicing initially, Stripe integration planned

## Database Schema

### `contractors`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| company_name | VARCHAR | Business name |
| contact_name | VARCHAR | Primary contact |
| email | VARCHAR | Unique, login identifier |
| phone | VARCHAR | Contact phone |
| license_number | VARCHAR | State contractor license |
| service_types | TEXT[] | e.g., `['plumbing', 'electrical']` |
| coverage_zipcodes | TEXT[] | Service area zip codes |
| is_verified | BOOLEAN | Admin-verified contractor |

### `work_requests`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| hoa_id | UUID | FK → hoas |
| title | VARCHAR | Short description |
| description | TEXT | Full details |
| service_type | VARCHAR | e.g., "plumbing" |
| urgency | VARCHAR | normal / urgent / emergency |
| status | VARCHAR | open / bidding / awarded / completed |
| budget_range_low/high | DECIMAL | Expected cost range |
| awarded_to | UUID | FK → contractors (when awarded) |

### `bids`
| Column | Type | Description |
|--------|------|-------------|
| work_request_id | UUID | FK → work_requests |
| contractor_id | UUID | FK → contractors |
| amount | DECIMAL | Bid amount |
| estimated_days | INTEGER | Timeline estimate |
| proposal | TEXT | Work description |
| status | VARCHAR | submitted / accepted / rejected |
| is_featured | BOOLEAN | Paid placement (future) |

### `referral_tracking`
Tracks revenue from contractor awards:
- `referral_type`: "awarded", "directory_click" (future)
- `fee_amount`: calculated as 5% of bid amount
- `is_paid` / `paid_at`: payment tracking

## API Endpoints

All under `/api/marketplace/`:

### For HOA Admins

| Method | Path | Description |
|--------|------|-------------|
| GET | `/work-requests` | List work requests (filter by status) |
| POST | `/work-requests` | Create work request |
| GET | `/work-requests/{id}` | Detail with bids |
| PUT | `/work-requests/{id}/award/{bid_id}` | Award bid to contractor |

### For Contractors

| Method | Path | Description |
|--------|------|-------------|
| POST | `/contractors/register` | Register new contractor |
| GET | `/contractors/open-requests` | Browse open work requests |
| POST | `/contractors/{id}/bid/{request_id}` | Submit a bid |

## Workflow

```
1. Maintenance Issue Detected
   (resident emails about water leak, broken fixture, etc.)
        ↓
2. HOA Admin Creates Work Request
   POST /api/marketplace/work-requests
   {title: "Kitchen plumbing repair", service_type: "plumbing", urgency: "normal"}
        ↓
3. Contractors Browse Open Requests
   GET /api/marketplace/contractors/open-requests?service_type=plumbing
        ↓
4. Contractor Submits Bid
   POST /api/marketplace/contractors/{id}/bid/{request_id}
   {amount: 850.00, estimated_days: 3, proposal: "Replace valve + inspect adjacent..."}
        ↓
5. HOA Admin Reviews Bids
   GET /api/marketplace/work-requests/{id}  (includes all bids)
        ↓
6. Admin Awards Bid
   PUT /api/marketplace/work-requests/{id}/award/{bid_id}
   → Contractor notified, other bids rejected
   → Referral fee (5% = $42.50) tracked in referral_tracking
        ↓
7. Work Completed
   Admin marks completed, adds to maintenance log
```

## Future Enhancements

- **Stripe integration** for automatic referral fee collection
- **Contractor verification** badge (license check, insurance verification)
- **Featured bids** — contractors pay for priority placement
- **Ratings and reviews** after work completion
- **Auto-create work requests** from maintenance emails using LLM classification
