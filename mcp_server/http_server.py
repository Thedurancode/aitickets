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
from datetime import datetime
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, HTTPException, Request
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


# ============== FastAPI App ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


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

        # Broadcast event via SSE with full result
        await sse_manager.broadcast("tool_called", {
            "tool": tool_name,
            "arguments": request.arguments,
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
async def voice_action(request: Request):
    """
    Simplified endpoint for voice agents.

    Accepts natural language or structured commands.

    Example requests:
    {"action": "list_events"}
    {"action": "check_in", "qr_token": "abc123"}
    {"action": "send_reminder", "event_id": 1}
    """
    body = await request.json()
    action = body.get("action", "")

    # Map common voice commands to tools
    action_map = {
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
        # Search
        "find event": "search_events",
        "search events": "search_events",
        "search event": "search_events",
        "book ticket": "search_events",
        "buy ticket": "search_events",
        "buy tickets": "search_events",
        "purchase ticket": "search_events",
        "get tickets": "search_events",
        "find customer": "search_customers",
        "search customer": "search_customers",
        "search customers": "search_customers",
        "look up guest": "find_guest",
        "lookup guest": "find_guest",
        "find guest": "find_guest",
        "guest list": "guest_list",
        "who's coming": "guest_list",
        "whos coming": "guest_list",
        "how many people": "guest_list",
        "attendee list": "guest_list",
        "who's on the list": "guest_list",
        # Availability
        "availability": "get_ticket_availability",
        "how many tickets": "get_ticket_availability",
        "tickets left": "get_ticket_availability",
        "tickets available": "get_ticket_availability",
        "tickets remaining": "get_ticket_availability",
        # Customer
        "customer profile": "get_customer_profile",
        "customer info": "get_customer_profile",
        "customer details": "get_customer_profile",
        # Categories
        "list categories": "list_categories",
        "show categories": "list_categories",
        "event types": "list_categories",
        "event categories": "list_categories",
        "categories": "list_categories",
        # Marketing campaigns
        "send marketing": "quick_send_campaign",
        "send blast": "quick_send_campaign",
        "marketing blast": "quick_send_campaign",
        "email blast": "quick_send_campaign",
        "sms blast": "quick_send_campaign",
        "send campaign": "send_campaign",
        "create campaign": "create_campaign",
        "new campaign": "create_campaign",
        "list campaigns": "list_campaigns",
        "show campaigns": "list_campaigns",
        "campaigns": "list_campaigns",
        "marketing campaigns": "list_campaigns",
        # Segment targeting shortcuts
        "vip blast": "quick_send_campaign",
        "blast vips": "quick_send_campaign",
        "blast high spenders": "quick_send_campaign",
        "blast repeat customers": "quick_send_campaign",
        "edit campaign": "update_campaign",
        "update campaign": "update_campaign",
        "change campaign message": "update_campaign",
        # Promo codes
        "create promo code": "create_promo_code",
        "new promo code": "create_promo_code",
        "create discount code": "create_promo_code",
        "add coupon": "create_promo_code",
        "list promo codes": "list_promo_codes",
        "show promo codes": "list_promo_codes",
        "promo codes": "list_promo_codes",
        "discount codes": "list_promo_codes",
        "validate promo code": "validate_promo_code",
        "check promo code": "validate_promo_code",
        "check coupon": "validate_promo_code",
        "deactivate promo code": "deactivate_promo_code",
        "disable promo code": "deactivate_promo_code",
        "remove promo code": "deactivate_promo_code",
        # Analytics
        "event analytics": "get_event_analytics",
        "page views": "get_event_analytics",
        "event page views": "get_event_analytics",
        "analytics": "get_event_analytics",
        "traffic": "get_event_analytics",
        "how many views": "get_event_analytics",
        # Share event link
        "share event": "share_event_link",
        "share event link": "share_event_link",
        "send event link": "share_event_link",
        "send link": "share_event_link",
        "invite to event": "share_event_link",
        "text event link": "share_event_link",
        "email event link": "share_event_link",
        # Magic link admin
        "send admin link": "send_admin_link",
        "admin link": "send_admin_link",
        "edit event link": "send_admin_link",
        "change event picture": "send_admin_link",
        "upload event image": "send_admin_link",
        "manage event link": "send_admin_link",
        "event admin link": "send_admin_link",
        # Event visibility
        "hide event": "set_event_visibility",
        "hide the event": "set_event_visibility",
        "make event live": "set_event_visibility",
        "make event visible": "set_event_visibility",
        "show event": "set_event_visibility",
        "publish event": "set_event_visibility",
        # Bulk ticket controls
        "turn off all tickets": "toggle_all_tickets",
        "disable all tickets": "toggle_all_tickets",
        "pause all tickets": "toggle_all_tickets",
        "turn on all tickets": "toggle_all_tickets",
        "enable all tickets": "toggle_all_tickets",
        "activate all tickets": "toggle_all_tickets",
        "make tickets live": "toggle_all_tickets",
        "open ticket sales": "toggle_all_tickets",
        "close ticket sales": "toggle_all_tickets",
        # Add tickets
        "add more tickets": "add_tickets",
        "add tickets": "add_tickets",
        "add another": "add_tickets",
        "increase tickets": "add_tickets",
        "increase inventory": "add_tickets",
        # Update tier
        "update ticket tier": "update_ticket_tier",
        "update tier": "update_ticket_tier",
        "change tier": "update_ticket_tier",
        "pause tier": "update_ticket_tier",
        "activate tier": "update_ticket_tier",
    }

    tool_name = action_map.get(action.lower(), action)

    # Extract arguments
    arguments = {k: v for k, v in body.items() if k != "action"}

    db = SessionLocal()
    try:
        result = await _execute_tool(tool_name, arguments, db)

        # Format response for voice
        if "error" in result:
            return {
                "success": False,
                "speech": f"Sorry, there was an error: {result['error']}",
                "data": result,
            }

        # Generate speech-friendly response
        speech = _generate_speech_response(tool_name, result)

        return {
            "success": True,
            "speech": speech,
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "speech": f"Sorry, I encountered an error: {str(e)}",
            "error": str(e),
        }
    finally:
        db.close()


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
                return f"There is 1 event: {e['name']} on {e['event_date']} at {e['event_time']}."
            else:
                return f"There are {len(result)} events. The first one is {result[0]['name']} on {result[0]['event_date']}."

    elif tool_name == "create_event":
        if isinstance(result, dict):
            return f"Event '{result.get('name', '')}' created for {result.get('event_date', '')} at {result.get('event_time', '')}."

    elif tool_name == "get_event":
        if isinstance(result, dict):
            tiers = result.get("ticket_tiers", [])
            tier_info = f" with {len(tiers)} ticket tiers" if tiers else ""
            return f"{result.get('name', 'Event')}, {result.get('event_date', '')} at {result.get('event_time', '')}{tier_info}. Status: {result.get('status', 'scheduled')}."

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
            return f"{result.get('event_name', 'Event')} has sold {total} tickets for ${revenue:.2f} total revenue."

    elif tool_name == "get_all_sales":
        if isinstance(result, dict):
            total = result.get("total_tickets_sold", 0)
            revenue = result.get("total_revenue_dollars", 0)
            events = result.get("events_with_sales", 0)
            return f"Total across {events} events: {total} tickets sold for ${revenue:.2f} revenue."

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
            return f"Category '{result.get('name', '')}' created."

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
