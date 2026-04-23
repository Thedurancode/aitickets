"""
Event Research Agent

Autonomous agent that researches event context (venue, location, date, competitors)
and generates data-driven marketing plans using web search and AI analysis.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models import Event, Venue, EventCategory, TicketTier
from app.config import get_settings
from app.services.youtube_research import research_artist_youtube
from app.services.artist_social_research import (
    research_spotify,
    research_wikipedia,
    research_social_media_links,
    research_comprehensive_web_search,
)
from app.services.ai_artist_research import research_artist_with_ai, populate_artist_from_ai
from app.services.artist_service import (
    find_or_create_artist,
    save_artist_research,
    should_refresh_research,
    get_artist_with_history,
    get_artist_insights,
)


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


def research_artist_or_performer(event_name: str, event_description: Optional[str]) -> Dict:
    """
    Research artist/performer using web search and AI analysis.

    Uses OpenRouter to search the web and extract artist information.
    """
    settings = get_settings()

    # Build search query
    search_query = f"{event_name} artist performer musician biography"

    # Use AI to research artist
    try:
        import requests

        # Use OpenRouter with web search capability
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "perplexity/llama-3.1-sonar-large-128k-online",  # Has web search
                "messages": [
                    {
                        "role": "user",
                        "content": f"""Research information about this event: "{event_name}"

Event description: {event_description or "Not provided"}

Please find and return:
1. Artist/Performer Name - Who is performing?
2. Artist Bio - Brief background (2-3 sentences)
3. Genre/Style - What type of music/performance?
4. Notable Achievements - Awards, hit songs, famous performances
5. Social Media - Instagram, Twitter, Spotify handles (if found)
6. Similar Artists - 3-5 artists with similar style
7. Fan Demographics - Typical age range and interests of fans
8. Event Type - Concert, comedy show, sports event, etc.

If this is not a performance event (e.g., sports, conference), adapt the research accordingly.

Return as JSON with keys: artist_name, bio, genre, achievements, social_media, similar_artists, fan_demographics, event_type"""
                    }
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            artist_data = result["choices"][0]["message"]["content"]

            try:
                import json
                return json.loads(artist_data)
            except:
                return {"raw_data": artist_data, "parsed": False}
        else:
            return {"error": f"API error: {response.status_code}"}

    except Exception as e:
        # Fallback: Basic extraction from event name
        return {
            "artist_name": event_name.split("-")[0].strip() if "-" in event_name else event_name,
            "bio": "Research unavailable - manual addition recommended",
            "genre": "To be determined",
            "event_type": "Live event",
            "note": f"Automatic research failed: {str(e)}",
            "fallback": True,
        }


def research_venue_area(venue_address: str, event_date: Optional[str] = None) -> Dict:
    """
    Research the area around a venue using geocoding and real APIs.

    Uses:
    - Google Places API for nearby venues/competitors
    - OpenWeather API for event date forecast
    - Geopy for geocoding
    """
    from app.config import get_settings

    settings = get_settings()

    # Parse city and state from address
    parts = venue_address.split(",")
    city = parts[-2].strip() if len(parts) >= 2 else "Unknown"
    state = parts[-1].strip() if len(parts) >= 1 else "Unknown"

    result = {
        "location": {
            "city": city,
            "state": state,
            "full_address": venue_address,
        },
        "demographics": {},
        "nearby_venues": [],
        "local_events": [],
        "weather_forecast": None,
    }

    # Geocode the address to get coordinates
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="ai-tickets-research")
        location = geolocator.geocode(venue_address)

        if location:
            result["location"]["latitude"] = location.latitude
            result["location"]["longitude"] = location.longitude

            # Research nearby venues using Google Places API
            if settings.google_places_api_key:
                import requests
                places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                places_params = {
                    "location": f"{location.latitude},{location.longitude}",
                    "radius": 8047,  # 5 miles in meters
                    "type": "night_club|bar|stadium|amusement_park|art_gallery",
                    "key": settings.google_places_api_key,
                }

                try:
                    places_resp = requests.get(places_url, params=places_params, timeout=10)
                    if places_resp.status_code == 200:
                        places_data = places_resp.json()
                        result["nearby_venues"] = [
                            {
                                "name": p["name"],
                                "address": p.get("vicinity", ""),
                                "rating": p.get("rating"),
                                "types": p.get("types", []),
                            }
                            for p in places_data.get("results", [])[:10]
                        ]
                except Exception:
                    result["nearby_venues"] = ["Google Places API unavailable"]
            else:
                result["nearby_venues"] = ["Google Places API key not configured"]

            # Get weather forecast if event date provided
            if event_date and settings.openweather_api_key:
                try:
                    from datetime import datetime
                    event_dt = datetime.strptime(event_date, "%Y-%m-%d")
                    days_away = (event_dt - datetime.now()).days

                    if 0 <= days_away <= 7:
                        # Use 7-day forecast
                        weather_url = "https://api.openweathermap.org/data/2.5/forecast"
                        weather_params = {
                            "lat": location.latitude,
                            "lon": location.longitude,
                            "appid": settings.openweather_api_key,
                            "units": "imperial",
                        }

                        weather_resp = requests.get(weather_url, params=weather_params, timeout=10)
                        if weather_resp.status_code == 200:
                            forecast_data = weather_resp.json()
                            # Find forecast closest to event date
                            for forecast in forecast_data.get("list", []):
                                forecast_date = forecast["dt_txt"].split()[0]
                                if forecast_date == event_date:
                                    result["weather_forecast"] = {
                                        "temp_f": forecast["main"]["temp"],
                                        "description": forecast["weather"][0]["description"],
                                        "humidity": forecast["main"]["humidity"],
                                        "wind_speed_mph": forecast["wind"]["speed"],
                                    }
                                    break
                except Exception:
                    result["weather_forecast"] = "Weather API unavailable"
            elif not settings.openweather_api_key:
                result["weather_forecast"] = "OpenWeather API key not configured"

    except Exception:
        # Geocoding failed, return basic data
        result["demographics"] = {"note": "Geocoding service unavailable"}

    return result


def _generate_event_description(
    event_context: Dict,
    artist_research: Dict,
) -> str:
    """
    Generate engaging event description from artist research.
    """
    artist_name = artist_research.get("artist_name", "")
    bio = artist_research.get("bio", "")
    genre = artist_research.get("genre", "")
    achievements = artist_research.get("achievements", "")

    event_name = event_context['event']['name']
    event_date = event_context['event']['date']
    venue_name = event_context['venue']['name']

    description = f"""Join us for {event_name} at {venue_name} on {event_date}!

