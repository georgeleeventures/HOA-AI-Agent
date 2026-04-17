"""Multi-tenancy middleware: resolves HOA from subdomain."""

import logging

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import get_pool

logger = logging.getLogger(__name__)

# Paths that don't require tenant resolution
PUBLIC_PATHS = {"/", "/health", "/favicon.ico", "/signup", "/login", "/logout"}
WEBHOOK_PREFIX = "/webhooks/"
PUBLIC_PREFIXES = ("/static", "/auth/", "/oauth/")


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve HOA from subdomain and attach to request state.

    Routes:
    - {slug}.housekeep.click → look up HOA by slug
    - housekeep.click (no subdomain) → landing page (no hoa_id)
    - /webhooks/* → HOA resolved from payload, not subdomain
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Webhooks resolve tenant from payload, not subdomain
        if path.startswith(WEBHOOK_PREFIX):
            request.state.hoa_id = None
            request.state.hoa = None
            return await call_next(request)

        # Public paths don't need tenant
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            request.state.hoa_id = None
            request.state.hoa = None
            return await call_next(request)

        # Extract subdomain from Host header
        host = request.headers.get("host", "")
        slug = self._extract_slug(host)

        if not slug:
            # No subdomain — serve landing page or pass through
            request.state.hoa_id = None
            request.state.hoa = None
            return await call_next(request)

        # Look up HOA by slug
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, slug, email_address, settings FROM hoas WHERE slug = $1 AND is_active = TRUE",
                slug,
            )

        if not row:
            raise HTTPException(status_code=404, detail="HOA not found")

        request.state.hoa_id = str(row["id"])
        request.state.hoa = dict(row)
        request.state.hoa["id"] = str(row["id"])

        return await call_next(request)

    @staticmethod
    def _extract_slug(host: str) -> str | None:
        """Extract subdomain slug from host header.

        Examples:
            twinpeaks.housekeep.click → twinpeaks
            housekeep.click → None
            localhost:8000 → None
            twinpeaks.localhost:8000 → twinpeaks
        """
        # Remove port
        hostname = host.split(":")[0]

        parts = hostname.split(".")

        # localhost or IP
        if len(parts) <= 1:
            return None

        # housekeep.click (2 parts) → no subdomain
        # twinpeaks.housekeep.click (3 parts) → slug is first part
        if len(parts) >= 3:
            return parts[0]

        # For local dev: twinpeaks.localhost
        if parts[-1] == "localhost" and len(parts) == 2:
            return parts[0]

        return None


def get_hoa_id(request: Request) -> str:
    """Get the current HOA ID from request state. Raises 400 if not set."""
    hoa_id = getattr(request.state, "hoa_id", None)
    if not hoa_id:
        raise HTTPException(status_code=400, detail="HOA context required")
    return hoa_id
