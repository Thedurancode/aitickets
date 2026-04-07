"""
Enhanced Event Research Agent with Artist Data Persistence

This version saves all artist research permanently to the database,
enabling historical tracking and cross-event intelligence.
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Event, Venue, EventCategory, TicketTier
from app.config import get_settings
from app.services.artist_service import (
    find_or_create_artist,
    save_artist_research,
    should_refresh_research,
    get_artist_insights
)


async def run_event_research_agent_enhanced(
    db: Session,
    event_id: int,
    include_ai_plan: bool = True,
    include_artist_research: bool = True,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Enhanced research agent that saves all discoveries permanently.

    Improvements:
    1. Checks if artist already exists before researching
    2. Saves all research data to database
    3. Tracks artist growth over time
    4. Provides insights from historical data
    """
    start_time = time.time()

    # Get event details
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Extract artist name from event name
    # Common patterns: "Artist Name - Tour Name", "Artist Name Live", etc.
    artist_name = extract_artist_name(event.name)

    # Find or create artist in database
    artist = find_or_create_artist(db, artist_name)

    # Link artist to event
    if not event.artist_id:
        event.artist_id = artist.id
        db.commit()

    result = {
        "event_id": event_id,
        "event_name": event.name,
        "artist_id": artist.id,
        "artist_name": artist.name,
        "used_cached_data": False
    }

    # Check if we need to research or can use existing data
    needs_research = should_refresh_research(artist) or force_refresh

    if not needs_research:
        # Use existing artist data
        result["used_cached_data"] = True
        result["artist_data"] = {
            "name": artist.name,
            "genre": artist.genre,
            "spotify_listeners": artist.spotify_monthly_listeners,
            "instagram_handle": artist.instagram_handle,
            "instagram_followers": artist.instagram_followers,
            "last_researched": artist.last_researched_at.isoformat() if artist.last_researched_at else None
        }

        # Get historical insights
        result["insights"] = get_artist_insights(db, artist.id)

    else:
        # Perform new research
        research_data = await perform_comprehensive_research(artist_name, event.description)

        # Save research to database
        research_snapshot = save_artist_research(
            db=db,
            artist=artist,
            research_data=research_data,
            event_id=event_id,
            trigger="event_creation"
        )

        result["research_snapshot_id"] = research_snapshot.id
        result["artist_data"] = research_data

        # Get insights with new data
        result["insights"] = get_artist_insights(db, artist.id)

    # Add event context
    result["event_context"] = analyze_event_context_for_marketing(db, event)

    # Generate marketing plan if requested
    if include_ai_plan:
        result["marketing_plan"] = await generate_ai_marketing_plan(
            event=event,
            artist_data=result["artist_data"],
            context=result["event_context"]
        )

    # Calculate research duration
    research_duration_ms = int((time.time() - start_time) * 1000)
    result["research_duration_ms"] = research_duration_ms

    return result


def extract_artist_name(event_name: str) -> str:
    """
    Extract artist name from event name.

    Common patterns:
    - "Bad Bunny - Most Wanted Tour" -> "Bad Bunny"
    - "Drake Live at Madison Square Garden" -> "Drake"
    - "Taylor Swift Eras Tour" -> "Taylor Swift"
    """
    # Remove common suffixes
    suffixes_to_remove = [
        " - ", " Live", " Tour", " Concert", " at ", " @ ",
        " World Tour", " Festival", " Show", " Performance"
    ]

    artist_name = event_name
    for suffix in suffixes_to_remove:
        if suffix in artist_name:
            artist_name = artist_name.split(suffix)[0]
            break

    return artist_name.strip()


async def perform_comprehensive_research(artist_name: str, event_description: Optional[str]) -> Dict[str, Any]:
    """
    Perform comprehensive research on artist using multiple sources.
    """
    settings = get_settings()
    research_data = {
        "artist_name": artist_name,
        "researched_at": datetime.utcnow().isoformat(),
        "sources_checked": []
    }

    # 1. Spotify Research
    try:
        from app.services.artist_social_research import research_spotify
        spotify_data = await research_spotify(artist_name)
        if spotify_data:
            research_data["spotify"] = spotify_data
            research_data["sources_checked"].append("spotify")
    except Exception as e:
        print(f"Spotify research failed: {e}")

    # 2. YouTube Research
    try:
        from app.services.youtube_research import research_artist_youtube
        youtube_data = await research_artist_youtube(artist_name)
        if youtube_data:
            research_data["youtube"] = youtube_data
            research_data["sources_checked"].append("youtube")
    except Exception as e:
        print(f"YouTube research failed: {e}")

    # 3. Wikipedia Research
    try:
        from app.services.artist_social_research import research_wikipedia
        wiki_data = await research_wikipedia(artist_name)
        if wiki_data:
            research_data["wikipedia"] = wiki_data
            research_data["sources_checked"].append("wikipedia")
    except Exception as e:
        print(f"Wikipedia research failed: {e}")

    # 4. Social Media Research
    try:
        from app.services.artist_social_research import research_social_media_links
        social_data = await research_social_media_links(artist_name)
        if social_data:
            research_data["social_media"] = social_data
            research_data["sources_checked"].append("social_media")
    except Exception as e:
        print(f"Social media research failed: {e}")

    # 5. Web Search for Additional Info
    if settings.openrouter_api_key:
        try:
            artist_info = await research_artist_via_llm(artist_name, event_description)
            if artist_info:
                research_data["artist_info"] = artist_info
                research_data["sources_checked"].append("llm_research")
        except Exception as e:
            print(f"LLM research failed: {e}")

    # 6. Extract fan demographics
    research_data["fan_demographics"] = extract_fan_demographics(research_data)

    return research_data


