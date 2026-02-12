import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path

from app.database import init_db
from app.config import get_settings
from app.rate_limit import limiter
from app.routers import venues, events, ticket_tiers, event_goers, tickets, payments, notifications, mcp, categories, promo_codes, public, analytics, knowledge, webhooks, about

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Event Ticket System",
    description="REST API for managing venues, events, ticket tiers, and sales with Stripe payment processing",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============== Global Error Handlers ==============

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a consistent JSON format for validation errors."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.append(f"{field}: {err['msg']}" if field else err["msg"])
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": "; ".join(errors)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — log full traceback, return safe message."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred."},
    )

# API routers (JSON endpoints, prefixed with /api)
api_prefix = "/api"
app.include_router(venues.router, prefix=api_prefix)
app.include_router(events.router, prefix=api_prefix)
app.include_router(ticket_tiers.router, prefix=api_prefix)
app.include_router(event_goers.router, prefix=api_prefix)
app.include_router(tickets.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)
app.include_router(categories.router, prefix=api_prefix)
app.include_router(promo_codes.router, prefix=api_prefix)
app.include_router(analytics.router, prefix=api_prefix)
app.include_router(knowledge.router, prefix=api_prefix)
app.include_router(webhooks.router, prefix=api_prefix)
app.include_router(about.router, prefix=api_prefix)

# Non-API routers (keep at root)
app.include_router(payments.router)   # /webhooks/stripe
app.include_router(mcp.router)        # /mcp/*

# Public frontend (HTML pages at /events)
app.include_router(public.router)

# Mount static files for uploads
settings = get_settings()
uploads_dir = Path(settings.uploads_dir)
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


# ============== CORS Middleware ==============
_settings = get_settings()
_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()] if _settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== API Key Auth Middleware ==============
# Protects /api/* write endpoints when MCP_API_KEY is set.
# Public pages (/events, /purchase-success, etc.) remain open.

REST_PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc",
                     "/events", "/about", "/purchase-success", "/purchase-cancelled",
                     "/unsubscribe", "/webhooks/stripe"}
REST_PUBLIC_PREFIXES = ("/events/", "/uploads/", "/api/events/", "/api/page-view", "/api/about")


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        # REST API uses admin_api_key if set, otherwise falls back to mcp_api_key
        api_key = settings.admin_api_key or settings.mcp_api_key

        if not api_key:
            return await call_next(request)

        path = request.url.path

        # Allow public paths and prefixes
        if path in REST_PUBLIC_PATHS:
            return await call_next(request)
        if any(path.startswith(p) for p in REST_PUBLIC_PREFIXES):
            return await call_next(request)

        # Check for API key — accept either x-mcp-key or x-admin-key header
        provided_key = (
            request.headers.get("x-admin-key")
            or request.headers.get("x-mcp-key")
        )

        if not provided_key or provided_key != api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Invalid or missing API key."},
            )

        return await call_next(request)


app.add_middleware(ApiKeyAuthMiddleware)


@app.on_event("startup")
def on_startup():
    """Initialize database and scheduler on startup."""
    init_db()
    try:
        from app.services.scheduler import init_scheduler, bootstrap_existing_reminders
        init_scheduler()
        bootstrap_existing_reminders()
    except Exception as e:
        print(f"Scheduler init note: {e}")


@app.on_event("shutdown")
def on_shutdown():
    """Shut down scheduler gracefully."""
    try:
        from app.services.scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception:
        pass


@app.get("/")
def root():
    """Root endpoint — redirect to events page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/events")


@app.get("/health")
def health_check():
    """Health check endpoint — verifies DB connectivity."""
    from sqlalchemy import text
    from app.database import SessionLocal

    checks = {"db": "ok"}
    status = "healthy"

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        checks["db"] = str(e)
        status = "unhealthy"

    code = 200 if status == "healthy" else 503
    return JSONResponse(status_code=code, content={"status": status, "checks": checks})


@app.get("/purchase-success", response_class=HTMLResponse)
def purchase_success(session_id: str = None):
    """Purchase success page."""
    s = get_settings()
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Purchase Successful | {s.org_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex items-center justify-center">
    <div class="text-center max-w-md mx-auto px-6">
        <div class="text-6xl mb-6">🎉</div>
        <h1 class="text-3xl font-bold mb-4">You're In!</h1>
        <p class="text-gray-400 mb-8">Your tickets have been confirmed. Check your email for your ticket with QR code.</p>
        <a href="/events" class="inline-block px-6 py-3 rounded-lg font-medium text-white transition-colors" style="background-color: {s.org_color};">
            Browse More Events
        </a>
    </div>
</body>
</html>""")


@app.get("/purchase-cancelled", response_class=HTMLResponse)
def purchase_cancelled():
    """Purchase cancelled page."""
    s = get_settings()
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Purchase Cancelled | {s.org_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen flex items-center justify-center">
    <div class="text-center max-w-md mx-auto px-6">
        <h1 class="text-2xl font-bold mb-4">Purchase Cancelled</h1>
        <p class="text-gray-400 mb-8">No charges were made. You can try again anytime.</p>
        <a href="/events" class="inline-block px-6 py-3 rounded-lg font-medium text-white transition-colors" style="background-color: {s.org_color};">
            Back to Events
        </a>
    </div>
</body>
</html>""")


@app.get("/unsubscribe")
def unsubscribe_redirect(email: str):
    """Redirect unsubscribe to notifications endpoint."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/api/notifications/unsubscribe?email={email}")
