"""
Meta Ads AI Strategist

Uses LLM to analyze event context and generate optimized ad campaign strategies:
- Smart targeting based on event type, venue, ticket price
- Compelling ad copy variations
- Budget and objective recommendations
- Interest targeting suggestions
"""

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import joinedload, Session

from app.models import Event, Venue, TicketTier, Ticket, EventCategory
from app.services.llm_router import route_to_llm

logger = logging.getLogger(__name__)


# ============== Budget Calculator ==============


def calculate_auto_budget(context: Dict) -> Dict[str, Any]:
    """
    Automatically calculate optimal daily budget based on event characteristics.

    Factors:
    - Event type (concerts, sports, comedy, family)
    - Ticket price point (premium, mid-range, budget)
    - Venue capacity
    - Days until event (urgency)
    - Historical performance of similar events

    Returns budget in cents with reasoning.
    """
    import datetime
    from datetime import timezone

    event = context["event"]
    tickets = context["tickets"]
    similar_stats = context.get("similar_events_stats")

    # Base daily budget - uniform $5/day for all events (adjustable by other factors)
    base_budget = 500  # $5/day in cents

    # Adjust by price tier
    price_tier = classify_price_tier(context)
    price_multipliers = {
        "budget": 0.6,      # Lower spend for cheap tickets
        "mid_range": 1.0,   # Standard
        "premium": 1.5,     # Higher spend for premium events
    }

    price_multiplier = price_multipliers.get(price_tier, 1.0)

    # Adjust by venue capacity
    capacity = tickets["total_capacity"]
    if capacity > 0:
        if capacity < 100:
            capacity_multiplier = 0.5  # Small venue, lower spend
        elif capacity < 300:
            capacity_multiplier = 0.7
        elif capacity < 1000:
            capacity_multiplier = 1.0
        else:
            capacity_multiplier = 1.3  # Large venue, higher spend
    else:
        capacity_multiplier = 1.0

    # Adjust by days until event (urgency)
    try:
        event_date = datetime.datetime.strptime(event["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_until = (event_date - datetime.datetime.now(timezone.utc)).days
    except:
        days_until = 30

    if days_until < 7:
        urgency_multiplier = 1.5  # Urgent - increase spend
    elif days_until < 14:
        urgency_multiplier = 1.2
    elif days_until < 30:
        urgency_multiplier = 1.0
    else:
        urgency_multiplier = 0.8  # Far out - can start slower

    # Adjust by historical performance
    performance_multiplier = 1.0
    if similar_stats:
        avg_revenue = similar_stats.get("average_revenue", 0)
        if avg_revenue > 10000:
            performance_multiplier = 1.3  # Strong history
        elif avg_revenue > 5000:
            performance_multiplier = 1.1
        elif avg_revenue < 1000:
            performance_multiplier = 0.8  # Weak history

    # Calculate final budget
    final_budget = int(
        base_budget
        * price_multiplier
        * capacity_multiplier
        * urgency_multiplier
        * performance_multiplier
    )

    # Round to nearest $10
    final_budget = round(final_budget / 1000) * 1000

    # Minimum and maximum caps
    final_budget = max(500, min(final_budget, 50000))  # $5 - $500 per day

    # Build reasoning
    reasoning_parts = [
        f"Base budget: ${base_budget / 100:.0f}/day",
    ]

    # Only show multiplier details if they're not 1.0
    if price_multiplier != 1.0:
        if price_multiplier > 1:
            reasoning_parts.append(f"Increased {int((price_multiplier - 1) * 100)}% for premium pricing")
        else:
            reasoning_parts.append(f"Decreased {int((1 - price_multiplier) * 100)}% for budget pricing")

    if price_multiplier != 1.0:
        if price_multiplier > 1:
            reasoning_parts.append(f"Increased {int((price_multiplier - 1) * 100)}% for premium pricing")
        else:
            reasoning_parts.append(f"Decreased {int((1 - price_multiplier) * 100)}% for budget pricing")

    if capacity_multiplier != 1.0:
        reasoning_parts.append(f"Adjusted for venue capacity ({capacity} seats)")

    if urgency_multiplier != 1.0:
        reasoning_parts.append(f"Increased spend due to urgency ({days_until} days until event)")

    if performance_multiplier != 1.0 and similar_stats:
        reasoning_parts.append(f"Adjusted based on similar event performance (${avg_revenue:.0f} avg revenue)")

    # If no adjustments, add simple message
    if len(reasoning_parts) == 1:
        reasoning_parts.append("Standard daily budget for event advertising")

    return {
        "daily_budget_cents": final_budget,
        "daily_budget_display": f"${final_budget / 100:.2f}",
        "budget_reasoning": ". ".join(reasoning_parts) + ".",
        "factors": {
            "base_budget_cents": base_budget,
            "price_tier": price_tier,
            "capacity": capacity,
            "days_until_event": days_until,
            "final_budget_cents": final_budget,
        }
    }


# ============== Event Analysis ==============


def analyze_event_context(db: Session, event_id: int) -> Dict[str, Any]:
    """Gather comprehensive context about an event for AI analysis."""
    event = (
        db.query(Event)
        .options(
            joinedload(Event.venue),
            joinedload(Event.categories),
            joinedload(Event.ticket_tiers)
        )
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    # Get sales history for similar events
    from sqlalchemy import func as sqlfunc

    category_ids = [c.id for c in event.categories] if event.categories else []

    similar_events_stats = None
    if category_ids:
        similar_stats = (
            db.query(
                sqlfunc.count(Ticket.id).label("total_tickets"),
                sqlfunc.avg(TicketTier.price).label("avg_price"),
                sqlfunc.sum(TicketTier.price * TicketTier.quantity_sold).label("total_revenue")
            )
            .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
            .join(Event, TicketTier.event_id == Event.id)
            .join(Event.categories)
            .filter(
                Event.id != event_id,
                EventCategory.id.in_(category_ids),
                Ticket.status.in_(["paid", "checked_in"])
            )
            .first()
        )
        if similar_stats.total_tickets:
            similar_events_stats = {
                "total_tickets_sold": int(similar_stats.total_tickets or 0),
                "average_ticket_price": float(similar_stats.avg_price or 0) / 100,
                "average_revenue": float(similar_stats.total_revenue or 0) / 100,
            }

    # Get venue characteristics
    venue_context = {
        "name": event.venue.name,
        "address": event.venue.address,
        "description": event.venue.description,
    }

    # Get ticket tier info
    tiers = []
    lowest_price = None
    highest_price = None
    total_capacity = 0

    for tier in event.ticket_tiers:
        price_dollars = tier.price / 100
        if lowest_price is None or price_dollars < lowest_price:
            lowest_price = price_dollars
        if highest_price is None or price_dollars > highest_price:
            highest_price = price_dollars
        total_capacity += tier.quantity_available

        tiers.append({
            "name": tier.name,
            "price_dollars": price_dollars,
            "available": tier.quantity_available - tier.quantity_sold,
            "sold": tier.quantity_sold,
            "sell_through_percent": round(tier.quantity_sold / max(tier.quantity_available, 1) * 100, 1),
        })

    # Get categories
    categories = [c.name for c in event.categories] if event.categories else []

    # Determine event "vibe" and target audience hints from name/description
    event_keywords = {
        "name": event.name,
        "description": event.description or "",
        "categories": categories,
    }

    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "description": event.description,
            "date": event.event_date,
            "time": event.event_time,
            "categories": categories,
            "is_series": bool(event.series_id),
            "has_image": bool(event.image_url),
            "image_url": event.image_url,
        },
        "venue": venue_context,
        "tickets": {
            "lowest_price_dollars": lowest_price,
            "highest_price_dollars": highest_price,
            "price_range": f"${lowest_price:.0f} - ${highest_price:.0f}" if lowest_price and highest_price else "TBD",
            "total_capacity": total_capacity,
            "tiers": tiers,
        },
        "similar_events_stats": similar_events_stats,
        "existing_ad_copy": {
            "name": event.name,
            "date": event.event_date,
            "time": event.event_time,
            "venue": event.venue.name,
        }
    }


# ============== AI Strategy Generation ==============


async def generate_ad_strategy(
    db: Session,
    event_id: int,
    budget_override_cents: Optional[int] = None,
    radius_override_miles: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate AI-powered ad campaign strategy for an event.

    Returns:
        - Target audience recommendations (age, gender, location radius)
        - Budget recommendation
        - Campaign objective
        - Interest targeting suggestions
        - 3 ad copy variations
        - Call-to-action suggestions
    """

    # Gather event context
    context = analyze_event_context(db, event_id)

    if "error" in context:
        return context

    # Calculate auto-budget (used if no override)
    auto_budget = calculate_auto_budget(context)

    # Use override or auto-calculated budget
    final_budget_cents = budget_override_cents or auto_budget["daily_budget_cents"]

    # Build prompt for AI strategist with calculated budget
    prompt = build_strategist_prompt(context, final_budget_cents, radius_override_miles, auto_budget)

    # Call LLM
    try:
        llm_response = await route_to_llm(
            prompt=prompt,
            response_format="json",
            system="You are an expert Facebook/Instagram Ads strategist for live events. You understand audience targeting, ad creative best practices, and how to drive ticket sales."
        )

        # Parse response
        strategy = json.loads(llm_response)

        # Override AI's budget with our calculated budget (more reliable)
        strategy["campaign"]["daily_budget_cents"] = final_budget_cents
        strategy["campaign"]["auto_calculated_budget"] = auto_budget

        # Add context info
        strategy["event_id"] = event_id
        strategy["event_name"] = context["event"]["name"]
        strategy["analysis"] = {
            "event_type": classify_event_type(context),
            "price_tier": classify_price_tier(context),
            "venue_type": classify_venue_type(context),
        }

        return {
            "success": True,
            "strategy": strategy,
            "auto_budget": auto_budget,
            "context_summary": {
                "event": context["event"]["name"],
                "date": context["event"]["date"],
                "venue": context["venue"]["name"],
                "price_range": context["tickets"]["price_range"],
                "categories": context["event"]["categories"],
                "has_image": context["event"]["has_image"],
                "image_url": context["event"].get("image_url"),
            }
        }

    except Exception as e:
        logger.error(f"Error generating ad strategy: {e}")
        return {
            "error": f"Failed to generate strategy: {str(e)}",
            "fallback_strategy": generate_fallback_strategy(context),
            "auto_budget": auto_budget,
        }


def build_strategist_prompt(context: Dict, budget_cents: int, radius_override: Optional[int], auto_budget: Optional[Dict] = None) -> str:
    """Build the prompt for the AI strategist."""

    event = context["event"]
    venue = context["venue"]
    tickets = context["tickets"]

    # Build budget explanation
    if auto_budget:
        budget_note = f"""
RECOMMENDED BUDGET: ${budget_cents / 100:.2f}/day
Budget Reasoning: {auto_budget.get('budget_reasoning', 'Standard daily budget')}
Factors: Price tier ({auto_budget['factors'].get('price_tier')}), Capacity ({auto_budget['factors'].get('capacity')} seats), Days until event ({auto_budget['factors'].get('days_until_event')})

IMPORTANT: Use ${budget_cents / 100:.2f} as the exact daily_budget_cents in your response.
"""
    else:
        budget_note = f"\nRECOMMENDED BUDGET: ${budget_cents / 100:.2f}/day. Use this exact amount."

    radius_note = ""
    if radius_override:
        radius_note = f"\nRADIUS CONSTRAINT: User specified {radius_override} mile radius. Use this exact radius."
    else:
        radius_note = "\nRADIUS: Recommend a targeting radius based on venue location and event type."

    prompt = f"""You are a Meta Ads expert. Analyze this event and create an optimal advertising strategy.

EVENT DETAILS:
- Name: {event['name']}
- Description: {event.get('description', 'N/A')}
- Date/Time: {event['date']} at {event['time']}
- Categories: {', '.join(event['categories']) if event['categories'] else 'General'}
- Venue: {venue['name']} ({venue.get('address', 'N/A')})
- Event Image: {'Yes - event flyer will be uploaded and used' if event.get('has_image') else 'No - text-only ad'}

TICKET INFO:
- Price Range: {tickets['price_range']}
- Total Capacity: {tickets['total_capacity']}
- Tiers: {len(tickets.get('tiers', []))} tier(s)

{budget_note}
{radius_note}

SIMILAR EVENTS PERFORMANCE:
{context.get('similar_events_stats', 'No historical data available')}

Your task: Generate a complete Facebook/Instagram ad strategy. Return ONLY valid JSON in this exact format:

{{
  "target_audience": {{
    "age_min": 18,
    "age_max": 65,
    "gender": "all",
    "radius_miles": 10,
    "interests": ["interest1", "interest2", "interest3"],
    "audience_description": "Why this targeting makes sense for this event"
  }},
  "campaign": {{
    "objective": "traffic|engagement|awareness|leads",
    "objective_reasoning": "Why this objective",
    "daily_budget_cents": 5000,
    "budget_reasoning": "Why this budget"
  }},
  "creative": {{
    "primary_text": "Main ad copy with emojis",
    "headline": "Short headline",
    "description": "Supporting text",
    "call_to_action": "GET_TICKETS"
  }},
  "variations": [
    {{
      "angle": "urgency",
      "primary_text": "Urgency-focused copy",
      "headline": "FOMO headline"
    }},
    {{
      "angle": "social_proof",
      "primary_text": "Social proof copy",
      "headline": "Popularity headline"
    }},
    {{
      "angle": "value",
      "primary_text": "Value-focused copy",
      "headline": "Value headline"
    }}
  ],
  "recommendations": [
    "Tip 1 for optimization",
    "Tip 2 for targeting",
    "Tip 3 for creative"
  ]
}}

Targeting Guidelines:
- Concerts/Music: Broad appeal, radius 15-30 miles, ages 18-45
- Sports Events: Local fans, radius 25-50 miles, ages 21-55
- Comedy Shows: Nightlife crowd, radius 10-20 miles, ages 25-50
- Family Events: Parents, radius 10-15 miles, ages 25-55
- Premium Events ($100+): Affluent targeting, smaller radius
- Budget Events ($25-): Broad targeting, larger radius

Interest Targeting Suggestions:
- Music: Live music, Concerts, Ticketmaster, Live Nation
- Sports: [Sport name], Sports tickets, Live sports
- Comedy: Stand-up comedy, Comedy clubs, Comedians
- Family: Family activities, Kids activities, Local events

Creative Guidelines:
- Use 2-3 relevant emojis
- Include date, venue, and starting price
- Create urgency (limited tickets, selling fast)
- Clear call-to-action

Return ONLY the JSON. No additional text."""

    return prompt


# ============== Classification Helpers ==============


def classify_event_type(context: Dict) -> str:
    """Classify event type for targeting purposes."""
    categories = [c.lower() for c in context["event"]["categories"]]
    name_lower = context["event"]["name"].lower()

    if any(cat in categories or cat in name_lower for cat in ["concert", "music", "jazz", "rock", "pop"]):
        return "music"
    elif any(cat in categories or cat in name_lower for cat in ["sports", "basketball", "football", "hockey"]):
        return "sports"
    elif any(cat in categories or cat in name_lower for cat in ["comedy", "standup"]):
        return "comedy"
    elif any(cat in categories or cat in name_lower for cat in ["family", "kids", "children"]):
        return "family"
    elif "theater" in categories or "theatre" in name_lower:
        return "theater"
    else:
        return "general"


def classify_price_tier(context: Dict) -> str:
    """Classify event by price point."""
    lowest = context["tickets"]["lowest_price_dollars"]

    if lowest is None:
        return "unknown"
    elif lowest < 25:
        return "budget"
    elif lowest < 75:
        return "mid_range"
    else:
        return "premium"


def classify_venue_type(context: Dict) -> str:
    """Classify venue type."""
    venue_name = context["venue"]["name"].lower()

    if any(word in venue_name for word in ["stadium", "arena", "center"]):
        return "large_venue"
    elif any(word in venue_name for word in ["club", "lounge", "bar"]):
        return "nightlife"
    elif any(word in venue_name for word in ["theater", "theatre", "hall"]):
        return "theater"
    else:
        return "standard"


def generate_fallback_strategy(context: Dict) -> Dict:
    """Generate a reasonable fallback strategy if AI fails."""

    event_type = classify_event_type(context)
    price_tier = classify_price_tier(context)

    # Calculate auto-budget
    auto_budget = calculate_auto_budget(context)

    # Default targeting based on event type
    targeting_defaults = {
        "music": {"age_min": 18, "age_max": 45, "radius": 25},
        "sports": {"age_min": 21, "age_max": 55, "radius": 40},
        "comedy": {"age_min": 25, "age_max": 50, "radius": 15},
        "family": {"age_min": 25, "age_max": 55, "radius": 12},
        "theater": {"age_min": 30, "age_max": 65, "radius": 20},
        "general": {"age_min": 21, "age_max": 55, "radius": 15},
    }

    targeting = targeting_defaults.get(event_type, targeting_defaults["general"])

    return {
        "target_audience": {
            "age_min": targeting["age_min"],
            "age_max": targeting["age_max"],
            "gender": "all",
            "radius_miles": targeting["radius"],
            "interests": [],
            "audience_description": f"Default targeting for {event_type} events"
        },
        "campaign": {
            "objective": "traffic",
            "objective_reasoning": "Drive traffic to event page",
            "daily_budget_cents": auto_budget["daily_budget_cents"],
            "budget_reasoning": auto_budget["budget_reasoning"],
            "auto_calculated_budget": auto_budget
        },
        "creative": {
            "primary_text": f"🎟️ {context['event']['name']}\n\n{context['event']['date']} at {context['event']['time']}\n{context['venue']['name']}\n\nGet your tickets now!",
            "headline": context['event']["name"],
            "description": f"{context['venue']['name']} • {context['event']['date']}",
            "call_to_action": "GET_TICKETS"
        },
        "variations": [],
        "recommendations": [
            "Use AI-generated strategy for better results",
            "Upload event flyer as ad image",
            "Consider promoting 1-2 weeks before event"
        ]
    }


# ============== One-Click Campaign Creation ==============


async def create_strategy_and_campaign(
    db: Session,
    event_id: int,
    budget_cents: Optional[int] = None,
    radius_miles: Optional[int] = None,
    auto_create: bool = False,
) -> Dict[str, Any]:
    """
    Generate strategy and optionally create the campaign in one step.

    Args:
        db: Database session
        event_id: Event to create campaign for
        budget_cents: Optional budget override
        radius_miles: Optional radius override
        auto_create: If True, automatically create the campaign with AI strategy

    Returns:
        Strategy and optionally created campaign details
    """

    # Generate strategy
    strategy_result = await generate_ad_strategy(
        db=db,
        event_id=event_id,
        budget_override_cents=budget_cents,
        radius_override_miles=radius_miles,
    )

    if "error" in strategy_result and "fallback_strategy" not in strategy_result:
        return strategy_result

    strategy = strategy_result.get("strategy", strategy_result.get("fallback_strategy"))

    if not auto_create:
        return {
            "success": True,
            "strategy": strategy,
            "context": strategy_result.get("context_summary"),
            "message": "Strategy generated. Set auto_create=True to create the campaign."
        }

    # Create the campaign with AI-generated strategy
    from app.services.meta_ads import create_campaign_for_event

    target = strategy["target_audience"]
    campaign = strategy["campaign"]
    creative = strategy["creative"]

    result = create_campaign_for_event(
        db=db,
        event_id=event_id,
        budget_cents=budget_cents or campaign["daily_budget_cents"],
        budget_type="daily",
        objective=campaign["objective"],
        radius_miles=radius_miles or target["radius_miles"],
        age_min=target["age_min"],
        age_max=target["age_max"],
        genders=target.get("gender"),
        interests=target.get("interests"),
        primary_text=creative["primary_text"],
        headline=creative["headline"],
        description=creative["description"],
        call_to_action=creative["call_to_action"],
    )

    if result.get("success"):
        result["ai_strategy"] = strategy
        result["message"] = "AI-generated campaign created successfully"

    return result
