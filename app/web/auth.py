"""Passwordless magic-code authentication."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import settings
from app.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

CODE_EXPIRY_MINUTES = 10
RATE_LIMIT_CODES_PER_HOUR = 5
SESSION_COOKIE = "housekeep_session"


class SendCodeRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


def _generate_code() -> str:
    """Generate a random 6-digit numeric code."""
    return f"{secrets.randbelow(1000000):06d}"


def _get_serializer():
    from itsdangerous import URLSafeSerializer
    return URLSafeSerializer(settings.app_secret_key)


@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Passwordless login page (email + code flow)."""
    return templates.TemplateResponse("auth_login.html", {"request": request})


@router.post("/auth/send-code")
async def send_code(body: SendCodeRequest):
    """Send a 6-digit magic code to the given email (via Resend)."""
    email = body.email.lower().strip()
    if "@" not in email or len(email) < 5:
        raise HTTPException(status_code=400, detail="Invalid email")

    pool = await get_pool()

    async with pool.acquire() as conn:
        recent_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM email_codes
            WHERE email = $1 AND created_at > NOW() - INTERVAL '1 hour'
            """,
            email,
        )
    if recent_count and recent_count >= RATE_LIMIT_CODES_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many codes requested. Try again in an hour.",
        )

    # Check if user exists (but don't reveal the result — always return 200)
    async with pool.acquire() as conn:
        resident = await conn.fetchrow(
            "SELECT email FROM residents WHERE email = $1 AND is_authorized = TRUE LIMIT 1",
            email,
        )

    # Always generate + store (prevents enumeration via timing)
    code = _generate_code()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        minutes=CODE_EXPIRY_MINUTES
    )
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO email_codes (email, code, expires_at) VALUES ($1, $2, $3)",
            email,
            code,
            expires_at,
        )

    # Only actually send the email if the user is registered
    if resident:
        try:
            from app.email.resend_provider import ResendProvider

            provider = ResendProvider()
            await provider.send(
                from_email=f"HouseKeep <noreply@{settings.resend_sending_domain}>",
                to=email,
                subject=f"Your HouseKeep login code: {code}",
                body=(
                    f"Your 6-digit login code is: {code}\n\n"
                    f"This code expires in {CODE_EXPIRY_MINUTES} minutes.\n\n"
                    f"If you didn't request this, you can safely ignore this email.\n\n"
                    f"— HouseKeep"
                ),
            )
        except Exception:
            logger.exception("Failed to send magic code email to %s", email)

    # Always return success (prevents email enumeration)
    return {"status": "sent", "message": "If the email is registered, a code has been sent."}


@router.post("/auth/verify-code")
async def verify_code(body: VerifyCodeRequest):
    """Verify a 6-digit code and create a session."""
    email = body.email.lower().strip()
    code = body.code.strip()

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, expires_at FROM email_codes
            WHERE email = $1 AND code = $2 AND used_at IS NULL AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """,
            email,
            code,
        )

        if not row:
            raise HTTPException(status_code=401, detail="Invalid or expired code")

        await conn.execute(
            "UPDATE email_codes SET used_at = NOW() WHERE id = $1",
            row["id"],
        )

        resident = await conn.fetchrow(
            """
            SELECT r.id, r.email, r.name, r.unit, r.role, r.hoa_id,
                   h.slug AS hoa_slug, h.name AS hoa_name
            FROM residents r
            JOIN hoas h ON r.hoa_id = h.id
            WHERE r.email = $1 AND r.is_authorized = TRUE
            ORDER BY r.created_at ASC
            LIMIT 1
            """,
            email,
        )

    if not resident:
        raise HTTPException(status_code=403, detail="Email not registered with any HOA")

    session_data = {
        "id": str(resident["id"]),
        "email": resident["email"],
        "name": resident["name"],
        "unit": resident["unit"],
        "role": resident["role"],
        "hoa_id": str(resident["hoa_id"]),
        "hoa_slug": resident["hoa_slug"],
        "hoa_name": resident["hoa_name"],
    }
    cookie_value = _get_serializer().dumps(session_data)

    # Return JSONResponse with cookie attached (so set_cookie actually applies)
    response = JSONResponse(content={"status": "ok", "redirect": "/"})
    response.set_cookie(
        SESSION_COOKIE,
        cookie_value,
        httponly=True,
        secure=settings.domain != "localhost",
        samesite="lax",
        max_age=86400 * 7,
    )
    return response
