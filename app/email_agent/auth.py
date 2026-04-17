import logging

import asyncpg

logger = logging.getLogger(__name__)


def parse_auth_results(headers: list[dict]) -> dict:
    """Extract SPF/DKIM/DMARC results from Gmail message headers."""
    auth_results = {"spf": False, "dkim": False, "dmarc": False}

    for header in headers:
        if header.get("name", "").lower() == "authentication-results":
            value = header.get("value", "").lower()
            auth_results["spf"] = "spf=pass" in value
            auth_results["dkim"] = "dkim=pass" in value
            auth_results["dmarc"] = "dmarc=pass" in value
            break

    return auth_results


async def verify_sender(
    pool: asyncpg.Pool,
    sender_email: str,
    auth_results: dict,
    hoa_id: str,
) -> dict | None:
    """Verify that the sender is authorized to interact with HouseKeep.

    Returns the resident record if authorized, None otherwise.
    """
    # Require DKIM and DMARC to pass (skipped in test mode)
    from app.config import settings

    if settings.test_mode:
        logger.warning("TEST MODE: skipping DKIM/DMARC verification for %s", sender_email)
    elif not auth_results.get("dkim") or not auth_results.get("dmarc"):
        logger.warning(
            "Email authentication failed for %s: dkim=%s dmarc=%s",
            sender_email,
            auth_results.get("dkim"),
            auth_results.get("dmarc"),
        )
        return None

    # Look up sender in authorized residents
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, name, unit, role, ownership_pct
            FROM residents
            WHERE email = $1 AND hoa_id = $2 AND is_authorized = TRUE
            """,
            sender_email.lower().strip(),
            hoa_id,
        )

    if row is None:
        logger.info("Unknown sender: %s", sender_email)
        return None

    return dict(row)


async def resolve_hoa_from_email(
    pool: asyncpg.Pool, sender_email: str
) -> dict | None:
    """Look up the sender in residents across all HOAs.

    Used by the central Resend inbox path, where a single address
    (e.g. hello@housekeep.click) receives mail for every HOA and we
    identify the tenant by looking up the sender's email address.

    Returns a dict combining resident + HOA fields, or None if the sender
    is not an authorized resident of any active HOA.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT r.id, r.email, r.name, r.unit, r.role, r.hoa_id, r.ownership_pct,
                   h.slug AS hoa_slug, h.name AS hoa_name, h.email_address AS hoa_email
            FROM residents r
            JOIN hoas h ON r.hoa_id = h.id
            WHERE r.email = $1 AND r.is_authorized = TRUE AND h.is_active = TRUE
            ORDER BY r.created_at ASC
            LIMIT 1
            """,
            sender_email.lower().strip(),
        )
    return dict(row) if row else None
