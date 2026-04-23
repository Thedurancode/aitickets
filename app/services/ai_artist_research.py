"""
AI-Powered Artist Research

Uses OpenRouter LLM to research artists without needing Spotify/YouTube API keys.
Falls back gracefully if no LLM key is configured.
"""

import json
import httpx
from typing import Dict, Optional
from app.config import get_settings

import logging
logger = logging.getLogger(__name__)


def research_artist_with_ai(artist_name: str) -> Dict:
    """
    Research an artist using AI (OpenRouter/OpenAI) to get comprehensive data.

    The LLM has training data on most known artists and can provide:
    - Bio, genres, country, career history
    - Estimated social media stats
    - Top songs, achievements, similar artists
    - Fan demographics and primary markets
    - Image search suggestions

    Returns structured data matching the Artist model fields.
    """
    settings = get_settings()
    api_key = settings.openrouter_api_key or settings.openai_api_key

    if not api_key:
        return {"error": "No LLM API key configured", "fallback": True}

    is_openrouter = bool(settings.openrouter_api_key)
    base_url = "https://openrouter.ai/api/v1" if is_openrouter else "https://api.openai.com/v1"
    model = settings.llm_router_model or ("openai/gpt-4o-mini" if is_openrouter else "gpt-4o-mini")

    prompt = f"""Research the musical artist "{artist_name}" and return a comprehensive JSON profile.

Return ONLY valid JSON with these exact fields (use null for unknown, never guess social media handles you're not confident about):

{{
  "name": "Full artist/stage name",
  "bio": "2-3 paragraph biography covering career highlights, origin story, musical style, and cultural impact",
  "genre": "Primary genre",
  "sub_genres": ["list", "of", "sub-genres"],
  "country_of_origin": "Country",
  "active_since_year": 2000,

  "spotify_followers": 0,
  "spotify_monthly_listeners": 0,
  "spotify_popularity": 0,
  "spotify_genres": ["from", "spotify"],
  "spotify_top_tracks": ["Song 1", "Song 2", "Song 3", "Song 4", "Song 5", "Song 6", "Song 7", "Song 8", "Song 9", "Song 10"],
  "spotify_image_url": "URL to an official artist image if known, otherwise null",

  "youtube_subscribers": 0,
  "youtube_view_count": 0,

  "instagram_handle": "@handle or null",
  "instagram_followers": 0,
  "twitter_handle": "@handle or null",
  "twitter_followers": 0,
  "tiktok_handle": "@handle or null",
  "tiktok_followers": 0,
  "facebook_page": "page name or null",
  "facebook_likes": 0,

  "achievements": ["Achievement 1", "Achievement 2", "Achievement 3"],
  "similar_artists": ["Artist 1", "Artist 2", "Artist 3", "Artist 4", "Artist 5"],

  "fan_demographics": {{
    "age_range": "18-35",
    "gender_split": "60% female, 40% male",
    "primary_ethnicity": "if relevant"
  }},
  "primary_markets": ["City 1", "City 2", "City 3", "City 4", "City 5"],
  "fan_interests": ["Interest 1", "Interest 2", "Interest 3"],

  "average_ticket_price_usd": 0,
  "typical_venue_size": "club/theater/arena/stadium",
  "sellout_velocity": "fast/moderate/slow",

  "image_search_urls": ["URL1", "URL2", "URL3"]
}}

IMPORTANT:
- Use real, accurate data from your knowledge. Do NOT make up numbers.
- For social media stats, use the most recent numbers you know of.
- For image URLs, provide real publicly accessible image URLs if you know them (Wikipedia commons, official sites). Otherwise return empty array.
- For spotify_image_url, use the format: https://i.scdn.co/image/... if you know it, otherwise null.
- Return ONLY the JSON object, no other text."""

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a music industry research expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

        if response.status_code != 200:
            logger.error(f"AI research API error: {response.status_code} - {response.text[:200]}")
            return {"error": f"API error: {response.status_code}", "fallback": True}

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Clean up markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        data["source"] = "ai_research"
        data["fallback"] = False

        logger.info(f"AI research complete for '{artist_name}': {data.get('genre', 'unknown')} artist")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response for '{artist_name}': {e}")
        return {"error": f"Failed to parse AI response: {e}", "fallback": True}
    except Exception as e:
        logger.error(f"AI artist research failed for '{artist_name}': {e}")
        return {"error": f"AI research failed: {e}", "fallback": True}


