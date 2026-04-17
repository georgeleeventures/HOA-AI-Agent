import json
import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer

from app.config import settings
from app.database import get_pool
from app.tenant import get_hoa_id

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
OAUTH_SCOPES = "openid email profile"

SESSION_COOKIE = "housekeep_session"


def _get_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(settings.app_secret_key)


def _cookie_secure(request: Request) -> bool:
    """Whether the session cookie should be marked Secure for this request.

    A Secure cookie is only sent back over HTTPS, so marking it Secure on
    a plain-HTTP request silently drops the session on the first navigation.
    We honor the X-Forwarded-Proto header set by our reverse proxy (Caddy).
    """
    if settings.domain == "localhost":
        return False
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    if forwarded_proto:
        return forwarded_proto == "https"
    return request.url.scheme == "https"


def get_current_user(request: Request) -> dict | None:
    """Read and verify the session cookie. Returns user dict or None."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return None
    try:
        data = _get_serializer().loads(cookie)
        return data
    except Exception:
        return None


def _get_redirect_uri(request: Request) -> str:
    scheme = "https" if settings.domain != "localhost" else "http"
    host = request.headers.get("host", settings.domain)
    return f"{scheme}://{host}/oauth/callback"


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    if user:
        return templates.TemplateResponse(
            "index.html", {"request": request, "user": user}
        )
    # Logged-out visitors see the marketing landing page
    return templates.TemplateResponse(
        "landing.html", {"request": request}
    )


@router.get("/login")
async def login(request: Request):
    redirect_uri = _get_redirect_uri(request)
    params = {
        "client_id": settings.gmail_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "access_type": "online",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse("/")

    redirect_uri = _get_redirect_uri(request)

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.error("OAuth token exchange failed: %s", token_resp.text)
        return RedirectResponse("/")

    tokens = token_resp.json()
    access_token = tokens.get("access_token")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if user_resp.status_code != 200:
        logger.error("Failed to fetch user info: %s", user_resp.text)
        return RedirectResponse("/")

    user_info = user_resp.json()
    user_email = user_info.get("email", "").lower().strip()

    # HOA is derived from the user's account (residents table), not the URL
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT r.id, r.email, r.name, r.unit, r.role, r.hoa_id,
                   h.slug AS hoa_slug, h.name AS hoa_name
            FROM residents r
            JOIN hoas h ON r.hoa_id = h.id
            WHERE r.email = $1 AND r.is_authorized = TRUE
            ORDER BY r.created_at ASC
            LIMIT 1
            """,
            user_email,
        )

    if row is None:
        return templates.TemplateResponse(
            "landing.html",
            {
                "request": request,
                "error": "Your email is not authorized. Contact your HOA administrator to be added.",
            },
        )

    # Create session with hoa_id from the resident record
    session_data = {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"] or user_info.get("name", ""),
        "unit": row["unit"],
        "role": row["role"],
        "hoa_id": str(row["hoa_id"]),
        "hoa_slug": row["hoa_slug"],
        "hoa_name": row["hoa_name"],
    }

    response = RedirectResponse("/", status_code=302)
    cookie_value = _get_serializer().dumps(session_data)
    response.set_cookie(
        SESSION_COOKIE,
        cookie_value,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )
    return response


@router.get("/demo")
async def demo_mode(request: Request):
    """Enter demo mode with a synthetic user session."""
    demo_user = {
        "id": "demo",
        "email": "demo@housekeep.click",
        "name": "Alex Rivera",
        "unit": "101",
        "role": "admin",
        "is_demo": True,
    }
    response = RedirectResponse("/", status_code=302)
    cookie_value = _get_serializer().dumps(demo_user)
    response.set_cookie(
        SESSION_COOKIE,
        cookie_value,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        max_age=3600,  # 1 hour
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "chat.html", {"request": request, "user": user}
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    category = request.query_params.get("category")
    subcategory = request.query_params.get("subcategory")
    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
            "user": user,
            "active_category": category,
            "active_subcategory": subcategory,
        },
    )


@router.get("/documents/{doc_id}", response_class=HTMLResponse)
async def document_detail(request: Request, doc_id: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    from app.documents.store import DocumentStore

    pool = await get_pool()
    store = DocumentStore(pool)
    doc = await store.get_document(doc_id)

    if not doc:
        return RedirectResponse("/documents")

    return templates.TemplateResponse(
        "document_detail.html",
        {"request": request, "user": user, "doc": doc},
    )


@router.get("/maintenance", response_class=HTMLResponse)
async def maintenance_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "maintenance.html", {"request": request, "user": user}
    )


@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "help.html", {"request": request, "user": user}
    )


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    if user.get("role") != "admin":
        return RedirectResponse("/")
    return templates.TemplateResponse(
        "admin.html", {"request": request, "user": user}
    )
