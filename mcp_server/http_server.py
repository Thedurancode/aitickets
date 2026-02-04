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
        "send reminder": "send_event_reminders",
        "send_reminder": "send_event_reminders",
        "ticket status": "get_ticket_status",
        "ticket_status": "get_ticket_status",
        "event sales": "get_event_sales",
        "event_sales": "get_event_sales",
        "sales": "get_event_sales",
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
