"""
Event Research Agent

Autonomous agent that researches event context (venue, location, date, competitors)
and generates data-driven marketing plans using web search and AI analysis.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from app.models import Event, Venue, EventCategory, TicketTier
from app.config import get_settings


def analyze_event_context(db: Session, event_id: int) -> Dict:
    """
    Analyze event context: date, location, venue, pricing, categories.

    Returns comprehensive event intelligence for marketing planning.
    """
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    venue = db.query(Venue).filter(Venue.id == event.venue_id).first()
    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    categories = event.categories if hasattr(event, 'categories') else []

    # Parse event date
    try:
        event_datetime = datetime.strptime(
            f"{event.event_date} {event.event_time}",
            "%Y-%m-%d %H:%M"
        )
        days_until = (event_datetime - datetime.now()).days

        # Determine season
        month = event_datetime.month
        if month in [12, 1, 2]:
            season = "winter"
        elif month in [3, 4, 5]:
            season = "spring"
        elif month in [6, 7, 8]:
            season = "summer"
        else:
            season = "fall"

        # Day of week
        day_of_week = event_datetime.strftime("%A")
        is_weekend = day_of_week in ["Friday", "Saturday", "Sunday"]

    except:
        event_datetime = None
        days_until = None
        season = "unknown"
        day_of_week = "unknown"
        is_weekend = False

    # Pricing analysis
    price_range = {
        "min": min([t.price for t in tiers]) if tiers else 0,
        "max": max([t.price for t in tiers]) if tiers else 0,
        "avg": sum([t.price for t in tiers]) / len(tiers) if tiers else 0,
    }

    # Inventory analysis
    total_capacity = sum([t.quantity_available for t in tiers])
    total_sold = sum([t.quantity_sold for t in tiers])
    sell_through = (total_sold / total_capacity * 100) if total_capacity > 0 else 0

    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "description": event.description,
            "date": event.event_date,
            "time": event.event_time,
            "doors_open": event.doors_open_time,
            "days_until_event": days_until,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "season": season,
        },
        "venue": {
            "name": venue.name if venue else "Unknown",
            "address": venue.address if venue else "Unknown",
            "phone": venue.phone if venue else None,
        },
        "categories": [
            {"id": c.id, "name": c.name, "color": c.color}
            for c in categories
        ],
        "pricing": {
            "min_cents": price_range["min"],
            "max_cents": price_range["max"],
            "avg_cents": int(price_range["avg"]),
            "min_usd": f"${price_range['min']/100:.2f}",
            "max_usd": f"${price_range['max']/100:.2f}",
            "avg_usd": f"${price_range['avg']/100:.2f}",
        },
        "inventory": {
            "total_capacity": total_capacity,
            "sold": total_sold,
            "available": total_capacity - total_sold,
            "sell_through_percent": round(sell_through, 1),
        },
        "tiers": [
            {
                "name": t.name,
                "price_cents": t.price,
                "quantity": t.quantity_available,
                "sold": t.quantity_sold,
            }
            for t in tiers
        ],
    }


def research_venue_area(venue_address: str) -> Dict:
    """
    Research the area around a venue using geocoding and local insights.

    In production, this would use:
    - Google Places API for nearby venues/competitors
    - Census data for demographics
    - Weather API for event date forecast
    """
    # Parse city and state from address
    parts = venue_address.split(",")
    city = parts[-2].strip() if len(parts) >= 2 else "Unknown"
    state = parts[-1].strip() if len(parts) >= 1 else "Unknown"

    # Mock demographic data (replace with real API calls)
    return {
        "location": {
            "city": city,
            "state": state,
            "full_address": venue_address,
        },
        "demographics": {
            "population": "Estimated from census data",
            "median_age": "Research via census API",
            "median_income": "Research via census API",
        },
        "nearby_venues": [
            "Research via Google Places API",
            "Find competing venues within 5 miles",
        ],
        "local_events": [
            "Research via Eventbrite/Ticketmaster APIs",
            "Identify competing events on same date",
        ],
        "weather_forecast": "Use OpenWeather API for event date",
    }


def generate_marketing_plan(
    event_context: Dict,
    area_research: Dict,
) -> Dict:
    """
    Generate AI-powered marketing plan based on event research.

    Uses OpenRouter LLM to analyze context and create recommendations.
    """
    settings = get_settings()

    # Build research prompt
    prompt = f"""You are an expert event marketing strategist. Analyze this event and create a comprehensive marketing plan.

