"""
MCP/SSE Router for Voice Agent Integration

Exposes MCP tools via HTTP endpoints with SSE support for real-time streaming.
Compatible with ElevenLabs, voice agents, and LLM function calling.

Endpoints:
    GET  /mcp/tools         - List available tools
    POST /mcp/tools/{name}  - Call a tool
    GET  /mcp/sse           - SSE stream for real-time updates
    POST /mcp/message       - MCP JSON-RPC messages
    POST /mcp/voice/action  - Simplified voice agent endpoint
"""

import json
import asyncio
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import SessionLocal
from mcp_server.server import list_tools, _execute_tool


router = APIRouter(prefix="/mcp", tags=["MCP"])


# ============== Pydantic Models ==============

class ToolCallRequest(BaseModel):
    arguments: dict = {}


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

# Store pending responses for MCP sessions
mcp_sessions: dict[str, asyncio.Queue] = {}


# ============== Endpoints ==============

@router.get("")
async def mcp_info():
    """MCP server info and available endpoints."""
    return {
        "name": "event-tickets-mcp",
        "version": "1.0.0",
        "transport": "http/sse",
        "endpoints": {
            "tools": "/mcp/tools",
            "call_tool": "/mcp/tools/{tool_name}",
            "sse_stream": "/mcp/sse",
            "mcp_message": "/mcp/message",
            "voice_action": "/mcp/voice/action",
            "dashboard": "/mcp/dashboard",
        },
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the real-time TV-style operations dashboard."""
    dashboard_path = Path(__file__).parent.parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(), status_code=200)
    else:
        return HTMLResponse(
            content="<h1>Dashboard not found</h1><p>Looking for: " + str(dashboard_path) + "</p>",
            status_code=404
        )


@router.get("/tools")
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


@router.get("/tools/openai")
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


@router.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: ToolCallRequest):
    """Call a specific MCP tool."""
    db = SessionLocal()
    try:
        result = await _execute_tool(tool_name, request.arguments, db)

        # Broadcast event via SSE
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


# ============== SSE Stream ==============

@router.get("/sse")
async def sse_stream(request: Request, session_id: Optional[str] = None):
    """
    Server-Sent Events stream for real-time updates.

    Events:
    - tool_called: When any tool is executed
    - ticket_purchased: When a ticket is purchased
    - check_in: When a ticket is checked in
    - refresh: Dashboard refresh command
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
                if await request.is_disconnected():
                    break

                try:
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

@router.get("/protocol/sse")
async def mcp_protocol_sse_stream(request: Request):
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
                    yield {
                        "event": "ping",
                        "data": "",
                    }
        finally:
            if session_id in mcp_sessions:
                del mcp_sessions[session_id]

    return EventSourceResponse(event_generator())


@router.post("/message")
async def mcp_message(request: Request, session_id: Optional[str] = None):
    """
    Handle MCP JSON-RPC messages.

    Supports:
    - initialize
    - tools/list
    - tools/call
    """
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

            await sse_manager.broadcast("tool_called", {
                "tool": tool_name,
                "arguments": arguments,
                "success": "error" not in result,
                "result": result,
            })

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

    if response:
        if session_id in mcp_sessions:
            await mcp_sessions[session_id].put(response)
        return response

    return {"ok": True}


# ============== Voice Agent Endpoint ==============

@router.post("/voice/action")
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
    }

    tool_name = action_map.get(action.lower(), action)
    arguments = {k: v for k, v in body.items() if k != "action"}

    db = SessionLocal()
    try:
        result = await _execute_tool(tool_name, arguments, db)

        if "error" in result:
            return {
                "success": False,
                "speech": f"Sorry, there was an error: {result['error']}",
                "data": result,
            }

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

    if tool_name == "list_events":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no upcoming events."
            elif len(result) == 1:
                e = result[0]
                return f"There is 1 event: {e['name']} on {e['event_date']} at {e['event_time']}."
            else:
                return f"There are {len(result)} events. The first one is {result[0]['name']} on {result[0]['event_date']}."

    elif tool_name == "list_venues":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no venues registered."
            elif len(result) == 1:
                return f"There is 1 venue: {result[0]['name']}."
            else:
                return f"There are {len(result)} venues. Including {result[0]['name']} and {result[1]['name'] if len(result) > 1 else ''}."

    elif tool_name == "check_in_ticket":
        if result.get("valid"):
            ticket = result.get("ticket", {})
            return f"Welcome! {ticket.get('attendee_name', 'Guest')} is checked in for {ticket.get('event_name', 'the event')}."
        else:
            return f"Check-in failed: {result.get('message', 'Invalid ticket')}"

    elif tool_name == "get_event_sales":
        total = result.get("total_tickets_sold", 0)
        revenue = result.get("total_revenue_cents", 0) / 100
        return f"Event {result.get('event_name', '')} has sold {total} tickets for ${revenue:.2f} total revenue."

    elif tool_name == "send_event_reminders":
        sent = result.get("email_sent", 0) + result.get("sms_sent", 0)
        return f"Sent {sent} reminders for {result.get('event_name', 'the event')}."

    elif tool_name == "get_ticket_status":
        if result.get("found"):
            ticket = result.get("ticket", {})
            return f"Ticket found. Status: {ticket.get('status')} for {ticket.get('event_name', 'event')}."
        else:
            return "Ticket not found."

    elif tool_name == "search_events":
        if isinstance(result, dict):
            if result.get("found"):
                count = result.get("count", 0)
                events = result.get("events", [])
                if count == 1:
                    return f"Found 1 event: {events[0]['name']} on {events[0]['event_date']}."
                return f"Found {count} matching events. The first is {events[0]['name']}."
            return "No events found matching your search."

    elif tool_name == "search_customers":
        if isinstance(result, dict):
            if result.get("found"):
                count = result.get("count", 0)
                customers = result.get("customers", [])
                if count == 1:
                    return f"Found {customers[0]['name']}."
                return f"Found {count} matching customers."
            return "No customers found matching your search."

    elif tool_name == "get_ticket_availability":
        if isinstance(result, dict) and not result.get("error"):
            remaining = result.get("total_remaining", 0)
            return f"{result.get('event_name', 'The event')} has {remaining} tickets remaining."

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

    elif tool_name == "list_categories":
        if isinstance(result, list):
            if len(result) == 0:
                return "There are no event categories yet."
            names = [c["name"] for c in result[:5]]
            if len(result) == 1:
                return f"There is 1 category: {names[0]}."
            return f"There are {len(result)} categories: {', '.join(names)}."

    return "Done."


@router.post("/refresh")
async def refresh_dashboard(full: bool = False, message: str = None):
    """
    Send a refresh command to all connected dashboards.
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


@router.post("/admin/migrate")
async def run_migrations():
    """Run database migrations to add new columns."""
    try:
        from app.migrations.add_stripe_columns import run_migration
        results = run_migration()
        return {"success": True, "message": "Migrations completed", "details": results}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
