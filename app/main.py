from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import get_pool, close_pool
from app.tenant import TenantMiddleware
from app.web.routes import router as web_router
from app.web.api import router as api_router
from app.email_agent.webhook import router as webhook_router
from app.email.webhook import router as resend_webhook_router
from app.web.contractor_api import router as contractor_router
from app.web.auth import router as auth_router
from app.web.signup import router as signup_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database pool
    await get_pool()
    yield
    # Shutdown: close database pool
    await close_pool()


app = FastAPI(
    title="HouseKeep AI",
    description="Email-first AI agent for HOA management",
    version="0.2.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(TenantMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Routes
app.include_router(web_router)
app.include_router(api_router, prefix="/api")
app.include_router(webhook_router, prefix="/webhooks")
app.include_router(resend_webhook_router, prefix="/webhooks")
app.include_router(contractor_router, prefix="/api/marketplace")
app.include_router(auth_router)
app.include_router(signup_router)
