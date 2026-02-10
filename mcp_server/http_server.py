"""
HTTP/SSE Transport for MCP Server

Exposes MCP tools via HTTP endpoints with SSE support for streaming.
Compatible with voice agents, LLM function calling, and other HTTP clients.

Usage:
    python -m mcp_server.http_server --port 3001

Endpoints:
    GET  /                  - Server info
    GET  /tools             - List available tools
    POST /tools/{name}      - Call a tool
    GET  /sse               - SSE stream for real-time updates
    POST /chat              - Chat endpoint with function calling format
"""

import json
import asyncio
import argparse
import os
from datetime import datetime
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, init_db
from mcp_server.server import list_tools, _execute_tool


# ============== Voice Command Keyword Map (Fallback) ==============
# Used when LLM routing is unavailable or fails

ACTION_MAP = {
    "list events": "list_events",
    "list_events": "list_events",
    "show events": "list_events",
    "get events": "list_events",
    "list venues": "list_venues",
    "list_venues": "list_venues",
    "show venues": "list_venues",
    "check in": "check_in_ticket",
    "check_in": "check_in_ticket",
    "checkin": "check_in_ticket",
    "check in by name": "check_in_by_name",
    "check in guest": "check_in_by_name",
    "check out": "check_out_by_name",
    "check_out": "check_out_by_name",
    "checkout": "check_out_by_name",
    "undo check in": "check_out_by_name",
    "undo checkin": "check_out_by_name",
    "send reminder": "send_event_reminders",
    "send_reminder": "send_event_reminders",
    "ticket status": "get_ticket_status",
    "ticket_status": "get_ticket_status",
    "event sales": "get_event_sales",
    "event_sales": "get_event_sales",
    "sales": "get_event_sales",
    "revenue report": "get_revenue_report",
    "revenue breakdown": "get_revenue_report",
    "sales report": "get_revenue_report",
    "how much revenue": "get_revenue_report",
    "how much money": "get_revenue_report",
    "revenue": "get_revenue_report",
    "total revenue": "get_all_sales",
    "all sales": "get_all_sales",
    "all event sales": "get_all_sales",
    "refund": "refund_ticket",
    "refund ticket": "refund_ticket",
    "issue refund": "refund_ticket",
    "cancel ticket": "refund_ticket",
    "give refund": "refund_ticket",
    "process refund": "refund_ticket",
    "download pdf": "download_ticket_pdf",
    "ticket pdf": "download_ticket_pdf",
    "pdf ticket": "download_ticket_pdf",
    "send pdf": "send_ticket_pdf",
    "email pdf": "send_ticket_pdf",
    "wallet pass": "download_wallet_pass",
    "apple wallet": "download_wallet_pass",
    "add to wallet": "download_wallet_pass",
    "send wallet pass": "send_wallet_pass",
    "send apple wallet": "send_wallet_pass",
    "email wallet": "send_wallet_pass",
    "set reminder": "configure_auto_reminder",
    "set auto reminder": "configure_auto_reminder",
    "configure reminder": "configure_auto_reminder",
    "auto reminder": "configure_auto_reminder",
    "enable reminders": "configure_auto_reminder",
    "disable reminders": "configure_auto_reminder",
    "turn off reminders": "configure_auto_reminder",
    "turn on reminders": "configure_auto_reminder",
    "check reminders": "list_scheduled_reminders",
    "list reminders": "list_scheduled_reminders",
    "scheduled reminders": "list_scheduled_reminders",
    "find event": "search_events",
    "search events": "search_events",
    "book ticket": "search_events",
    "buy ticket": "search_events",
    "buy tickets": "search_events",
    "find customer": "search_customers",
    "search customers": "search_customers",
    "look up guest": "find_guest",
    "find guest": "find_guest",
    "guest list": "guest_list",
    "who's coming": "guest_list",
    "whos coming": "guest_list",
    "attendee list": "guest_list",
    "availability": "get_ticket_availability",
    "how many tickets": "get_ticket_availability",
    "tickets left": "get_ticket_availability",
    "customer profile": "get_customer_profile",
    "list categories": "list_categories",
    "categories": "list_categories",
    "create category": "create_category",
    "send marketing": "quick_send_campaign",
    "send blast": "quick_send_campaign",
    "marketing blast": "quick_send_campaign",
    "send campaign": "send_campaign",
    "create campaign": "create_campaign",
    "list campaigns": "list_campaigns",
    "create promo code": "create_promo_code",
    "list promo codes": "list_promo_codes",
    "validate promo code": "validate_promo_code",
    "event analytics": "get_event_analytics",
    "analytics": "get_event_analytics",
    "share event": "share_event_link",
    "send admin link": "send_admin_link",
    "hide event": "set_event_visibility",
    "publish event": "set_event_visibility",
    "toggle all tickets": "toggle_all_tickets",
    "add tickets": "add_tickets",
    "postpone event": "postpone_event",
    "conversion analytics": "get_conversion_analytics",
    "create recurring event": "create_recurring_event",
    "set recap video": "set_post_event_video",
    "send photo link": "send_photo_sharing_link",
    "get event photos": "get_event_photos",
    "text guest list": "text_guest_list",
    "text everyone": "text_guest_list",
    "check waitlist": "get_waitlist",
    "waitlist": "get_waitlist",
    "notify waitlist": "notify_waitlist",
    "preview audience": "preview_audience",
    "create list": "create_marketing_list",
    "marketing lists": "list_marketing_lists",
    "send to list": "send_to_marketing_list",
    # Predictive analytics
    "predict demand": "predict_demand",
    "demand forecast": "predict_demand",
    "will it sell out": "predict_demand",
    "sell out prediction": "predict_demand",
    "pricing suggestions": "get_pricing_suggestions",
    "dynamic pricing": "get_pricing_suggestions",
    "price recommendation": "get_pricing_suggestions",
    "suggest prices": "get_pricing_suggestions",
    "churn prediction": "predict_churn",
    "at risk customers": "predict_churn",
    "who's churning": "predict_churn",
    "predict churn": "predict_churn",
    "customer segments": "get_customer_segments",
    "segment customers": "get_customer_segments",
    "rfm analysis": "get_customer_segments",
    "recommend events": "recommend_events",
    "event recommendations": "recommend_events",
    "what should they see": "recommend_events",
    "trending events": "get_trending_events",
    "what's trending": "get_trending_events",
    "hot events": "get_trending_events",
    "trending": "get_trending_events",
    # Automation
    "abandoned carts": "get_abandoned_carts",
    "pending carts": "get_abandoned_carts",
    "stale tickets": "get_abandoned_carts",
    "cart recovery": "send_cart_recovery",
    "recover carts": "send_cart_recovery",
    "list triggers": "list_auto_triggers",
    "auto triggers": "list_auto_triggers",
    "marketing triggers": "list_auto_triggers",
    "create trigger": "create_auto_trigger",
    "add trigger": "create_auto_trigger",
    "delete trigger": "delete_auto_trigger",
    "remove trigger": "delete_auto_trigger",
    "trigger history": "get_trigger_history",
    "revenue forecast": "get_revenue_forecast",
    "forecast revenue": "get_revenue_forecast",
    "projected revenue": "get_revenue_forecast",
    "revenue projection": "get_revenue_forecast",
    "survey results": "get_survey_results",
    "nps score": "get_survey_results",
    "event feedback": "get_survey_results",
    "send survey": "send_event_survey",
    "send feedback survey": "send_event_survey",
}


# ============== Pydantic Models ==============

class ToolCallRequest(BaseModel):
    arguments: dict = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class FunctionCall(BaseModel):
    name: str
    arguments: dict


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    functions: Optional[list[dict]] = None
    function_call: Optional[str | dict] = None
    stream: bool = False


class SessionState:
    """Track session state for stateful interactions."""
    def __init__(self):
        self.context: dict = {}
        self.last_event_id: Optional[int] = None
        self.last_venue_id: Optional[int] = None
        self.last_ticket_id: Optional[int] = None
        self.created_at: datetime = datetime.utcnow()


# Session storage (in production, use Redis)
sessions: dict[str, SessionState] = {}


# ============== SSE Event Queue ==============

