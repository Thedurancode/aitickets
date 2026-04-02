"""
Artist Social Media & Web Presence Research
Finds Spotify, Wikipedia, Instagram, TikTok, and performs comprehensive web search
"""

from typing import Dict, Optional
import requests
from app.config import get_settings


def research_spotify(artist_name: str) -> Dict:
    """
    Research artist on Spotify to find profile, monthly listeners, top tracks.

    Args:
        artist_name: Name of the artist

    Returns:
        Dict with Spotify profile, monthly listeners, top tracks, popularity score
    """
    settings = get_settings()

    if not settings.spotify_client_id or not settings.spotify_client_secret:
        return {
            "error": "Spotify API credentials not configured",
            "note": "Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to .env",
            "fallback": True,
        }

    try:
        # Get Spotify access token
        auth_response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
            timeout=10,
        )

        if auth_response.status_code != 200:
            return {"error": "Spotify authentication failed", "fallback": True}

        access_token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Search for artist
        search_url = "https://api.spotify.com/v1/search"
        search_params = {
            "q": artist_name,
            "type": "artist",
            "limit": 1,
        }

        search_resp = requests.get(search_url, headers=headers, params=search_params, timeout=10)

        if search_resp.status_code != 200:
            return {"error": "Spotify search failed", "fallback": True}

        search_data = search_resp.json()

        if not search_data.get("artists", {}).get("items"):
            return {"error": "Artist not found on Spotify", "fallback": True}

        artist = search_data["artists"]["items"][0]
        artist_id = artist["id"]

        # Get artist's top tracks
        top_tracks_url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
        top_tracks_params = {"market": "US"}

        top_tracks_resp = requests.get(
            top_tracks_url,
            headers=headers,
            params=top_tracks_params,
            timeout=10
        )

        top_tracks = []
        if top_tracks_resp.status_code == 200:
            tracks_data = top_tracks_resp.json()
            top_tracks = [
                {
                    "name": track["name"],
                    "url": track["external_urls"]["spotify"],
                    "preview_url": track.get("preview_url"),
                    "popularity": track["popularity"],
                    "album": track["album"]["name"],
                    "album_image": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                }
                for track in tracks_data.get("tracks", [])[:5]
            ]

        return {
            "artist_name": artist["name"],
            "spotify_url": artist["external_urls"]["spotify"],
            "spotify_id": artist_id,
            "followers": artist["followers"]["total"],
            "popularity": artist["popularity"],  # 0-100 score
            "genres": artist["genres"],
            "profile_image": artist["images"][0]["url"] if artist["images"] else None,
            "top_tracks": top_tracks,
            "monthly_listeners": None,  # Requires web scraping (not in API)
        }

    except Exception as e:
        return {
            "error": f"Spotify research failed: {str(e)}",
            "fallback": True,
        }


def research_wikipedia(artist_name: str) -> Dict:
    """
    Research artist on Wikipedia to get biography, career info, awards.

    Args:
        artist_name: Name of the artist

    Returns:
        Dict with Wikipedia summary, full article URL, notable facts
    """
    try:
        # Search Wikipedia
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "opensearch",
            "search": artist_name,
            "limit": 1,
            "namespace": 0,
            "format": "json",
        }

        search_resp = requests.get(search_url, params=search_params, timeout=10)

        if search_resp.status_code != 200:
            return {"error": "Wikipedia search failed", "fallback": True}

        search_data = search_resp.json()

        if not search_data[1]:  # No results
            return {"error": "Artist not found on Wikipedia", "fallback": True}

        page_title = search_data[1][0]
        page_url = search_data[3][0]

        # Get page summary
        summary_params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": page_title,
            "format": "json",
        }

        summary_resp = requests.get(search_url, params=summary_params, timeout=10)

        if summary_resp.status_code != 200:
            return {"error": "Failed to fetch Wikipedia summary", "fallback": True}

        summary_data = summary_resp.json()
        pages = summary_data["query"]["pages"]
        page = next(iter(pages.values()))

        summary = page.get("extract", "")

        # Get page image
        image_params = {
            "action": "query",
            "prop": "pageimages",
            "piprop": "original",
            "titles": page_title,
            "format": "json",
        }

        image_resp = requests.get(search_url, params=image_params, timeout=10)
        image_url = None

        if image_resp.status_code == 200:
            image_data = image_resp.json()
            image_pages = image_data["query"]["pages"]
            image_page = next(iter(image_pages.values()))
            image_url = image_page.get("original", {}).get("source")

        return {
            "page_title": page_title,
            "wikipedia_url": page_url,
            "summary": summary[:500],  # First 500 chars
            "full_summary": summary,
            "image_url": image_url,
        }

    except Exception as e:
        return {
            "error": f"Wikipedia research failed: {str(e)}",
            "fallback": True,
        }