EVENT DETAILS:
- Name: {event_context['event']['name']}
- Description: {event_context['event']['description']}
- Date: {event_context['event']['date']} ({event_context['event']['day_of_week']})
- Time: {event_context['event']['time']}
- Days Until Event: {event_context['event']['days_until_event']}
- Season: {event_context['event']['season']}
- Weekend Event: {event_context['event']['is_weekend']}

VENUE:
- Name: {event_context['venue']['name']}
- Location: {event_context['venue']['address']}
- City: {area_research['location']['city']}, {area_research['location']['state']}

PRICING:
- Range: {event_context['pricing']['min_usd']} - {event_context['pricing']['max_usd']}
- Average: {event_context['pricing']['avg_usd']}

INVENTORY:
- Total Capacity: {event_context['inventory']['total_capacity']}
- Current Sell-Through: {event_context['inventory']['sell_through_percent']}%
- Available: {event_context['inventory']['available']}

CATEGORIES: {', '.join([c['name'] for c in event_context['categories']])}

Create a detailed marketing plan with:
1. **Target Audience** - Who should we market to? (age, interests, psychographics)
2. **Key Messaging** - What story should we tell? (value props, emotional hooks)
3. **Channel Strategy** - Where should we advertise? (social, email, SMS, Meta ads)
4. **Timing Strategy** - When to launch campaigns? (based on days until event)
5. **Budget Allocation** - How to split marketing spend across channels?
6. **Urgency Tactics** - How to create FOMO? (countdown, limited tickets, early bird)
7. **Content Ideas** - Specific post/ad copy examples
8. **Success Metrics** - What KPIs to track?

