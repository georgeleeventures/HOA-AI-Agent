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
) -> dict | None:
    """Verify that the sender is authorized to interact with HouseKeep.

    Returns the resident record if authorized, None otherwise.
    """
    # Require DKIM and DMARC to pass
    if not auth_results.get("dkim") or not auth_results.get("dmarc"):
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
            WHERE email = $1 AND is_authorized = TRUE
            """,
            sender_email.lower().strip(),
        )

    if row is None:
        logger.info("Unknown sender: %s", sender_email)
        return None

    return dict(row)
