from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db
from app.config import get_settings
from app.routers import venues, events, ticket_tiers, event_goers, tickets, payments, notifications

# Initialize FastAPI app
app = FastAPI(
    title="Event Ticket System",
    description="REST API for managing venues, events, ticket tiers, and sales with Stripe payment processing",
    version="1.0.0",
)

# Include routers
app.include_router(venues.router)
app.include_router(events.router)
app.include_router(ticket_tiers.router)
app.include_router(event_goers.router)
app.include_router(tickets.router)
app.include_router(payments.router)
app.include_router(notifications.router)

# Mount static files for uploads
settings = get_settings()
uploads_dir = Path(settings.uploads_dir)
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.on_event("startup")
def on_startup():
    """Initialize database on startup."""
    init_db()


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Event Ticket System API",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Simple success/cancel pages for Stripe redirect
@app.get("/purchase-success")
def purchase_success(session_id: str = None):
    """Purchase success page."""
    return {
        "message": "Purchase successful! Check your email for the ticket.",
        "session_id": session_id,
    }


@app.get("/purchase-cancelled")
def purchase_cancelled():
    """Purchase cancelled page."""
    return {
        "message": "Purchase was cancelled. No charges were made.",
    }


@app.get("/unsubscribe")
def unsubscribe_redirect(email: str):
    """Redirect unsubscribe to notifications endpoint."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/notifications/unsubscribe?email={email}")
