from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.database import init_db
from app.config import get_settings
from app.routers import venues, events, ticket_tiers, event_goers, tickets, payments, notifications, mcp, categories, promo_codes, public, analytics

# Initialize FastAPI app
app = FastAPI(
    title="Event Ticket System",
    description="REST API for managing venues, events, ticket tiers, and sales with Stripe payment processing",
    version="1.0.0",
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
    """Health check endpoint."""
    return {"status": "healthy"}


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