Format as JSON with these exact keys: target_audience, key_messaging, channel_strategy, timing_strategy, budget_allocation, urgency_tactics, content_ideas, success_metrics"""

    # Call OpenRouter LLM
    try:
        import requests

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert event marketing strategist. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if response.status_code == 200:
            ai_response = response.json()
            marketing_plan_text = ai_response["choices"][0]["message"]["content"]

            try:
                marketing_plan = json.loads(marketing_plan_text)
            except:
                marketing_plan = {"raw_response": marketing_plan_text}
        else:
            marketing_plan = {
                "error": f"OpenRouter API error: {response.status_code}",
                "fallback": "Generate manual plan based on templates"
            }

    except Exception as e:
        marketing_plan = {
            "error": f"Failed to generate AI plan: {str(e)}",
            "fallback": _generate_template_plan(event_context)
        }

    return marketing_plan


def _generate_template_plan(event_context: Dict) -> Dict:
    """Fallback template-based marketing plan if AI fails."""
    days_until = event_context['event']['days_until_event'] or 30
    is_weekend = event_context['event']['is_weekend']
    sell_through = event_context['inventory']['sell_through_percent']

    # Determine urgency level
    if days_until <= 7:
        urgency = "HIGH"
    elif days_until <= 14:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"

    return {
        "target_audience": {
            "primary": "Local residents aged 25-45 interested in live events",
            "secondary": "Event enthusiasts within 50 mile radius",
        },
        "key_messaging": {
            "headline": f"Don't Miss {event_context['event']['name']}!",
            "subheadline": f"{event_context['event']['day_of_week']}, {event_context['event']['date']}",
            "urgency_message": f"Only {event_context['inventory']['available']} tickets left!" if sell_through > 50 else "Limited tickets available",
        },
        "channel_strategy": {
            "meta_ads": {"priority": "HIGH", "budget_percent": 40},
            "email": {"priority": "MEDIUM", "budget_percent": 20},
            "sms": {"priority": "MEDIUM" if urgency == "HIGH" else "LOW", "budget_percent": 15},
            "organic_social": {"priority": "HIGH", "budget_percent": 0},
        },
        "timing_strategy": {
            "launch_date": f"{days_until - 14} days before event" if days_until > 14 else "ASAP",
            "intensity_ramp": "Increase ad spend 50% in final 7 days" if urgency != "HIGH" else "Maximum intensity now",
        },
        "urgency_tactics": [
            "Countdown timer in emails/ads",
            f"Early bird pricing (if {'available' if sell_through < 30 else 'not available'})",
            "Limited quantity messaging",
            "Social proof (X tickets sold already)",
        ],
        "success_metrics": {
            "ticket_sales_target": event_context['inventory']['total_capacity'],
            "email_open_rate_target": "25%+",
            "ad_ctr_target": "2%+",
            "cost_per_ticket": f"<${event_context['pricing']['avg_cents'] * 0.2 / 100:.2f}",
        },
    }


async def run_event_research_agent(
    db: Session,
    event_id: int,
    include_ai_plan: bool = True,
) -> Dict:
    """
    Run complete research agent for an event.

    Steps:
    1. Analyze event context (date, venue, pricing, inventory)
    2. Research venue area (demographics, competitors, weather)
    3. Generate AI marketing plan
    4. Return comprehensive research report
    """
    # Step 1: Analyze event
    event_context = analyze_event_context(db, event_id)

    if "error" in event_context:
        return event_context

    # Step 2: Research area
    area_research = research_venue_area(event_context['venue']['address'])

    # Step 3: Generate marketing plan
    if include_ai_plan:
        marketing_plan = generate_marketing_plan(event_context, area_research)
    else:
        marketing_plan = {"message": "AI plan generation skipped"}

    # Step 4: Compile research report
    return {
        "event_id": event_id,
        "event_name": event_context['event']['name'],
        "research_completed_at": datetime.utcnow().isoformat(),
        "event_context": event_context,
        "area_research": area_research,
        "marketing_plan": marketing_plan,
        "next_steps": [
            "Review marketing plan recommendations",
            "Adjust budget allocations based on sell-through rate",
            "Create Meta ad campaigns using recommended messaging",
            "Schedule email/SMS campaigns per timing strategy",
            "Monitor KPIs and adjust in real-time",
        ],
    }


def get_research_summary(research_report: Dict) -> str:
    """Generate human-readable summary of research report."""
    ctx = research_report['event_context']
    plan = research_report.get('marketing_plan', {})

    summary = f"""
EVENT RESEARCH SUMMARY
{'='*60}

Event: {ctx['event']['name']}
Date: {ctx['event']['day_of_week']}, {ctx['event']['date']} at {ctx['event']['time']}
Days Until Event: {ctx['event']['days_until_event']}
Venue: {ctx['venue']['name']}, {ctx['venue']['address']}

INVENTORY STATUS:
• Total Capacity: {ctx['inventory']['total_capacity']} tickets
• Sold: {ctx['inventory']['sold']} ({ctx['inventory']['sell_through_percent']}%)
• Available: {ctx['inventory']['available']}

PRICING:
• Range: {ctx['pricing']['min_usd']} - {ctx['pricing']['max_usd']}
• Average: {ctx['pricing']['avg_usd']}

MARKETING PLAN:
"""

    if isinstance(plan, dict) and 'target_audience' in plan:
        summary += f"\nTarget Audience: {plan.get('target_audience', 'See full report')}"
        summary += f"\nKey Messaging: {plan.get('key_messaging', 'See full report')}"
        summary += f"\nChannel Strategy: {list(plan.get('channel_strategy', {}).keys())}"

    summary += f"\n\n{'='*60}"
    return summary