class SSEManager:
    """Manage SSE connections and broadcast events."""

    def __init__(self):
        self.connections: dict[str, asyncio.Queue] = {}

    async def connect(self, session_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.connections[session_id] = queue
        return queue

    def disconnect(self, session_id: str):
        if session_id in self.connections:
            del self.connections[session_id]

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast event to all connected clients."""
        message = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}
        for queue in self.connections.values():
            await queue.put(message)

    async def send_to_session(self, session_id: str, event_type: str, data: dict):
        """Send event to specific session."""
        if session_id in self.connections:
            message = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}
            await self.connections[session_id].put(message)


sse_manager = SSEManager()


# ============== WebSocket Manager ==============


class WebSocketManager:
    """Manage WebSocket connections and broadcast events to dashboard clients."""

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast event to all connected WebSocket clients."""
        message = json.dumps(
            {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()},
            default=str,
        )
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self.connections:
                self.connections.remove(ws)

    @property
    def client_count(self) -> int:
        return len(self.connections)


ws_manager = WebSocketManager()


# ============== FastAPI App ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and scheduler on startup."""
    init_db()
    try:
        from app.services.scheduler import init_scheduler, bootstrap_existing_reminders, bootstrap_automation_jobs
        init_scheduler()
        bootstrap_existing_reminders()
        bootstrap_automation_jobs()
    except Exception as e:
        print(f"Scheduler init note: {e}")
    yield
    try:
        from app.services.scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="Event Tickets MCP Server (HTTP/SSE)",
    description="HTTP transport for MCP tools - compatible with voice agents and LLM function calling",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for voice agents
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Endpoints ==============

@app.get("/")
async def root():
    """Server info and available endpoints."""
    return {
        "name": "event-tickets-mcp",
        "version": "1.0.0",
        "transport": "http/sse",
        "endpoints": {
            "dashboard": "/dashboard",
            "websocket": "/ws",
            "dashboard_stats": "/api/dashboard/stats",
            "tools": "/tools",
            "call_tool": "/tools/{tool_name}",
            "sse_stream": "/sse",
            "mcp_sse": "/mcp/sse",
            "mcp_message": "/mcp/message",
            "chat": "/chat",
            "openai_functions": "/v1/chat/completions",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/admin/migrate")
async def run_migrations():
    """Run database migrations to add new columns."""
    try:
        from app.migrations.add_stripe_columns import run_migration
        results = run_migration()
        return {"success": True, "message": "Migrations completed", "details": results}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the real-time TV-style operations dashboard."""
    dashboard_path = Path(__file__).parent.parent / "app" / "static" / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(), status_code=200)
    else:
        return HTMLResponse(
            content="<h1>Dashboard not found</h1><p>Looking for: " + str(dashboard_path) + "</p>",
            status_code=404
        )


# ============== WebSocket Endpoint ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await ws_manager.connect(websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {"clients": ws_manager.client_count},
            "timestamp": datetime.utcnow().isoformat(),
        }))
        while True:
            # Keep connection alive; ignore any client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/internal/broadcast")
async def internal_broadcast(request: Request):
    """Internal endpoint for cross-process event broadcasting (e.g. Stripe webhooks)."""
    body = await request.json()
    event_type = body.get("event_type", "update")
    data = body.get("data", {})
    await ws_manager.broadcast(event_type, data)
    await sse_manager.broadcast(event_type, data)
    return {"ok": True}


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Single endpoint returning all dashboard data. Avoids MCP tool calls and SSE feedback loops."""
    from app.models import Event, TicketTier, Ticket, TicketStatus, EventGoer, Venue
    from sqlalchemy import func as sqlfunc
    from sqlalchemy.orm import joinedload

    db = SessionLocal()
    try:
        # Counts
        event_count = db.query(sqlfunc.count(Event.id)).scalar() or 0
        venue_count = db.query(sqlfunc.count(Venue.id)).scalar() or 0
        contact_count = db.query(sqlfunc.count(EventGoer.id)).scalar() or 0

        # Sales totals
        sales = (
            db.query(
                sqlfunc.count(Ticket.id).label("sold"),
                sqlfunc.sum(
                    TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                ).label("revenue"),
            )
            .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .first()
        )
        total_sold = sales.sold if sales and sales.sold else 0
        total_revenue = int(sales.revenue) if sales and sales.revenue else 0

        checked_in = (
            db.query(sqlfunc.count(Ticket.id))
            .filter(Ticket.status == TicketStatus.CHECKED_IN)
            .scalar() or 0
        )

        # Capacity
        capacity = (
            db.query(sqlfunc.sum(TicketTier.quantity_available).label("available"))
            .scalar() or 0
        )

        # Next upcoming event
        today = datetime.utcnow().strftime("%Y-%m-%d")
        next_event = (
            db.query(Event)
            .options(joinedload(Event.venue))
            .filter(Event.event_date >= today)
            .order_by(Event.event_date.asc(), Event.event_time.asc())
            .first()
        )

        next_event_data = None
        next_event_sold = 0
        next_event_available = 0
        next_event_checked_in = 0
        next_event_revenue = 0
        if next_event:
            ne_stats = (
                db.query(
                    sqlfunc.count(Ticket.id).label("sold"),
                    sqlfunc.sum(
                        TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                    ).label("revenue"),
                )
                .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
                .filter(
                    TicketTier.event_id == next_event.id,
                    Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                )
                .first()
            )
            next_event_sold = ne_stats.sold if ne_stats and ne_stats.sold else 0
            next_event_revenue = int(ne_stats.revenue) if ne_stats and ne_stats.revenue else 0
            next_event_checked_in = (
                db.query(sqlfunc.count(Ticket.id))
                .join(TicketTier)
                .filter(
                    TicketTier.event_id == next_event.id,
                    Ticket.status == TicketStatus.CHECKED_IN,
                )
                .scalar() or 0
            )
            next_event_available = (
                db.query(sqlfunc.sum(TicketTier.quantity_available))
                .filter(TicketTier.event_id == next_event.id)
                .scalar() or 0
            )
            next_event_data = {
                "id": next_event.id,
                "name": next_event.name,
                "event_date": next_event.event_date,
                "event_time": next_event.event_time,
                "venue_name": next_event.venue.name if next_event.venue else None,
                "venue_address": next_event.venue.address if next_event.venue else None,
                "image_url": next_event.image_url,
                "promo_video_url": next_event.promo_video_url,
                "tickets_sold": next_event_sold,
                "tickets_available": next_event_available,
                "tickets_checked_in": next_event_checked_in,
                "revenue_cents": next_event_revenue,
            }

        # All events for ticker
        events_list = (
            db.query(Event)
            .options(joinedload(Event.venue))
            .filter(Event.event_date >= today)
            .order_by(Event.event_date.asc())
            .all()
        )
        events_data = [
            {
                "id": e.id,
                "name": e.name,
                "event_date": e.event_date,
                "event_time": e.event_time,
                "venue_name": e.venue.name if e.venue else None,
            }
            for e in events_list
        ]

        # Branding
        from app.config import get_settings
        settings = get_settings()

        return {
            "events": event_count,
            "venues": venue_count,
            "contacts": contact_count,
            "tickets_sold": total_sold,
            "revenue_cents": total_revenue,
            "checked_in": checked_in,
            "total_capacity": capacity,
            "next_event": next_event_data,
            "upcoming_events": events_data,
            "branding": {
                "org_name": settings.org_name,
                "org_logo_url": getattr(settings, "org_logo_url", ""),
            },
        }
    finally:
        db.close()


@app.get("/tools")
async def get_tools():
    """List all available MCP tools."""
    tools = await list_tools()
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
            for tool in tools
        ]
    }


@app.get("/tools/openai")
async def get_tools_openai_format():
    """List tools in OpenAI function calling format."""
    tools = await list_tools()
    return {
        "functions": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
            for tool in tools
        ]
    }


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: ToolCallRequest, session_id: Optional[str] = None):
    """
    Call a specific MCP tool.

    Supports session context for stateful interactions.
    """
    db = SessionLocal()
    try:
        # Get or create session
        if session_id and session_id in sessions:
            session = sessions[session_id]
        else:
            session = None

        # Execute tool
        result = await _execute_tool(tool_name, request.arguments, db)

        # Update session context
        if session:
            if "event_id" in request.arguments:
                session.last_event_id = request.arguments["event_id"]
            if "venue_id" in request.arguments:
                session.last_venue_id = request.arguments["venue_id"]
            if "ticket_id" in request.arguments:
                session.last_ticket_id = request.arguments["ticket_id"]

        # Broadcast event via SSE and WebSocket
        broadcast_data = {
            "tool": tool_name,
            "arguments": request.arguments,
            "success": "error" not in result,
            "result": result,
        }
        await sse_manager.broadcast("tool_called", broadcast_data)
        await ws_manager.broadcast("tool_called", broadcast_data)

        # Specific check-in/check-out broadcasts for dashboard
        if tool_name in ("check_in_ticket", "check_in_by_name") and isinstance(result, dict) and result.get("success"):
            await ws_manager.broadcast("check_in", {
                "guest_name": result.get("guest_name") or result.get("guest", {}).get("name", "Guest"),
                "tier_name": result.get("tier_name") or result.get("ticket", {}).get("tier", "General"),
                "event_name": result.get("event_name", ""),
            })
        elif tool_name == "check_out_by_name" and isinstance(result, dict) and result.get("success"):
            await ws_manager.broadcast("check_out", {
                "guest_name": result.get("guest", {}).get("name") or request.arguments.get("name", "Guest"),
            })

        # Special handling for refresh_dashboard tool
        if tool_name == "refresh_dashboard" and result.get("success"):
            refresh_data = {
                "type": result.get("type", "soft"),
                "message": result.get("message", "Dashboard refreshed"),
                "timestamp": datetime.utcnow().isoformat(),
            }
            await sse_manager.broadcast("refresh", refresh_data)
            await ws_manager.broadcast("refresh", refresh_data)

        return {
            "success": "error" not in result,
            "result": result,
            "tool": tool_name,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/tools/{tool_name}/stream")
async def call_tool_stream(tool_name: str, request: ToolCallRequest):
    """
    Call a tool with SSE streaming response.

    Useful for long-running operations like sending bulk notifications.
    """
    async def generate() -> AsyncGenerator[str, None]:
        db = SessionLocal()
        try:
            yield f"data: {json.dumps({'status': 'started', 'tool': tool_name})}\n\n"

            result = await _execute_tool(tool_name, request.arguments, db)

            yield f"data: {json.dumps({'status': 'completed', 'result': result}, default=str)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
        finally:
            db.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============== SSE Stream ==============

@app.get("/sse")
async def sse_stream(request: Request, session_id: Optional[str] = None):
    """
    Server-Sent Events stream for real-time updates.

    Events:
    - tool_called: When any tool is executed
    - ticket_purchased: When a ticket is purchased
    - check_in: When a ticket is checked in
    - notification_sent: When a notification is sent
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[dict, None]:
        queue = await sse_manager.connect(session_id)

        # Send connection confirmation
        yield {
            "event": "connected",
            "data": json.dumps({"session_id": session_id}),
        }

        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for events with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message["type"],
                        "data": json.dumps(message["data"], default=str),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {
                        "event": "keepalive",
                        "data": json.dumps({"timestamp": datetime.utcnow().isoformat()}),
                    }
        finally:
            sse_manager.disconnect(session_id)

    return EventSourceResponse(event_generator())


# ============== WebSocket for Dashboard ==============


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.

    Events pushed to clients:
    - ticket_purchased: When a ticket is purchased (from Stripe webhook)
    - ticket_refunded: When a ticket is refunded
    - check_in: When a guest checks in
    - check_out: When a guest checks out
    - tool_called: When any MCP tool is executed
    - refresh: Dashboard refresh command
    - stats_update: Periodic stats snapshot
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; ignore client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.post("/internal/broadcast")
async def internal_broadcast(request: Request):
    """
    Internal endpoint for cross-process event broadcasting.

    Called by the main app (Stripe webhooks, REST API) to push events
    to WebSocket dashboard clients on this server.
    """
    body = await request.json()
    event_type = body.get("event_type", "update")
    data = body.get("data", {})
    await ws_manager.broadcast(event_type, data)
    # Also push to SSE for any SSE clients
    await sse_manager.broadcast(event_type, data)
    return {"ok": True, "clients": ws_manager.client_count}


# ============== MCP Protocol SSE Transport ==============

# Store pending responses for MCP sessions
mcp_sessions: dict[str, asyncio.Queue] = {}


@app.get("/mcp/sse")
async def mcp_sse_stream(request: Request):
    """
    MCP Protocol SSE Transport endpoint.

    This implements the official MCP SSE transport for tools like ElevenLabs.
    Messages are sent via POST to /mcp/message with session_id.
    """
    session_id = str(uuid.uuid4())
    mcp_sessions[session_id] = asyncio.Queue()

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Send endpoint event so client knows where to POST messages
        yield {
            "event": "endpoint",
            "data": f"/mcp/message?session_id={session_id}",
        }

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    message = await asyncio.wait_for(
                        mcp_sessions[session_id].get(),
                        timeout=30.0
                    )
                    yield {
                        "event": "message",
                        "data": json.dumps(message, default=str),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield {
                        "event": "ping",
                        "data": "",
                    }
        finally:
            if session_id in mcp_sessions:
                del mcp_sessions[session_id]

    return EventSourceResponse(event_generator())


@app.post("/mcp/message")
async def mcp_message(request: Request, session_id: Optional[str] = None):
    """
    Handle MCP JSON-RPC messages.

    Supports:
    - initialize
    - tools/list
    - tools/call
    """
    # Auto-create session if needed (for clients that POST without SSE)
    if not session_id:
        session_id = str(uuid.uuid4())
    if session_id not in mcp_sessions:
        mcp_sessions[session_id] = asyncio.Queue()

    body = await request.json()
    method = body.get("method", "")
    msg_id = body.get("id")
    params = body.get("params", {})

    response = None

    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "event-tickets-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "notifications/initialized":
        # Client acknowledged initialization - no response needed
        return {"ok": True}

    elif method == "tools/list":
        tools = await list_tools()
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        db = SessionLocal()
        try:
            result = await _execute_tool(tool_name, arguments, db)

            # Broadcast to dashboard via SSE
            await sse_manager.broadcast("tool_called", {
                "tool": tool_name,
                "arguments": arguments,
                "success": "error" not in result,
                "result": result,
            })

            # Special handling for refresh_dashboard tool
            if tool_name == "refresh_dashboard" and result.get("success"):
                await sse_manager.broadcast("refresh", {
                    "type": result.get("type", "soft"),
                    "message": result.get("message", "Dashboard refreshed"),
                    "timestamp": datetime.utcnow().isoformat(),
                })

            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, default=str)
                        }
                    ]
                }
            }
        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
        finally:
            db.close()

    else:
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    # Queue response for SSE and also return directly
    if response:
        if session_id in mcp_sessions:
            await mcp_sessions[session_id].put(response)
        return response

    return {"ok": True}


# ============== Session Management ==============

@app.post("/sessions")
async def create_session():
    """Create a new session for stateful interactions."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = SessionState()
    return {
        "session_id": session_id,
        "created_at": sessions[session_id].created_at.isoformat(),
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session context."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    return {
        "session_id": session_id,
        "context": session.context,
        "last_event_id": session.last_event_id,
        "last_venue_id": session.last_venue_id,
        "last_ticket_id": session.last_ticket_id,
        "created_at": session.created_at.isoformat(),
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
    return {"deleted": True}


@app.post("/refresh")
async def refresh_dashboard(full: bool = False, message: str = None):
    """
    Send a refresh command to all connected dashboards.

    Args:
        full: If true, triggers a full page reload. Otherwise, soft refresh.
        message: Optional message to display in the activity feed.
    """
    await sse_manager.broadcast("refresh", {
        "type": "full" if full else "soft",
        "message": message or ("Full refresh triggered" if full else "Data refreshed"),
        "timestamp": datetime.utcnow().isoformat(),
    })
    return {
        "success": True,
        "type": "full" if full else "soft",
        "message": "Refresh command sent to all connected dashboards",
    }


# ============== OpenAI-Compatible Chat Endpoint ==============

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    OpenAI-compatible chat completions endpoint with function calling.

    This allows voice agents that use OpenAI's API format to work directly.
    """
    # Get available tools
    tools = await list_tools()
    tool_map = {tool.name: tool for tool in tools}

    # Check if function calling is requested
    if request.function_call:
        # Determine which function to call
        if isinstance(request.function_call, dict):
            function_name = request.function_call.get("name")
        elif request.function_call == "auto":
            # Simple heuristic: look for tool names in the last message
            last_message = request.messages[-1].content.lower() if request.messages else ""
            function_name = None
            for tool in tools:
                if tool.name.replace("_", " ") in last_message:
                    function_name = tool.name
                    break
        else:
            function_name = None

        if function_name and function_name in tool_map:
            db = SessionLocal()
            try:
                # Extract arguments from message (simplified)
                result = await _execute_tool(function_name, {}, db)

                return {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion",
                    "created": int(datetime.utcnow().timestamp()),
                    "model": "mcp-event-tickets",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "function_call": {
                                    "name": function_name,
                                    "arguments": json.dumps({}),
                                },
                            },
                            "finish_reason": "function_call",
                        }
                    ],
                    "function_result": result,
                }
            finally:
                db.close()

    # Return available functions if no specific call
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(datetime.utcnow().timestamp()),
        "model": "mcp-event-tickets",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "I have access to event ticket management tools. What would you like to do?",
                },
                "finish_reason": "stop",
            }
        ],
        "available_functions": [tool.name for tool in tools],
    }


# ============== Voice Agent Specific Endpoints ==============

@app.post("/voice/action")
async def voice_action(request: Request, use_llm: bool = True):
    """
    Simplified endpoint for voice agents.

    Accepts natural language commands and uses LLM to route to the appropriate tool.

    Args:
        use_llm: If True (default), use LLM-based routing. If False, use keyword matching.

    Example requests:
    {"action": "list_events"}
    {"action": "check in John Smith for tonight's event"}
    {"action": "how much revenue did we make last week?"}
    {"action": "send a reminder to everyone coming to the Raptors game"}
    """
    body = await request.json()
    action = body.get("action", "")

    # Try LLM-based routing first (if enabled and configured)
    if use_llm and action:
        try:
            from app.services.llm_router import route_with_fallback
            tools = await list_tools()

            # Build context from session or body
            context = {
                "last_event_id": body.get("event_id") or body.get("last_event_id"),
                "last_customer_id": body.get("customer_id") or body.get("last_customer_id"),
            }

            # Route using LLM
            route_result = await route_with_fallback(
                user_input=action,
                tools=tools,
                keyword_map=ACTION_MAP,  # Fallback to keyword matching
                context=context,
                org_name=os.getenv("ORG_NAME", "Event Tickets"),
            )

            if route_result.get("tool"):
                tool_name = route_result["tool"]
                # Merge LLM-extracted arguments with any explicit arguments from body
                arguments = {k: v for k, v in body.items() if k != "action"}
                arguments.update(route_result.get("arguments", {}))

                db = SessionLocal()
                try:
                    result = await _execute_tool(tool_name, arguments, db)

                    # Broadcast to dashboard via WebSocket
                    await ws_manager.broadcast("tool_called", {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": "error" not in result,
                        "result": result,
                    })

                    # Generate speech response
                    if "error" in result:
                        speech = f"Sorry, there was an error: {result['error']}"
                        success = False
                    else:
                        speech = _generate_speech_response(tool_name, result)
                        success = True

                    # Prepend any pending announcements
                    from app.routers.announcement_queue import (
                        get_pending_announcements, format_announcement_speech, clear_announcements,
                    )
                    pending = get_pending_announcements()
                    announcement = format_announcement_speech(pending)
                    if announcement:
                        speech = f"{announcement} {speech}"
                        clear_announcements()

                    return {
                        "success": success,
                        "speech": speech,
                        "data": result,
                        "routing": {
                            "method": route_result.get("routed_by", "llm"),
                            "tool": tool_name,
                            "extracted_args": route_result.get("arguments", {}),
                        }
                    }
                finally:
                    db.close()

            # LLM chose not to call a tool - return its message
            elif route_result.get("message"):
                return {
                    "success": True,
                    "speech": route_result["message"],
                    "data": {},
                    "routing": {"method": "llm", "tool": None}
                }

        except ImportError:
            # LLM router not available, fall through to keyword matching
            pass
        except Exception as e:
            # Log error but fall through to keyword matching
            print(f"LLM routing error: {e}")

    # Fall back to keyword matching
    tool_name = ACTION_MAP.get(action.lower(), action)

    # Extract arguments
    arguments = {k: v for k, v in body.items() if k != "action"}

    db = SessionLocal()
    try:
        result = await _execute_tool(tool_name, arguments, db)

        # Broadcast to dashboard via WebSocket
        await ws_manager.broadcast("tool_called", {
            "tool": tool_name,
            "arguments": arguments,
            "success": "error" not in result,
            "result": result,
        })

        # Format response for voice
        if "error" in result:
            return {
                "success": False,
                "speech": f"Sorry, there was an error: {result['error']}",
                "data": result,
                "routing": {"method": "keyword", "tool": tool_name}
            }

        # Generate speech-friendly response
        speech = _generate_speech_response(tool_name, result)

        # Prepend any pending announcements from admin page changes
        from app.routers.announcement_queue import (
            get_pending_announcements, format_announcement_speech, clear_announcements,
        )
        pending = get_pending_announcements()
        announcement = format_announcement_speech(pending)
        if announcement:
            speech = f"{announcement} {speech}"
            clear_announcements()

        return {
            "success": True,
            "speech": speech,
            "data": result,
            "routing": {"method": "keyword", "tool": tool_name}
        }
    except Exception as e:
        return {
            "success": False,
            "speech": f"Sorry, I encountered an error: {str(e)}",
            "error": str(e),
        }
    finally:
        db.close()


def _format_time(t: str) -> str:
    """Convert HH:MM (24h) to 12-hour format like '7 PM' or '10:30 AM'."""
    try:
        h, m = int(t.split(":")[0]), int(t.split(":")[1])
        suffix = "AM" if h < 12 else "PM"
        h = h % 12 or 12
        return f"{h}:{m:02d} {suffix}" if m else f"{h} {suffix}"
    except (ValueError, IndexError):
        return t


def _generate_speech_response(tool_name: str, result: dict | list) -> str:
    """Generate a speech-friendly response for voice agents."""

    # Handle errors for any tool
    if isinstance(result, dict) and result.get("error"):
        return f"Sorry, {result['error']}"

    # ============== Event Tools ==============
    if tool_name == "list_events":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no upcoming events."
            elif len(result) == 1:
                e = result[0]
                return f"There is 1 event: {e['name']} on {e['event_date']} at {_format_time(e['event_time'])}."
            else:
                return f"There are {len(result)} events. The first one is {result[0]['name']} on {result[0]['event_date']}."

    elif tool_name == "create_event":
        if isinstance(result, dict):
            return f"Event '{result.get('name', '')}' created for {result.get('event_date', '')} at {_format_time(result.get('event_time', ''))}."

    elif tool_name == "create_recurring_event":
        if isinstance(result, dict):
            count = result.get("events_created", 0)
            name = result.get("event_name", "")
            day = result.get("day_of_week", "").capitalize()
            first = result.get("first_date", "")
            last = result.get("last_date", "")
            qty = result.get("tier_quantity", 0)
            price = result.get("tier_price_cents", 0)
            price_str = "free" if price == 0 else f"${price / 100:.2f}"
            return (
                f"Done! Created {count} '{name}' events, every {day} "
                f"from {first} to {last}. "
                f"Each event has {qty} tickets at {price_str}."
            )

    elif tool_name == "get_event":
        if isinstance(result, dict):
            tiers = result.get("ticket_tiers", [])
            tier_info = f" with {len(tiers)} ticket tiers" if tiers else ""
            return f"{result.get('name', 'Event')}, {result.get('event_date', '')} at {_format_time(result.get('event_time', ''))}{tier_info}. Status: {result.get('status', 'scheduled')}."

    elif tool_name == "update_event":
        if isinstance(result, dict):
            return f"Event '{result.get('name', '')}' has been updated."

    elif tool_name == "get_events_by_venue":
        if isinstance(result, list):
            if len(result) == 0:
                return "This venue has no events."
            elif len(result) == 1:
                return f"This venue has 1 event: {result[0]['name']} on {result[0]['event_date']}."
            return f"This venue has {len(result)} events. The first is {result[0]['name']} on {result[0]['event_date']}."

    elif tool_name == "search_events":
        if isinstance(result, dict):
            if result.get("found"):
                count = result.get("count", 0)
                events = result.get("events", [])
                if count == 1:
                    return f"Found 1 event: {events[0]['name']} on {events[0]['event_date']}."
                return f"Found {count} matching events. The first is {events[0]['name']}."
            return "No events found matching your search."

    elif tool_name == "send_event_update":
        if isinstance(result, dict):
            total = result.get("total_recipients", 0)
            return f"Event update sent to {total} attendees."

    elif tool_name == "cancel_event":
        if isinstance(result, dict):
            total = result.get("total_recipients", 0)
            return f"Event cancelled. Notifications sent to {total} ticket holders."

    elif tool_name == "postpone_event":
        if isinstance(result, dict):
            sent = result.get("notifications_sent", 0)
            new_date = result.get("new_date")
            new_time = result.get("new_time")
            name = result.get("event_name", "the event")
            if new_date and new_time:
                return f"Event postponed. {name} has been rescheduled to {new_date} at {_format_time(new_time)}. Notifications sent to {sent} ticket holders."
            elif new_date:
                return f"Event postponed. {name} has been rescheduled to {new_date}. Notifications sent to {sent} ticket holders."
            return f"Event postponed. Notifications sent to {sent} ticket holders. New date to be announced."

    # ============== Venue Tools ==============
    elif tool_name == "list_venues":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no venues registered."
            elif len(result) == 1:
                return f"There is 1 venue: {result[0]['name']}."
            else:
                return f"There are {len(result)} venues. Including {result[0]['name']} and {result[1]['name']}."

    elif tool_name == "create_venue":
        if isinstance(result, dict):
            return f"Venue '{result.get('name', '')}' created at {result.get('address', '')}."

    elif tool_name == "get_venue":
        if isinstance(result, dict):
            event_count = len(result.get("events", []))
            return f"{result.get('name', 'Venue')} at {result.get('address', '')}. {event_count} events."

    elif tool_name == "update_venue":
        if isinstance(result, dict):
            return f"Venue '{result.get('name', '')}' has been updated."

    # ============== Customer Tools ==============
    elif tool_name == "register_customer":
        if isinstance(result, dict):
            customer = result.get("customer", {})
            return f"{customer.get('name', 'Customer')} registered with email {customer.get('email', '')}."

    elif tool_name == "get_customer_profile":
        if isinstance(result, dict):
            if not result.get("found"):
                return result.get("message", "Customer not found.")
            customer = result.get("customer", {})
            stats = result.get("stats", {})
            prefs = result.get("preferences", {})
            vip_label = " VIP" if prefs.get("is_vip") else ""
            return f"{customer.get('name', 'Customer')},{vip_label}. {stats.get('total_spent', '$0')} spent across {stats.get('events_attended', 0)} events, {stats.get('total_tickets', 0)} tickets total."

    elif tool_name == "lookup_customer":
        if isinstance(result, dict):
            if not result.get("found"):
                return result.get("message", "Customer not found.")
            customer = result.get("customer", {})
            return f"Found {customer.get('name', 'customer')}. Email: {customer.get('email', 'none')}."

    elif tool_name == "update_customer":
        if isinstance(result, dict):
            return f"Customer '{result.get('name', '')}' has been updated."

    elif tool_name == "search_customers":
        if isinstance(result, dict):
            if result.get("found"):
                count = result.get("count", 0)
                customers = result.get("customers", [])
                if count == 1:
                    return f"Found {customers[0]['name']}."
                return f"Found {count} matching customers."
            return "No customers found matching your search."

    elif tool_name == "list_customers":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no registered customers."
            return f"There are {len(result)} customers."

    elif tool_name == "list_event_goers":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no attendees."
            return f"There are {len(result)} attendees."

    elif tool_name == "get_customer_tickets":
        if isinstance(result, dict):
            if not result.get("found"):
                return result.get("message", "Customer not found.")
            customer = result.get("customer", {})
            tickets = result.get("tickets", [])
            if len(tickets) == 0:
                return f"{customer.get('name', 'Customer')} has no tickets."
            return f"{customer.get('name', 'Customer')} has {len(tickets)} tickets. Most recent: {tickets[0].get('event_name', 'event')}, status {tickets[0].get('status', 'unknown')}."

    elif tool_name == "add_customer_note":
        if isinstance(result, dict):
            return f"Note saved. {result.get('note_type', 'general')} note added."

    elif tool_name == "get_customer_notes":
        if isinstance(result, dict):
            notes = result.get("notes", [])
            if len(notes) == 0:
                return f"No notes for {result.get('customer', 'this customer')}."
            return f"{result.get('customer', 'Customer')} has {len(notes)} notes. Latest: {notes[0].get('note', '')[:80]}."

    elif tool_name == "update_customer_preferences":
        if isinstance(result, dict):
            return result.get("message", "Preferences updated.")

    # ============== Check-in Tools ==============
    elif tool_name == "check_in_ticket":
        if isinstance(result, dict):
            if result.get("valid"):
                ticket = result.get("ticket", {})
                return f"Welcome! {ticket.get('attendee_name', 'Guest')} is checked in for {ticket.get('event_name', 'the event')}."
            return f"Check-in failed: {result.get('message', 'Invalid ticket')}"

    elif tool_name == "check_in_by_name":
        if isinstance(result, dict):
            if result.get("success"):
                return result.get("message", "Guest checked in successfully.")
            return result.get("message", "Check-in failed.")

    elif tool_name == "check_out_by_name":
        if isinstance(result, dict):
            if result.get("success"):
                return result.get("message", "Guest checked out successfully.")
            return result.get("message", "Check-out failed.")

    elif tool_name == "guest_list":
        if isinstance(result, dict):
            total = result.get("total_guests", 0)
            checked_in = result.get("checked_in", 0)
            event = result.get("event", "the event")
            if total == 0:
                return f"No guests on the list yet for {event}."
            not_in = total - checked_in
            parts = [f"{total} guest{'s' if total != 1 else ''} on the list for {event}."]
            if checked_in > 0:
                parts.append(f"{checked_in} checked in")
            if not_in > 0:
                parts.append(f"{not_in} not yet arrived")
            return " ".join(parts) + "."

    elif tool_name == "find_guest":
        if isinstance(result, dict):
            if not result.get("found"):
                return result.get("message", "Guest not found.")
            count = result.get("count", 0)
            guests = result.get("guests", [])
            if count == 1:
                g = guests[0]
                return f"Found {g['name']} for {g.get('event', 'event')}. Ticket status: {g.get('status', 'unknown')}."
            return f"Found {count} guests matching that name."

    elif tool_name == "assign_ticket":
        if isinstance(result, dict):
            if result.get("success"):
                count = len(result.get("tickets", []))
                return f"{count} ticket{'s' if count != 1 else ''} assigned to {result.get('customer', 'customer')} for {result.get('event', 'event')}."
            return result.get("message", "Could not assign ticket.")

    # ============== Ticket & Sales Tools ==============
    elif tool_name == "get_ticket_status":
        if isinstance(result, dict):
            if result.get("found"):
                ticket = result.get("ticket", {})
                return f"Ticket for {ticket.get('event_name', 'event')}. Status: {ticket.get('status', 'unknown')}."
            return "Ticket not found."

    elif tool_name == "get_ticket_availability":
        if isinstance(result, dict):
            remaining = result.get("total_remaining", 0)
            return f"{result.get('event_name', 'The event')} has {remaining} tickets remaining."

    elif tool_name == "get_event_sales":
        if isinstance(result, dict):
            total = result.get("total_tickets_sold", 0)
            revenue = result.get("total_revenue_cents", 0) / 100
            name = result.get("event_name", "Event")
            dr = result.get("date_range")
            if dr:
                period = f"from {dr['start_date']} to {dr['end_date']}" if dr.get("start_date") and dr.get("end_date") else f"since {dr.get('start_date', 'the start')}" if dr.get("start_date") else f"through {dr.get('end_date', 'now')}"
                return f"{name} sold {total} tickets for ${revenue:.2f} {period}."
            return f"{name} has sold {total} tickets for ${revenue:.2f} total revenue."

    elif tool_name == "get_all_sales":
        if isinstance(result, dict):
            total = result.get("total_tickets_sold", 0)
            revenue = result.get("total_revenue_dollars", 0)
            events = result.get("events_with_sales", 0)
            dr = result.get("date_range")
            if dr:
                period = f"from {dr['start_date']} to {dr['end_date']}" if dr.get("start_date") and dr.get("end_date") else f"since {dr.get('start_date', 'the start')}" if dr.get("start_date") else f"through {dr.get('end_date', 'now')}"
                return f"Across {events} events {period}: {total} tickets sold for ${revenue:.2f} revenue."
            return f"Total across {events} events: {total} tickets sold for ${revenue:.2f} revenue."

    elif tool_name == "get_revenue_report":
        if isinstance(result, dict):
            period = result.get("report_period", {})
            total = result.get("total_tickets", 0)
            revenue = result.get("total_revenue_dollars", 0)
            top = result.get("top_events", [])
            days = period.get("days", 0)
            speech = f"Revenue report for {period.get('start_date', '')} to {period.get('end_date', '')}: {total} tickets sold for ${revenue:.2f} over {days} days."
            if top:
                speech += f" Top event: {top[0]['event_name']} with ${top[0]['revenue_dollars']:.2f}."
            comparison = result.get("comparison")
            if comparison:
                change_pct = comparison.get("revenue_change_percent")
                if change_pct is not None:
                    direction = "up" if change_pct > 0 else "down"
                    speech += f" That's {direction} {abs(change_pct)}% from the previous period."
            return speech

    elif tool_name == "refund_ticket":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            count = result.get("refunded_count", 0)
            total = result.get("refund_total_dollars", 0)
            if count == 0:
                skipped = result.get("skipped", [])
                if skipped:
                    return f"No tickets refunded. {skipped[0].get('reason', 'Already processed')}."
                return "No refundable tickets found."
            names = list(set(r.get("customer_name", "") for r in result.get("refunded", [])))
            customer = names[0] if names else "the customer"
            if total > 0:
                return f"Refunded {count} ticket{'s' if count > 1 else ''} for {customer}. ${total:.2f} will be returned to their card."
            return f"Cancelled {count} ticket{'s' if count > 1 else ''} for {customer}. No payment to refund."

    elif tool_name == "download_ticket_pdf":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            return f"The PDF ticket for {result.get('customer_name', 'the customer')} is ready. They can download it from their ticket page."

    elif tool_name == "download_wallet_pass":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            return f"The Apple Wallet pass for {result.get('customer_name', 'the customer')} is ready."

    elif tool_name == "send_ticket_pdf":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            return f"Done! I sent the PDF ticket to {result.get('customer_name', 'the customer')} at {result.get('email', 'their email')}."

    elif tool_name == "send_wallet_pass":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            return f"Done! I sent the Apple Wallet pass to {result.get('customer_name', 'the customer')} at {result.get('email', 'their email')}."

    elif tool_name == "configure_auto_reminder":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            event_name = result.get("event_name", "the event")
            if result.get("auto_reminder") == "disabled":
                return f"Auto-reminders have been turned off for {event_name}."
            hours = result.get("hours_before", 24)
            sms = " and SMS" if result.get("use_sms") else ""
            if result.get("scheduled"):
                return f"Auto-reminder set for {event_name}. An email{sms} will be sent {hours} hours before the event."
            return f"Auto-reminder configured for {event_name} at {hours} hours before, but the reminder time has already passed."

    elif tool_name == "list_scheduled_reminders":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            if result.get("event_id"):
                event_name = result.get("event_name", "the event")
                if result.get("has_scheduled_job"):
                    return f"{event_name} has an auto-reminder scheduled for {result.get('scheduled_time', 'upcoming')}."
                hours = result.get("auto_reminder_hours")
                if hours:
                    return f"{event_name} has auto-reminders configured at {hours} hours before, but no job is currently scheduled."
                return f"{event_name} does not have auto-reminders enabled."
            total = result.get("total_scheduled", 0)
            if total == 0:
                return "There are no scheduled auto-reminders."
            reminders = result.get("reminders", [])
            if total == 1:
                return f"There is 1 scheduled reminder: {reminders[0].get('event_name', 'event')} at {reminders[0].get('scheduled_time', 'upcoming')}."
            return f"There are {total} scheduled reminders. The next one is for {reminders[0].get('event_name', 'event')} at {reminders[0].get('scheduled_time', 'upcoming')}."

    elif tool_name == "list_ticket_tiers":
        if isinstance(result, list):
            if len(result) == 0:
                return "No ticket tiers for this event."
            names = [f"{t['name']} at ${t.get('price_cents', 0) / 100:.2f}" for t in result[:3]]
            return f"{len(result)} tiers: {', '.join(names)}."

    elif tool_name == "create_ticket_tier":
        if isinstance(result, dict):
            price = result.get("price_cents", result.get("price", 0)) / 100
            return f"Tier '{result.get('name', '')}' created at ${price:.2f} with {result.get('quantity_available', 0)} tickets."

    elif tool_name == "sync_tiers_to_stripe":
        if isinstance(result, dict):
            return f"Stripe sync complete. {result.get('synced', 0)} tiers synced."

    # ============== Payment & Link Tools ==============
    elif tool_name == "email_payment_link":
        if isinstance(result, dict):
            if result.get("success"):
                return f"Payment link sent to {result.get('customer', 'customer')} at {result.get('email', 'their email')} for {result.get('event', 'the event')}. {result.get('total', '')}."
            return result.get("error", "Could not send payment link.")

    elif tool_name == "send_ticket_link":
        if isinstance(result, dict):
            if result.get("success"):
                customer = result.get("customer", {})
                return f"Purchase link sent to {customer.get('name', 'customer')} for {result.get('event', 'the event')}."
            return result.get("error", "Could not send ticket link.")

    elif tool_name == "send_purchase_link":
        if isinstance(result, dict):
            if result.get("success"):
                return f"Purchase link sent to {result.get('phone', 'the phone number')} for {result.get('event', 'the event')}."
            return result.get("error", "Could not send purchase link.")

    elif tool_name == "create_payment_link":
        if isinstance(result, dict):
            if result.get("success"):
                return f"Payment link created for {result.get('event', 'the event')}, {result.get('tier', 'tier')}. Total: {result.get('total_display', '')}."
            return result.get("error", "Could not create payment link.")

    elif tool_name == "send_purchase_email":
        if isinstance(result, dict):
            if result.get("success"):
                return f"Purchase email sent to {result.get('email', 'the customer')} for {result.get('event', 'the event')}."
            return result.get("error", "Could not send purchase email.")

    # ============== Notification Tools ==============
    elif tool_name == "send_event_reminders":
        if isinstance(result, dict):
            sent = result.get("email_sent", 0) + result.get("sms_sent", 0)
            return f"Sent {sent} reminders for {result.get('event_name', 'the event')}."

    elif tool_name == "send_sms_ticket":
        if isinstance(result, dict):
            if result.get("success"):
                return "Ticket sent via SMS."
            return result.get("error", "Could not send SMS ticket.")

    elif tool_name == "get_notification_history":
        if isinstance(result, list):
            if len(result) == 0:
                return "No notification history found."
            return f"Found {len(result)} notifications in history."

    elif tool_name == "get_attendee_preferences":
        if isinstance(result, dict):
            prefs = []
            if result.get("email_opt_in"):
                prefs.append("email")
            if result.get("sms_opt_in"):
                prefs.append("SMS")
            if result.get("marketing_opt_in"):
                prefs.append("marketing")
            return f"{result.get('name', 'Attendee')} is opted in to: {', '.join(prefs) if prefs else 'nothing'}."

    elif tool_name == "update_attendee_preferences":
        if isinstance(result, dict):
            return result.get("message", "Preferences updated.")

    # ============== Phone Verification ==============
    elif tool_name == "send_verification_code":
        if isinstance(result, dict):
            if result.get("success"):
                return f"Verification code sent to {result.get('phone', 'the phone number')}. {result.get('expires_in', '')}."
            return result.get("error", "Could not send verification code.")

    elif tool_name == "verify_phone_code":
        if isinstance(result, dict):
            if result.get("verified"):
                return f"Phone number {result.get('phone', '')} verified successfully."
            return result.get("message", "Verification failed.")

    # ============== Category Tools ==============
    elif tool_name == "list_categories":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no event categories yet."
            names = [c["name"] for c in result[:5]]
            if len(result) == 1:
                return f"There is 1 category: {names[0]}."
            return f"There are {len(result)} categories: {', '.join(names)}."

    elif tool_name == "create_category":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            return f"Category '{result.get('name', '')}' created."

    elif tool_name == "update_category":
        if isinstance(result, dict):
            if result.get("error"):
                return result["error"]
            return f"Category '{result.get('name', '')}' updated."

    # ============== Campaign Tools ==============
    elif tool_name == "create_campaign":
        if isinstance(result, dict):
            segment_desc = f" targeting {result['segment_description']}" if result.get("segment_description") else ""
            return f"Campaign '{result.get('name', '')}' created as a draft{segment_desc} with {result.get('potential_recipients', 0)} potential recipients. Say 'send campaign' to send it."

    elif tool_name == "update_campaign":
        if isinstance(result, dict):
            return f"Campaign '{result.get('name', '')}' updated. Say 'send campaign' when you're ready to send it."

    elif tool_name == "list_campaigns":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no marketing campaigns."
            draft_count = len([c for c in result if c.get("status") == "draft"])
            sent_count = len([c for c in result if c.get("status") == "sent"])
            return f"There are {len(result)} campaigns. {draft_count} drafts and {sent_count} sent."

    elif tool_name in ("send_campaign", "quick_send_campaign"):
        if isinstance(result, dict):
            total = result.get("total_recipients", 0)
            emails = result.get("email_sent", 0)
            sms = result.get("sms_sent", 0)
            return f"Marketing blast sent! Reached {total} recipients with {emails} emails and {sms} SMS messages."

    # ============== Promo Codes ==============
    elif tool_name == "create_promo_code":
        if isinstance(result, dict):
            if result.get("success"):
                return f"Promo code '{result.get('code', '')}' created for {result.get('discount', '')} off."
            return result.get("error", "Could not create promo code.")

    elif tool_name == "list_promo_codes":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no active promo codes."
            codes = ", ".join(f"{p['code']} ({p['discount']})" for p in result[:5])
            if len(result) > 5:
                return f"There are {len(result)} promo codes. Including {codes}, and more."
            return f"There are {len(result)} promo codes: {codes}."

    elif tool_name == "validate_promo_code":
        if isinstance(result, dict):
            return result.get("message", "Could not validate promo code.")

    elif tool_name == "deactivate_promo_code":
        if isinstance(result, dict):
            return result.get("message", result.get("error", "Could not deactivate promo code."))

    # ============== Analytics ==============
    elif tool_name == "get_event_analytics":
        if isinstance(result, dict):
            views = result.get("total_views", 0)
            unique = result.get("unique_visitors", 0)
            days = result.get("period_days", 30)
            if result.get("event_id"):
                name = result.get("event_name", "the event")
                return f"In the last {days} days, {name} had {views} page views from {unique} unique visitors."
            return f"In the last {days} days, all event pages had {views} total views from {unique} unique visitors."

    elif tool_name == "get_conversion_analytics":
        if isinstance(result, dict):
            funnel = result.get("funnel", {})
            rate = result.get("conversion_rate_percent", 0)
            days = result.get("period_days", 30)
            name = result.get("event_name", "the event")
            detail = funnel.get("detail_views", 0)
            purchases = funnel.get("purchases", 0)
            buyers = funnel.get("unique_buyers", 0)
            return (
                f"In the last {days} days, {name} had {detail} detail page views "
                f"and {purchases} ticket purchases from {buyers} unique buyers. "
                f"Conversion rate is {rate} percent."
            )

    elif tool_name == "share_event_link":
        if isinstance(result, dict):
            if result.get("error"):
                return f"Sorry, {result['error']}"
            event_name = result.get("event", "the event")
            sent_via = result.get("sent_via", [])
            if sent_via:
                channels = " and ".join(sent_via)
                return f"Done! I sent the link for {event_name} via {channels}."
            return f"Sorry, I couldn't send the link for {event_name}. Please check the email or phone number."

    # ============== Magic Link Admin ==============
    elif tool_name == "send_admin_link":
        if isinstance(result, dict):
            if result.get("error"):
                return f"Sorry, {result['error']}"
            event_name = result.get("event", "the event")
            sent_to = result.get("sent_to", "the promoter")
            if result.get("success"):
                return f"Done! I sent the admin link for {event_name} to the phone ending in {sent_to}. It expires in 1 hour."
            return f"I generated the admin link for {event_name} but couldn't send the SMS. The promoter can use this link: {result.get('admin_url', '')}"

    # ============== Event Visibility ==============
    elif tool_name == "set_event_visibility":
        if isinstance(result, dict):
            if result.get("error"):
                return f"Sorry, {result['error']}"
            event_name = result.get("event", "the event")
            action = result.get("action", "updated")
            return f"Event '{event_name}' has been {action}."

    # ============== Ticket Tier Controls ==============
    elif tool_name == "update_ticket_tier":
        if isinstance(result, dict):
            if result.get("error"):
                return f"Sorry, {result['error']}"
            tier_name = result.get("tier", {}).get("name", "the tier")
            changes = result.get("changes", [])
            change_str = ", ".join(changes[:3]) if changes else "updated"
            return f"Updated {tier_name}: {change_str}."

    elif tool_name == "toggle_all_tickets":
        if isinstance(result, dict):
            if result.get("error"):
                return f"Sorry, {result['error']}"
            count = result.get("updated_count", 0)
            status = result.get("new_status", "")
            event_name = result.get("event", "the event")
            skipped = result.get("skipped_sold_out", 0)
            msg = f"{count} ticket tier{'s' if count != 1 else ''} for {event_name} {'are' if count != 1 else 'is'} now {status}."
            if skipped:
                msg += f" {skipped} sold-out tier{'s' if skipped != 1 else ''} skipped."
            return msg

    elif tool_name == "add_tickets":
        if isinstance(result, dict):
            if result.get("error"):
                return f"Sorry, {result['error']}"
            action = result.get("action")
            tier_name = result.get("tier", {}).get("name", "")
            event_name = result.get("event", "")
            if action == "increased":
                added = result.get("added", 0)
                new_qty = result.get("new_quantity", 0)
                return f"Added {added} tickets to {tier_name} for {event_name}. New total: {new_qty}."
            else:
                qty = result.get("quantity", 0)
                price = result.get("tier", {}).get("price_cents", 0) / 100
                return f"Created new tier '{tier_name}' with {qty} tickets at ${price:.2f} for {event_name}."

    # ============== Dashboard ==============
    elif tool_name == "refresh_dashboard":
        return "Dashboard refreshed."

    # ============== Waitlist ==============
    elif tool_name == "get_waitlist":
        if isinstance(result, dict):
            waiting = result.get("waiting", 0)
            event_name = result.get("event", "the event")
            if waiting == 0:
                return f"No one is on the waitlist for {event_name}."
            elif waiting == 1:
                entry = result.get("entries", [{}])[0]
                return f"There is 1 person on the waitlist for {event_name}: {entry.get('name', 'someone')}."
            else:
                return f"There are {waiting} people on the waitlist for {event_name}."

    elif tool_name == "notify_waitlist":
        if isinstance(result, dict):
            count = result.get("notified", 0)
            event_name = result.get("event", "the event")
            if count == 0:
                return f"No one is waiting on the waitlist for {event_name}."
            else:
                return f"Notified {count} {'person' if count == 1 else 'people'} from the waitlist for {event_name}."

    elif tool_name == "remove_from_waitlist":
        if isinstance(result, dict):
            return result.get("message", "Removed from waitlist.")

    elif tool_name == "preview_audience":
        if isinstance(result, dict):
            total = result.get("total_recipients", 0)
            sms = result.get("sms_eligible", 0)
            if total == 0:
                return "No one matches that audience targeting."
            samples = result.get("sample_names", [])
            sample_text = f" Including {', '.join(samples[:3])}." if samples else ""
            return f"{total} people would receive this message. {sms} are eligible for SMS.{sample_text}"

    # ============== Marketing Lists ==============
    elif tool_name == "create_marketing_list":
        if isinstance(result, dict) and result.get("success"):
            name = result.get("name", "the list")
            count = result.get("member_count", 0)
            return f"Created list '{name}' with {count} members."
        elif isinstance(result, dict):
            return result.get("error", "Failed to create list.")

    elif tool_name == "list_marketing_lists":
        if isinstance(result, dict):
            total = result.get("total_lists", 0)
            if total == 0:
                return "You don't have any marketing lists yet."
            lists = result.get("lists", [])
            summaries = [f"{l['name']} ({l['member_count']} members)" for l in lists[:5]]
            return f"You have {total} list{'s' if total != 1 else ''}: {', '.join(summaries)}."

    elif tool_name == "get_marketing_list":
        if isinstance(result, dict) and result.get("success"):
            return result.get("message", "List retrieved.")

    elif tool_name == "delete_marketing_list":
        if isinstance(result, dict):
            return result.get("message", "List deleted.")

    elif tool_name == "send_to_marketing_list":
        if isinstance(result, dict):
            return result.get("message", "Sent to list.")

    # ============== Predictive Analytics ==============
    elif tool_name == "predict_demand":
        if isinstance(result, dict) and "error" not in result:
            prob = result.get("sellout_probability_percent", 0)
            score = result.get("demand_score", 0)
            event_name = result.get("event_name", "this event")
            pace = result.get("sellout_pace", {})
            pace_msg = ""
            if pace.get("required_per_day", 0) > 0:
                pace_msg = f" You need to sell {pace['required_per_day']} tickets per day to sell out."
                if not pace.get("on_track"):
                    pace_msg += f" Currently at {pace['current_per_day']} per day — below target."
                else:
                    pace_msg += f" Currently at {pace['current_per_day']} per day — on track."
            if prob >= 80:
                return f"{event_name} has very high demand — {prob}% chance of selling out.{pace_msg}"
            elif prob >= 50:
                return f"{event_name} is trending well with a {prob}% sell-out probability.{pace_msg}"
            else:
                return f"{event_name} has moderate demand — {prob}% sell-out chance. Demand score is {score} out of 100.{pace_msg}"
        elif isinstance(result, dict):
            return result.get("error", "Couldn't predict demand.")

    elif tool_name == "get_pricing_suggestions":
        if isinstance(result, dict) and "error" not in result:
            tiers = result.get("tiers", [])
            changes = [t for t in tiers if t.get("action") != "hold"]
            if changes:
                summaries = []
                for t in changes[:3]:
                    summaries.append(f"{t['tier_name']}: {t['action']} to ${t['suggested_price_dollars']}")
                return f"Pricing suggestions: {'; '.join(summaries)}."
            return "Current pricing looks good — no changes recommended."
        elif isinstance(result, dict):
            return result.get("error", "Couldn't generate pricing suggestions.")

    elif tool_name == "predict_churn":
        if isinstance(result, dict) and "error" not in result:
            total = result.get("total_at_risk", 0)
            high = result.get("high_risk_count", 0)
            if total == 0:
                return "No customers flagged as at risk of churning. Looking good!"
            return f"Found {total} at-risk customers, {high} are high risk. Check the dashboard for details and re-engagement suggestions."
        elif isinstance(result, dict):
            return result.get("error", "Couldn't run churn prediction.")

    elif tool_name == "get_customer_segments":
        if isinstance(result, dict) and "error" not in result:
            segments = result.get("segments", [])
            total = result.get("total_customers", 0)
            summary = ", ".join(f"{s['count']} {s['segment_name']}" for s in segments[:4])
            return f"Segmented {total} customers: {summary}."
        elif isinstance(result, dict):
            return result.get("error", "Couldn't segment customers.")

    elif tool_name == "recommend_events":
        if isinstance(result, dict) and "error" not in result:
            recs = result.get("recommendations", [])
            if not recs:
                return "No upcoming events to recommend for this customer."
            names = [r["event_name"] for r in recs[:3]]
            return f"Top recommendations: {', '.join(names)}."
        elif isinstance(result, dict):
            return result.get("error", "Couldn't generate recommendations.")

    elif tool_name == "get_trending_events":
        if isinstance(result, dict) and "error" not in result:
            events = result.get("trending", [])
            if not events:
                return "No events are trending right now."
            top = events[0]
            return f"Top trending: {top['event_name']} with a trend score of {top['trend_score']}. {len(events)} events trending total."
        elif isinstance(result, dict):
            return result.get("error", "Couldn't get trending events.")

    # ============== Automation ==============
    elif tool_name == "get_abandoned_carts":
        if isinstance(result, dict):
            count = result.get("abandoned_count", 0)
            tickets = result.get("total_tickets", 0)
            if count == 0:
                return "No abandoned carts right now. All checkouts are converting!"
            return f"Found {count} abandoned cart(s) with {tickets} pending ticket(s). Send recovery emails to remind them to complete their purchase."

    elif tool_name == "send_cart_recovery":
        if isinstance(result, dict):
            return result.get("message", "Cart recovery processed.")

    elif tool_name == "list_auto_triggers":
        if isinstance(result, dict):
            total = result.get("total", 0)
            if total == 0:
                return "No auto triggers configured yet. Create one to automate your marketing."
            active = sum(1 for t in result.get("triggers", []) if t.get("is_active"))
            return f"{total} trigger(s) configured, {active} active."

    elif tool_name == "create_auto_trigger":
        if isinstance(result, dict):
            return result.get("message", "Trigger created.")

    elif tool_name == "delete_auto_trigger":
        if isinstance(result, dict):
            return result.get("message", "Trigger deleted.")

    elif tool_name == "get_trigger_history":
        if isinstance(result, dict) and "error" not in result:
            name = result.get("name", "Trigger")
            count = result.get("fire_count", 0)
            last = result.get("last_fired_at")
            if count == 0:
                return f"{name} hasn't fired yet. It runs automatically every hour when conditions are met."
            return f"{name} has fired {count} time(s). Last fired: {last}."
        elif isinstance(result, dict):
            return result.get("error", "Couldn't get trigger history.")

    elif tool_name == "get_revenue_forecast":
        if isinstance(result, dict) and "error" not in result:
            days = result.get("time_horizon_days", 90)
            total_events = result.get("total_events", 0)
            projected = result.get("projected_revenue_dollars", {})
            current = result.get("current_revenue_dollars", 0)
            if total_events == 0:
                return result.get("message", "No upcoming events to forecast.")
            mid = projected.get("mid", 0)
            low = projected.get("low", 0)
            high = projected.get("high", 0)
            return f"Revenue forecast for the next {days} days: ${mid:,.2f} projected across {total_events} events. Range: ${low:,.2f} to ${high:,.2f}. Current revenue: ${current:,.2f}."
        elif isinstance(result, dict):
            return result.get("error", "Couldn't generate forecast.")

    elif tool_name == "get_survey_results":
        if isinstance(result, dict) and "error" not in result:
            total = result.get("total_responses", 0)
            if total == 0:
                return result.get("message", "No survey responses yet.")
            avg = result.get("avg_rating", 0)
            nps = result.get("nps_score", 0)
            rate = result.get("response_rate_percent", 0)
            return f"Survey results: {total} responses, average rating {avg}/10, NPS score {nps}. Response rate: {rate}%."

    elif tool_name == "send_event_survey":
        if isinstance(result, dict):
            return result.get("message", "Survey sent.")

    # Default response
    return "Done."


# ============== Main ==============

def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="MCP HTTP/SSE Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=3001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"""
╔════════════════════════════════════════════════════════════╗
║         Event Tickets MCP Server (HTTP/SSE)                ║
╠════════════════════════════════════════════════════════════╣
║  Endpoints:                                                ║
║    GET  /tools          - List available tools             ║
║    POST /tools/{{name}}   - Call a tool                     ║
║    GET  /sse            - SSE stream for real-time         ║
║    POST /voice/action   - Voice agent endpoint             ║
║    POST /v1/chat/completions - OpenAI compatible           ║
║                                                            ║
║  Docs: http://{args.host}:{args.port}/docs                          ║
╚════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "mcp_server.http_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