{bio}

{achievements}

Don't miss this {genre} experience! Get your tickets now before they sell out.

Event Details:
• Date: {event_date}
• Time: {event_context['event']['time']}
• Venue: {venue_name}
• Location: {event_context['venue']['address']}
"""

    return description.strip()


def generate_marketing_plan(
    event_context: Dict,
    area_research: Dict,
    artist_research: Optional[Dict] = None,
) -> Dict:
    """
    Generate AI-powered marketing plan based on event research.

    Uses OpenRouter LLM to analyze context and create recommendations.
    """
    settings = get_settings()

    # Build research prompt with artist context
    artist_info = ""
    if artist_research and not artist_research.get("fallback"):
        artist_info = f"""
ARTIST/PERFORMER:
- Name: {artist_research.get('artist_name', 'Unknown')}
- Genre: {artist_research.get('genre', 'Unknown')}
- Bio: {artist_research.get('bio', 'Not available')}
- Achievements: {artist_research.get('achievements', 'Not available')}
- Fan Demographics: {artist_research.get('fan_demographics', 'Not available')}
- Similar Artists: {', '.join(artist_research.get('similar_artists', []))}
"""

    prompt = f"""You are an expert event marketing strategist. Analyze this event and create a comprehensive marketing plan.

EVENT DETAILS:
- Name: {event_context['event']['name']}
- Description: {event_context['event']['description']}
- Date: {event_context['event']['date']} ({event_context['event']['day_of_week']})
- Time: {event_context['event']['time']}
- Days Until Event: {event_context['event']['days_until_event']}
- Season: {event_context['event']['season']}
- Weekend Event: {event_context['event']['is_weekend']}
{artist_info}
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
    include_artist_research: bool = True,
    force_refresh: bool = False,
) -> Dict:
    """
    Enhanced research agent that saves all artist discoveries permanently.

    Improvements:
    1. Checks if artist already exists before researching
    2. Saves all research data to database
    3. Tracks artist growth over time
    4. Provides insights from historical data
    """
    import time
    start_time = time.time()

    # Step 1: Analyze event
    event_context = analyze_event_context(db, event_id)

    if "error" in event_context:
        return event_context

    # Get event details
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Extract artist name from event name
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
        "used_cached_data": False,
        "research_completed_at": datetime.utcnow().isoformat(),
        "event_context": event_context,
    }

    # Check if we need to research or can use existing data
    needs_research = should_refresh_research(artist) or force_refresh

    if not needs_research and artist.spotify_monthly_listeners:
        # Use existing artist data
        result["used_cached_data"] = True
        result["artist_research"] = {
            "artist_name": artist.name,
            "genre": artist.genre,
            "bio": artist.bio,
            "achievements": json.loads(artist.achievements) if artist.achievements else [],
            "similar_artists": json.loads(artist.similar_artists) if artist.similar_artists else [],
            "event_type": "Concert",
        }

        # Add cached research data
        result["spotify_research"] = {
            "id": artist.spotify_id,
            "followers": artist.spotify_followers,
            "monthly_listeners": artist.spotify_monthly_listeners,
            "popularity": artist.spotify_popularity,
            "top_tracks": json.loads(artist.spotify_top_tracks) if artist.spotify_top_tracks else [],
            "genres": json.loads(artist.spotify_genres) if artist.spotify_genres else [],
            "image_url": artist.spotify_image_url,
            "cached": True,
        }

        result["youtube_research"] = {
            "channel_id": artist.youtube_channel_id,
            "channel_name": artist.youtube_channel_name,
            "subscribers": artist.youtube_subscribers,
            "view_count": artist.youtube_view_count,
            "video_count": artist.youtube_video_count,
            "latest_videos": json.loads(artist.youtube_latest_videos) if artist.youtube_latest_videos else [],
            "cached": True,
        }

        result["social_media_research"] = {
            "instagram": artist.instagram_handle,
            "instagram_followers": artist.instagram_followers,
            "twitter": artist.twitter_handle,
            "twitter_followers": artist.twitter_followers,
            "tiktok": artist.tiktok_handle,
            "tiktok_followers": artist.tiktok_followers,
            "cached": True,
        }

        # Get historical insights
        result["insights"] = get_artist_insights(db, artist.id)

    else:
        # Perform new comprehensive research
        research_data = {
            "artist_name": artist_name,
            "researched_at": datetime.utcnow().isoformat(),
            "sources_checked": []
        }

        # Step 2: Research artist/performer
        artist_research = research_artist_or_performer(
            event_context['event']['name'],
            event_context['event']['description']
        )
        result["artist_research"] = artist_research
        if artist_research:
            research_data["artist_info"] = artist_research

        # Step 2.5: Research artist YouTube videos
        youtube_research = research_artist_youtube(artist_name, max_results=5)
        result["youtube_research"] = youtube_research
        if youtube_research and not youtube_research.get("error"):
            research_data["youtube"] = youtube_research
            research_data["sources_checked"].append("youtube")

        # Step 2.6: AI-powered comprehensive artist research (primary source)
        ai_research = research_artist_with_ai(artist_name)
        result["ai_research"] = ai_research
        if ai_research and not ai_research.get("fallback"):
            research_data["ai_research"] = ai_research
            research_data["sources_checked"].append("ai_research")
            # Populate artist model with AI data
            populate_artist_from_ai(db, artist, ai_research)
            logger.info(f"AI research populated artist '{artist_name}' with comprehensive data")

        # Step 2.6b: Research artist on Spotify (fallback/supplement)
        spotify_research = research_spotify(artist_name)
        result["spotify_research"] = spotify_research
        if spotify_research and not spotify_research.get("error"):
            research_data["spotify"] = spotify_research
            research_data["sources_checked"].append("spotify")

        # Step 2.7: Research artist on Wikipedia
        wikipedia_research = research_wikipedia(artist_name)
        result["wikipedia_research"] = wikipedia_research
        if wikipedia_research and not wikipedia_research.get("error"):
            research_data["wikipedia"] = wikipedia_research
            research_data["sources_checked"].append("wikipedia")

        # Step 2.8: Research artist social media links
        social_media_research = research_social_media_links(artist_name)
        result["social_media_research"] = social_media_research
        if social_media_research and not social_media_research.get("error"):
            research_data["social_media"] = social_media_research
            research_data["sources_checked"].append("social_media")

        # Step 2.9: Comprehensive web search (news, tours, awards)
        web_search_research = research_comprehensive_web_search(artist_name)
        result["web_search_research"] = web_search_research
        if web_search_research and not web_search_research.get("error"):
            research_data["web_search"] = web_search_research
            research_data["sources_checked"].append("web_search")

        # Extract fan demographics
        research_data["fan_demographics"] = extract_fan_demographics_from_research(research_data)

        # Calculate research duration
        research_data["research_duration_ms"] = int((time.time() - start_time) * 1000)

        # Save research to database
        research_snapshot = save_artist_research(
            db=db,
            artist=artist,
            research_data=research_data,
            event_id=event_id,
            trigger="event_creation"
        )

        result["research_snapshot_id"] = research_snapshot.id

        # Get insights with new data
        result["insights"] = get_artist_insights(db, artist.id)

    # Step 3: Research area
    area_research = research_venue_area(event_context['venue']['address'])
    result["area_research"] = area_research

    # Step 4: Generate enhanced event description
    enhanced_description = None
    if result.get("artist_research") and not result["artist_research"].get("fallback"):
        enhanced_description = _generate_event_description(
            event_context,
            result["artist_research"]
        )
    result["enhanced_description"] = enhanced_description

    # Step 5: Generate marketing plan (with artist context)
    if include_ai_plan:
        marketing_plan = generate_marketing_plan(
            event_context,
            area_research,
            result.get("artist_research")
        )
        result["marketing_plan"] = marketing_plan
    else:
        result["marketing_plan"] = {"message": "AI plan generation skipped"}

    # Add next steps
    result["next_steps"] = [
        "Review artist bio and update event description" if enhanced_description else None,
        "Embed top YouTube videos on event page" if result.get("youtube_research") and not result["youtube_research"].get("error") else None,
        "Add Spotify player widget to event page" if result.get("spotify_research") and not result["spotify_research"].get("error") else None,
        "Link to artist's Wikipedia page" if result.get("wikipedia_research") and not result["wikipedia_research"].get("error") else None,
        "Add social media follow buttons" if result.get("social_media_research") and not result["social_media_research"].get("error") else None,
        "Promote upcoming tour dates from web search" if result.get("web_search_research") and not result["web_search_research"].get("error") else None,
        "Review marketing plan recommendations",
        "Adjust budget allocations based on sell-through rate",
        "Create Meta ad campaigns using recommended messaging",
        "Schedule email/SMS campaigns per timing strategy",
        "Monitor KPIs and adjust in real-time",
    ]

    # Calculate total duration
    result["research_duration_ms"] = int((time.time() - start_time) * 1000)

    return result