def populate_artist_from_ai(db, artist, ai_data: Dict) -> None:
    """
    Populate an Artist model instance with data from AI research.
    Only fills in fields that are currently empty/null.
    """
    if ai_data.get("fallback") or ai_data.get("error"):
        return

    def set_if_empty(field, value):
        if value and not getattr(artist, field, None):
            setattr(artist, field, value)

    def set_json_if_empty(field, value):
        if value and not getattr(artist, field, None):
            setattr(artist, field, json.dumps(value) if isinstance(value, (list, dict)) else value)

    # Basic info
    set_if_empty("bio", ai_data.get("bio"))
    set_if_empty("genre", ai_data.get("genre"))
    set_json_if_empty("sub_genres", ai_data.get("sub_genres"))
    set_if_empty("country_of_origin", ai_data.get("country_of_origin"))
    set_if_empty("active_since_year", ai_data.get("active_since_year"))

    # Spotify data
    set_if_empty("spotify_followers", ai_data.get("spotify_followers"))
    set_if_empty("spotify_monthly_listeners", ai_data.get("spotify_monthly_listeners"))
    set_if_empty("spotify_popularity", ai_data.get("spotify_popularity"))
    set_json_if_empty("spotify_genres", ai_data.get("spotify_genres"))
    set_json_if_empty("spotify_top_tracks", ai_data.get("spotify_top_tracks"))
    set_if_empty("spotify_image_url", ai_data.get("spotify_image_url"))

    # YouTube
    set_if_empty("youtube_subscribers", ai_data.get("youtube_subscribers"))
    set_if_empty("youtube_view_count", ai_data.get("youtube_view_count"))

    # Social media
    set_if_empty("instagram_handle", ai_data.get("instagram_handle"))
    set_if_empty("instagram_followers", ai_data.get("instagram_followers"))
    set_if_empty("twitter_handle", ai_data.get("twitter_handle"))
    set_if_empty("twitter_followers", ai_data.get("twitter_followers"))
    set_if_empty("tiktok_handle", ai_data.get("tiktok_handle"))
    set_if_empty("tiktok_followers", ai_data.get("tiktok_followers"))
    set_if_empty("facebook_page", ai_data.get("facebook_page"))
    set_if_empty("facebook_likes", ai_data.get("facebook_likes"))

    # Career info
    set_json_if_empty("achievements", ai_data.get("achievements"))
    set_json_if_empty("similar_artists", ai_data.get("similar_artists"))
    set_json_if_empty("fan_demographics", ai_data.get("fan_demographics"))
    set_json_if_empty("primary_markets", ai_data.get("primary_markets"))
    set_json_if_empty("fan_interests", ai_data.get("fan_interests"))

    # Performance metrics
    if ai_data.get("average_ticket_price_usd"):
        set_if_empty("average_ticket_price", int(ai_data["average_ticket_price_usd"] * 100))
    set_if_empty("typical_venue_size", ai_data.get("typical_venue_size"))
    set_if_empty("sellout_velocity", ai_data.get("sellout_velocity"))

    # Set primary image
    if not artist.primary_image_url:
        artist.primary_image_url = (
            ai_data.get("spotify_image_url") or
            (ai_data.get("image_search_urls", [None])[0])
        )

    # Store reference images
    if ai_data.get("image_search_urls") and not artist.reference_images:
        imgs = [{"url": url, "label": "ai_research"} for url in ai_data["image_search_urls"] if url]
        if imgs:
            artist.reference_images = json.dumps(imgs)

    # Update metadata
    artist.data_source = "ai_research"
    artist.confidence_score = 0.8

    from datetime import datetime, timezone
    artist.last_researched_at = datetime.now(timezone.utc)

    db.commit()
