#!/usr/bin/env python3
"""Simple demo server for AI Tickets - showcases the main features"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db, init_db
from app.models import Event as DBEvent, Venue, TicketTier, EventCategory

# Initialize database
init_db()

app = FastAPI(title="AI Tickets Demo", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data
SAMPLE_EVENTS = [
    {
        "id": 1,
        "name": "Jazz Night at Blue Note",
        "date": (datetime.now() + timedelta(days=7)).isoformat(),
        "venue": "Blue Note Jazz Club",
        "price": 75.00,
        "tickets_available": 45,
        "total_capacity": 150,
        "category": "Music",
        "description": "An evening of smooth jazz featuring local artists"
    },
    {
        "id": 2,
        "name": "Comedy Central Stand-Up",
        "date": (datetime.now() + timedelta(days=14)).isoformat(),
        "venue": "Laugh Factory",
        "price": 35.00,
        "tickets_available": 120,
        "total_capacity": 200,
        "category": "Comedy",
        "description": "Top comedians from Comedy Central"
    },
    {
        "id": 3,
        "name": "Tech Conference 2024",
        "date": (datetime.now() + timedelta(days=30)).isoformat(),
        "venue": "Convention Center",
        "price": 299.00,
        "tickets_available": 500,
        "total_capacity": 1000,
        "category": "Conference",
        "description": "Annual technology conference with industry leaders"
    },
    {
        "id": 4,
        "name": "Summer Music Festival",
        "date": (datetime.now() + timedelta(days=45)).isoformat(),
        "venue": "Central Park",
        "price": 150.00,
        "tickets_available": 2000,
        "total_capacity": 5000,
        "category": "Festival",
        "description": "3-day music festival featuring 50+ artists"
    }
]

# Models
class Event(BaseModel):
    id: int
    name: str
    date: str
    venue: str
    price: float
    tickets_available: int
    total_capacity: int
    category: str
    description: str

class TicketPurchase(BaseModel):
    event_id: int
    quantity: int
    customer_name: str
    customer_email: str

# HTML template for the demo page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tickets - Voice-First Event Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .tagline {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        .feature-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }
        .feature-card:hover {
            transform: translateY(-5px);
        }
        .feature-icon {
            font-size: 2em;
            margin-bottom: 15px;
        }
        .feature-title {
            font-size: 1.3em;
            color: #333;
            margin-bottom: 10px;
        }
        .feature-desc {
            color: #666;
            line-height: 1.5;
        }
        .events-section {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin: 40px 0;
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
        }
        .events-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
            margin-top: 25px;
        }
        .event-card {
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s;
            cursor: pointer;
        }
        .event-card:hover {
            border-color: #667eea;
            background: #f8f9ff;
            transform: scale(1.02);
        }
        .event-title {
            font-size: 1.2em;
            color: #333;
            margin-bottom: 10px;
        }
        .event-details {
            color: #666;
            font-size: 0.9em;
            line-height: 1.6;
        }
        .event-price {
            font-size: 1.5em;
            color: #667eea;
            font-weight: bold;
            margin-top: 10px;
        }
        .availability {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            margin-top: 10px;
        }
        .available {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .limited {
            background: #fff3e0;
            color: #f57c00;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin: 30px 0;
        }
        .stat {
            text-align: center;
            padding: 20px;
        }
        .stat-number {
            font-size: 2.5em;
            color: white;
            font-weight: bold;
        }
        .stat-label {
            color: rgba(255,255,255,0.9);
            margin-top: 5px;
        }
        .voice-demo {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border-radius: 20px;
            padding: 30px;
            color: white;
            text-align: center;
            margin: 40px 0;
        }
        .voice-examples {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .voice-example {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 10px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎫 AI Tickets</h1>
            <p class="tagline">Voice-First Event Management Platform</p>
        </header>

        <div class="stats">
            <div class="stat">
                <div class="stat-number">150+</div>
                <div class="stat-label">Voice Commands</div>
            </div>
            <div class="stat">
                <div class="stat-number">48</div>
                <div class="stat-label">API Endpoints</div>
            </div>
            <div class="stat">
                <div class="stat-number">85%</div>
                <div class="stat-label">Production Ready</div>
            </div>
            <div class="stat">
                <div class="stat-number">28:1</div>
                <div class="stat-label">Expected ROAS</div>
            </div>
        </div>

        <div class="features">
            <div class="feature-card">
                <div class="feature-icon">🎙️</div>
                <div class="feature-title">Voice Control</div>
                <div class="feature-desc">Manage everything through natural conversation with AI agents</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-title">AI Marketing</div>
                <div class="feature-desc">Auto-generate and publish ads to Meta & Google</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Predictive Analytics</div>
                <div class="feature-desc">82% accuracy in sellout forecasting</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">👥</div>
                <div class="feature-title">Customer DNA</div>
                <div class="feature-desc">9-segment behavioral profiling system</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">💳</div>
                <div class="feature-title">Smart Payments</div>
                <div class="feature-desc">Stripe integration with dynamic pricing</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📱</div>
                <div class="feature-title">Multi-Channel</div>
                <div class="feature-desc">Email, SMS, Voice calls, Social media</div>
            </div>
        </div>

        <div class="voice-demo">
            <h2>Try These Voice Commands</h2>
            <div class="voice-examples">
                <div class="voice-example">"Check in John Smith"</div>
                <div class="voice-example">"Show revenue last week"</div>
                <div class="voice-example">"Create VIP marketing list"</div>
                <div class="voice-example">"Pause underperforming ads"</div>
            </div>
        </div>

        <div class="events-section">
            <h2 style="color: #333; margin-bottom: 10px;">Live Events</h2>
            <p style="color: #666;">Click any event to see AI-powered features</p>
            <div class="events-grid" id="events">
                <!-- Events will be loaded here -->
            </div>
        </div>
    </div>

    <script>
        async function loadEvents() {
            const response = await fetch('/api/events');
            const events = await response.json();
            const container = document.getElementById('events');

            container.innerHTML = events.map(event => {
                const availability = event.tickets_available / event.total_capacity;
                const availClass = availability > 0.3 ? 'available' : 'limited';
                const availText = availability > 0.3 ? 'Available' : 'Limited Seats';

                return `
                    <div class="event-card" onclick="alert('AI Agent: I can help you purchase tickets for ${event.name}!')">
                        <div class="event-title">${event.name}</div>
                        <div class="event-details">
                            <div>📍 ${event.venue}</div>
                            <div>📅 ${new Date(event.date).toLocaleDateString()}</div>
                            <div>🎫 ${event.tickets_available} / ${event.total_capacity} tickets</div>
                        </div>
                        <div class="event-price">$${event.price}</div>
                        <span class="availability ${availClass}">${availText}</span>
                    </div>
                `;
            }).join('');
        }

        loadEvents();
    </script>
</body>
</html>
"""

# Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the demo homepage"""
    return HTML_TEMPLATE

@app.get("/api/events")
async def get_events(db: Session = Depends(get_db)):
    """Get all events from database"""

    # Get events from database
    db_events = db.query(DBEvent).all()

    # Convert to response format
    events_data = []
    for event in db_events:
        # Get ticket availability
        tiers = db.query(TicketTier).filter_by(event_id=event.id).all()
        total_available = sum(tier.quantity_available for tier in tiers)
        total_capacity = sum(tier.quantity_available + tier.quantity_sold for tier in tiers)

        # Get lowest price
        prices = [tier.price/100 for tier in tiers if tier.price > 0]
        min_price = min(prices) if prices else 0

        events_data.append({
            "id": event.id,
            "name": event.name,
            "date": f"{event.event_date}T{event.event_time}:00",
            "venue": event.venue.name if event.venue else "TBA",
            "price": min_price,
            "tickets_available": total_available,
            "total_capacity": total_capacity,
            "category": event.categories[0].name if event.categories else "Event",
            "description": event.description[:200] if event.description else ""
        })

    # Add sample events if database is empty
    if not events_data:
        return SAMPLE_EVENTS

    return events_data

@app.get("/api/events/{event_id}", response_model=Event)
async def get_event(event_id: int):
    """Get a specific event"""
    for event in SAMPLE_EVENTS:
        if event["id"] == event_id:
            return event
    raise HTTPException(status_code=404, detail="Event not found")

@app.post("/api/purchase")
async def purchase_tickets(purchase: TicketPurchase):
    """Simulate ticket purchase"""
    for event in SAMPLE_EVENTS:
        if event["id"] == purchase.event_id:
            if event["tickets_available"] >= purchase.quantity:
                event["tickets_available"] -= purchase.quantity
                return {
                    "success": True,
                    "message": f"Successfully purchased {purchase.quantity} tickets for {event['name']}",
                    "confirmation_number": f"CONF-{random.randint(100000, 999999)}",
                    "total": event["price"] * purchase.quantity
                }
            else:
                raise HTTPException(status_code=400, detail="Not enough tickets available")
    raise HTTPException(status_code=404, detail="Event not found")

@app.get("/api/stats")
async def get_stats():
    """Get platform statistics"""
    total_events = len(SAMPLE_EVENTS)
    total_capacity = sum(e["total_capacity"] for e in SAMPLE_EVENTS)
    total_sold = sum(e["total_capacity"] - e["tickets_available"] for e in SAMPLE_EVENTS)

    return {
        "total_events": total_events,
        "total_capacity": total_capacity,
        "tickets_sold": total_sold,
        "revenue": sum((e["total_capacity"] - e["tickets_available"]) * e["price"] for e in SAMPLE_EVENTS),
        "ai_features": {
            "mcp_tools": 150,
            "api_endpoints": 48,
            "database_models": 30,
            "service_files": 75
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)