def research_social_media_links(artist_name: str) -> Dict:
    """
    Use AI web search to find artist's social media links.

    Args:
        artist_name: Name of the artist

    Returns:
        Dict with Instagram, TikTok, Twitter/X, Facebook, official website
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        return {
            "error": "OpenRouter API key not configured",
            "note": "Cannot search for social media links without web search",
            "fallback": True,
        }

    try:
        # Use Perplexity AI to search for social media links
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
                        "content": f"""Find the official social media accounts and website for: {artist_name}

Please find and return ONLY the official verified accounts:
1. Instagram - Full URL (https://instagram.com/...)
2. TikTok - Full URL (https://tiktok.com/@...)
3. Twitter/X - Full URL (https://twitter.com/...)
4. Facebook - Full URL (https://facebook.com/...)
5. Official Website - Full URL
6. Bandcamp - Full URL (if exists)
7. SoundCloud - Full URL (if exists)

Return as JSON with keys: instagram, tiktok, twitter, facebook, website, bandcamp, soundcloud
Use null for any that are not found. Only include VERIFIED official accounts."""
                    }
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            social_data = result["choices"][0]["message"]["content"]

            try:
                import json
                return json.loads(social_data)
            except:
                return {"raw_data": social_data, "parsed": False}
        else:
            return {"error": f"API error: {response.status_code}", "fallback": True}

    except Exception as e:
        return {
            "error": f"Social media research failed: {str(e)}",
            "fallback": True,
        }


def research_comprehensive_web_search(artist_name: str) -> Dict:
    """
    Perform comprehensive web search to find news, tours, awards, collaborations.

    Args:
        artist_name: Name of the artist

    Returns:
        Dict with recent news, upcoming tours, awards, notable collaborations
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        return {
            "error": "OpenRouter API key not configured",
            "note": "Cannot perform web search without API access",
            "fallback": True,
        }

    try:
        # Use Perplexity AI for comprehensive web search
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
                        "content": f"""Research comprehensive information about: {artist_name}

Please find and return:
1. Recent News (last 3 months) - 3-5 notable headlines with dates
2. Upcoming Tours/Shows - Any announced tour dates or festivals
3. Awards & Recognition - Grammy nominations, chart positions, industry awards
4. Notable Collaborations - Features, remixes, or collaborations with other artists
5. Career Milestones - Major achievements, viral moments, breakthrough songs
6. Current Trending Status - Are they trending? Why? Any recent viral moments?

Return as JSON with keys: recent_news (array), upcoming_tours (array), awards (array), collaborations (array), career_milestones (array), trending_status (string)"""
                    }
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            web_data = result["choices"][0]["message"]["content"]

            try:
                import json
                return json.loads(web_data)
            except:
                return {"raw_data": web_data, "parsed": False}
        else:
            return {"error": f"API error: {response.status_code}", "fallback": True}

    except Exception as e:
        return {
            "error": f"Web search failed: {str(e)}",
            "fallback": True,
        }


def research_artist_comprehensive(artist_name: str) -> Dict:
    """
    All-in-one function: Research artist across all platforms.

    Combines:
    - Spotify (followers, top tracks, popularity)
    - Wikipedia (biography, summary)
    - Social media links (Instagram, TikTok, Twitter, etc.)
    - Comprehensive web search (news, tours, awards)

    Args:
        artist_name: Name of the artist

    Returns:
        Comprehensive dict with all research data
    """
    return {
        "artist_name": artist_name,
        "spotify": research_spotify(artist_name),
        "wikipedia": research_wikipedia(artist_name),
        "social_media": research_social_media_links(artist_name),
        "web_search": research_comprehensive_web_search(artist_name),
    }


def format_follower_count(count: int) -> str:
    """Format follower count in human-readable format (1.2M, 500K, etc.)"""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)