async def research_artist_via_llm(artist_name: str, description: Optional[str]) -> Dict[str, Any]:
    """
    Use LLM to research artist information from web.
    """
    import requests
    settings = get_settings()

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "perplexity/llama-3.1-sonar-large-128k-online",
                "messages": [
                    {
                        "role": "user",
                        "content": f"""Research the artist/performer: {artist_name}

Please find and return as JSON:
1. genre - Primary music genre
2. sub_genres - List of sub-genres
3. bio - 2-3 sentence biography
4. achievements - List of major achievements/awards
5. similar_artists - List of 3-5 similar artists
6. country_of_origin - Country they're from
7. active_since_year - Year they started
8. typical_venue_size - small/medium/large/stadium
9. fan_age_range - Typical age range of fans
10. fan_interests - Common interests of their fans

Return ONLY valid JSON."""
                    }
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return json.loads(result["choices"][0]["message"]["content"])
    except:
        pass

    return {}


def extract_fan_demographics(research_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and synthesize fan demographics from all research sources.
    """
    demographics = {
        "age_range": "18-35",  # Default
        "gender_split": {"male": 50, "female": 50},
        "primary_languages": ["English"],
        "interests": []
    }

    # From Spotify genres
    if "spotify" in research_data and "genres" in research_data["spotify"]:
        genres = research_data["spotify"]["genres"]
        if "latin" in str(genres).lower() or "reggaeton" in str(genres).lower():
            demographics["primary_languages"] = ["Spanish", "English"]
            demographics["age_range"] = "18-35"
            demographics["interests"].extend(["Latin Music", "Reggaeton", "Latin Culture"])
        elif "k-pop" in str(genres).lower():
            demographics["age_range"] = "16-28"
            demographics["gender_split"] = {"male": 30, "female": 70}
            demographics["interests"].extend(["K-Pop", "Korean Culture", "Fashion"])

    # From artist info
    if "artist_info" in research_data:
        info = research_data["artist_info"]
        if "fan_age_range" in info:
            demographics["age_range"] = info["fan_age_range"]
        if "fan_interests" in info:
            demographics["interests"].extend(info["fan_interests"])

    return demographics


def analyze_event_context_for_marketing(db: Session, event: Event) -> Dict[str, Any]:
    """
    Analyze event context for marketing planning.
    """
    venue = db.query(Venue).filter(Venue.id == event.venue_id).first()
    tiers = db.query(TicketTier).filter(TicketTier.event_id == event.id).all()

    # Calculate pricing strategy
    price_points = [tier.price for tier in tiers]

    return {
        "venue": {
            "name": venue.name if venue else "Unknown",
            "address": venue.address if venue else "Unknown",
            "capacity": sum(tier.quantity_available for tier in tiers)
        },
        "pricing": {
            "min_price_cents": min(price_points) if price_points else 0,
            "max_price_cents": max(price_points) if price_points else 0,
            "average_price_cents": sum(price_points) / len(price_points) if price_points else 0,
            "tier_count": len(tiers)
        },
        "inventory": {
            "total_tickets": sum(tier.quantity_available for tier in tiers),
            "sold": sum(tier.quantity_sold for tier in tiers),
            "available": sum(tier.quantity_available - tier.quantity_sold for tier in tiers)
        }
    }


async def generate_ai_marketing_plan(
    event: Event,
    artist_data: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate AI marketing plan based on artist and event data.
    """
    # This would use the artist data to create targeted marketing strategies
    plan = {
        "target_audience": {
            "primary": extract_primary_audience(artist_data),
            "secondary": extract_secondary_audience(artist_data)
        },
        "messaging": {
            "key_message": f"Don't miss {artist_data.get('artist_name', event.name)}!",
            "urgency": "Limited tickets available"
        },
        "channels": recommend_marketing_channels(artist_data),
        "budget_allocation": calculate_budget_allocation(artist_data, context)
    }

    return plan


def extract_primary_audience(artist_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract primary target audience from artist data."""
    demographics = artist_data.get("fan_demographics", {})
    return {
        "age_range": demographics.get("age_range", "18-35"),
        "interests": demographics.get("interests", []),
        "languages": demographics.get("primary_languages", ["English"])
    }


def extract_secondary_audience(artist_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract secondary target audience."""
    # Could target fans of similar artists
    similar = []
    if "artist_info" in artist_data and "similar_artists" in artist_data["artist_info"]:
        similar = artist_data["artist_info"]["similar_artists"]

    return {
        "similar_artist_fans": similar,
        "broader_genre_fans": True
    }


def recommend_marketing_channels(artist_data: Dict[str, Any]) -> list:
    """Recommend marketing channels based on artist profile."""
    channels = ["meta_ads", "google_ads"]  # Always use these

    # Add platform-specific channels based on artist
    if "social_media" in artist_data:
        if artist_data["social_media"].get("tiktok"):
            channels.append("tiktok_ads")
        if artist_data["social_media"].get("youtube"):
            channels.append("youtube_ads")

    return channels


def calculate_budget_allocation(artist_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, int]:
    """Calculate budget allocation across channels."""
    total_budget = 10000  # $100 default

    # Adjust based on artist popularity
    if "spotify" in artist_data:
        listeners = artist_data["spotify"].get("monthly_listeners", 0)
        if listeners > 10000000:
            total_budget = 50000  # $500 for major artists
        elif listeners > 1000000:
            total_budget = 20000  # $200 for mid-tier

    # Allocate across channels
    return {
        "meta_ads": int(total_budget * 0.5),
        "google_ads": int(total_budget * 0.3),
        "social_organic": int(total_budget * 0.2)
    }