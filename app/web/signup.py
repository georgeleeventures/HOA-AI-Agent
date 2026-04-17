"""HOA signup flow: create new HOA + first admin."""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import settings
from app.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


class SignupRequest(BaseModel):
    hoa_name: str
    hoa_slug: str
    admin_email: str
    admin_name: str | None = None


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:50]


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.post("/signup")
async def create_hoa(body: SignupRequest):
    """Create a new HOA + first admin, send magic code to admin email."""
    hoa_name = body.hoa_name.strip()
    admin_email = body.admin_email.lower().strip()
    admin_name = (body.admin_name or admin_email.split("@")[0]).strip()
    slug = _slugify(body.hoa_slug or hoa_name)

    if not hoa_name or not admin_email or "@" not in admin_email:
        raise HTTPException(status_code=400, detail="Invalid input")
    if len(slug) < 2:
        raise HTTPException(status_code=400, detail="HOA slug must be at least 2 characters")

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing_slug = await conn.fetchval("SELECT id FROM hoas WHERE slug = $1", slug)
        if existing_slug:
            raise HTTPException(status_code=409, detail="HOA slug already taken")

        email_taken = await conn.fetchval(
            "SELECT id FROM residents WHERE email = $1 LIMIT 1", admin_email
        )
        if email_taken:
            raise HTTPException(
                status_code=409,
                detail="This email is already associated with an HOA. Sign in instead.",
            )

        hoa_row = await conn.fetchrow(
            """
            INSERT INTO hoas (name, slug, email_address)
            VALUES ($1, $2, $3)
            RETURNING id, name, slug
            """,
            hoa_name,
            slug,
            settings.housekeep_inbound_email,
        )

        await conn.execute(
            """
            INSERT INTO residents (hoa_id, email, name, role, is_authorized)
            VALUES ($1, $2, $3, 'admin', TRUE)
            """,
            hoa_row["id"],
            admin_email,
            admin_name,
        )

    # Send verification code
    try:
        code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)

        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO email_codes (email, code, expires_at) VALUES ($1, $2, $3)",
                admin_email,
                code,
                expires_at,
            )

        from app.email.resend_provider import ResendProvider

        provider = ResendProvider()
        await provider.send(
            from_email=f"HouseKeep <noreply@{settings.resend_sending_domain}>",
            to=admin_email,
            subject="Welcome to HouseKeep — verify your email",
            body=(
                f"Welcome to HouseKeep!\n\n"
                f"Your HOA '{hoa_name}' has been created.\n\n"
                f"Verify your email with this 6-digit code: {code}\n\n"
                f"This code expires in 10 minutes.\n\n"
                f"Sign in at https://{settings.resend_sending_domain}/auth/login\n\n"
                f"— HouseKeep"
            ),
        )
    except Exception:
        logger.exception("Failed to send signup verification email to %s", admin_email)

    return {
        "status": "ok",
        "hoa_id": str(hoa_row["id"]),
        "hoa_slug": hoa_row["slug"],
        "message": f"HOA '{hoa_name}' created. Check {admin_email} for a verification code.",
        "next_step": "/auth/login",
    }