def extract_artist_name(event_name: str) -> str:
    """
    Extract artist name from event name.

    Common patterns:
    - "Bad Bunny - Most Wanted Tour" -> "Bad Bunny"
    - "Drake Live at Madison Square Garden" -> "Drake"
    - "Taylor Swift Eras Tour" -> "Taylor Swift"
    - "Bad Bunny Summer Fest" -> "Bad Bunny"
    """
    # Remove common suffixes/keywords
    suffixes_to_remove = [
        " - ", " Live", " Tour", " Concert", " at ", " @ ",
        " World Tour", " Festival", " Show", " Performance",
        " Fest", " Summer", " Winter", " Spring", " Fall",
        " 2024", " 2025", " 2026", " Night", " Special"
    ]

    artist_name = event_name

    # First pass - remove everything after separator
    for separator in [" - ", " at ", " @ ", " Live"]:
        if separator in artist_name:
            artist_name = artist_name.split(separator)[0]
            break

    # Second pass - remove common suffixes
    for suffix in suffixes_to_remove:
        if artist_name.endswith(suffix):
            artist_name = artist_name[:-len(suffix)]

    # Third pass - if contains known words, extract before them
    for keyword in ["Tour", "Concert", "Festival", "Fest", "Show"]:
        if f" {keyword}" in artist_name:
            artist_name = artist_name.split(f" {keyword}")[0]

    return artist_name.strip()


def extract_fan_demographics_from_research(research_data: Dict) -> Dict:
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
        if "fan_demographics" in info:
            demographics["age_range"] = info.get("fan_age_range", demographics["age_range"])
        if "fan_interests" in info:
            demographics["interests"].extend(info["fan_interests"])

    return demographics


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
