"""Contractor marketplace REST API."""

import logging

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.database import get_pool
from app.tenant import get_hoa_id
from app.web.routes import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class WorkRequestCreate(BaseModel):
    title: str
    description: str | None = None
    service_type: str | None = None
    urgency: str = "normal"
    budget_range_low: float | None = None
    budget_range_high: float | None = None
    maintenance_log_id: str | None = None


class BidCreate(BaseModel):
    amount: float
    estimated_days: int | None = None
    proposal: str | None = None


class ContractorRegister(BaseModel):
    company_name: str
    contact_name: str | None = None
    email: str
    phone: str | None = None
    license_number: str | None = None
    service_types: list[str] = []
    coverage_zipcodes: list[str] = []
    bio: str | None = None
    website: str | None = None


def _serialize_row(row) -> dict:
    if row is None:
        return {}
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "hex"):
            d[k] = str(v)
        elif hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


# --- Work Requests (HOA Admin) ---


@router.get("/work-requests")
async def list_work_requests(request: Request, status: str | None = None):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    hoa_id = user.get("hoa_id") or get_hoa_id(request)

    pool = await get_pool()
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                """SELECT wr.*,
                   (SELECT count(*) FROM bids b WHERE b.work_request_id = wr.id) as bid_count
                   FROM work_requests wr
                   WHERE wr.hoa_id = $1 AND wr.status = $2
                   ORDER BY wr.created_at DESC""",
                hoa_id,
                status,
            )
        else:
            rows = await conn.fetch(
                """SELECT wr.*,
                   (SELECT count(*) FROM bids b WHERE b.work_request_id = wr.id) as bid_count
                   FROM work_requests wr
                   WHERE wr.hoa_id = $1
                   ORDER BY wr.created_at DESC""",
                hoa_id,
            )
    return [_serialize_row(r) for r in rows]


@router.post("/work-requests")
async def create_work_request(request: Request, body: WorkRequestCreate):
    user = get_current_user(request)
    if not user or user.get("role") not in ("admin", "board_member"):
        raise HTTPException(status_code=403)
    hoa_id = user.get("hoa_id") or get_hoa_id(request)

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO work_requests
               (hoa_id, title, description, service_type, urgency,
                budget_range_low, budget_range_high, maintenance_log_id, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               RETURNING *""",
            hoa_id,
            body.title,
            body.description,
            body.service_type,
            body.urgency,
            body.budget_range_low,
            body.budget_range_high,
            body.maintenance_log_id,
            user["email"],
        )
    return _serialize_row(row)


@router.get("/work-requests/{request_id}")
async def get_work_request(request: Request, request_id: str):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    hoa_id = user.get("hoa_id") or get_hoa_id(request)

    pool = await get_pool()
    async with pool.acquire() as conn:
        wr = await conn.fetchrow(
            "SELECT * FROM work_requests WHERE id = $1 AND hoa_id = $2",
            request_id,
            hoa_id,
        )
        if not wr:
            raise HTTPException(status_code=404)

        bids = await conn.fetch(
            """SELECT b.*, c.company_name, c.contact_name, c.phone,
                      c.license_number, c.is_verified
               FROM bids b JOIN contractors c ON b.contractor_id = c.id
               WHERE b.work_request_id = $1
               ORDER BY b.is_featured DESC, b.amount ASC""",
            request_id,
        )

    result = _serialize_row(wr)
    result["bids"] = [_serialize_row(b) for b in bids]
    return result


@router.put("/work-requests/{request_id}/award/{bid_id}")
async def award_bid(request: Request, request_id: str, bid_id: str):
    user = get_current_user(request)
    if not user or user.get("role") not in ("admin", "board_member"):
        raise HTTPException(status_code=403)
    hoa_id = user.get("hoa_id") or get_hoa_id(request)

    pool = await get_pool()
    async with pool.acquire() as conn:
        wr = await conn.fetchrow(
            "SELECT id FROM work_requests WHERE id = $1 AND hoa_id = $2",
            request_id,
            hoa_id,
        )
        if not wr:
            raise HTTPException(status_code=404)

        bid = await conn.fetchrow(
            "SELECT * FROM bids WHERE id = $1 AND work_request_id = $2",
            bid_id,
            request_id,
        )
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")

        await conn.execute(
            """UPDATE work_requests
               SET status = 'awarded', awarded_to = $1, awarded_at = NOW(), updated_at = NOW()
               WHERE id = $2""",
            bid["contractor_id"],
            request_id,
        )
        await conn.execute(
            "UPDATE bids SET status = 'accepted', updated_at = NOW() WHERE id = $1",
            bid_id,
        )
        await conn.execute(
            "UPDATE bids SET status = 'rejected', updated_at = NOW() WHERE work_request_id = $1 AND id != $2",
            request_id,
            bid_id,
        )

        await conn.execute(
            """INSERT INTO referral_tracking
               (work_request_id, contractor_id, hoa_id, referral_type, fee_amount)
               VALUES ($1, $2, $3, 'awarded', $4)""",
            request_id,
            bid["contractor_id"],
            hoa_id,
            float(bid["amount"]) * 0.05,
        )

    return {"status": "awarded", "bid_id": bid_id}


# --- Contractor endpoints ---


@router.post("/contractors/register")
async def register_contractor(body: ContractorRegister):
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """INSERT INTO contractors
                   (company_name, contact_name, email, phone, license_number,
                    service_types, coverage_zipcodes, bio, website)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                   RETURNING id, company_name, email""",
                body.company_name,
                body.contact_name,
                body.email,
                body.phone,
                body.license_number,
                body.service_types,
                body.coverage_zipcodes,
                body.bio,
                body.website,
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Email already registered")
    return _serialize_row(row)


@router.get("/contractors/open-requests")
async def list_open_requests(
    service_type: str | None = None,
):
    pool = await get_pool()
    conditions = ["wr.status = 'open'"]
    params: list = []
    idx = 1

    if service_type:
        conditions.append(f"wr.service_type = ${idx}")
        params.append(service_type)
        idx += 1

    where = "WHERE " + " AND ".join(conditions)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT wr.id, wr.title, wr.description, wr.service_type,
                       wr.urgency, wr.budget_range_low, wr.budget_range_high,
                       wr.created_at, h.name as hoa_name,
                       (SELECT count(*) FROM bids b WHERE b.work_request_id = wr.id) as bid_count
                FROM work_requests wr
                JOIN hoas h ON wr.hoa_id = h.id
                {where}
                ORDER BY wr.created_at DESC
                LIMIT 50""",
            *params,
        )
    return [_serialize_row(r) for r in rows]


@router.post("/contractors/{contractor_id}/bid/{request_id}")
async def submit_bid(contractor_id: str, request_id: str, body: BidCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        contractor = await conn.fetchrow(
            "SELECT id FROM contractors WHERE id = $1 AND is_active = TRUE",
            contractor_id,
        )
        if not contractor:
            raise HTTPException(status_code=404, detail="Contractor not found")

        wr = await conn.fetchrow(
            "SELECT id FROM work_requests WHERE id = $1 AND status = 'open'",
            request_id,
        )
        if not wr:
            raise HTTPException(status_code=404, detail="Work request not found or not open")

        try:
            row = await conn.fetchrow(
                """INSERT INTO bids
                   (work_request_id, contractor_id, amount, estimated_days, proposal)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING *""",
                request_id,
                contractor_id,
                body.amount,
                body.estimated_days,
                body.proposal,
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Already bid on this request")

    return _serialize_row(row)
