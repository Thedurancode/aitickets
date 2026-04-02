"""
YouTube Research Service
Finds artist's most popular videos, view counts, and links
"""

from typing import Dict, List, Optional
import requests
from app.config import get_settings


def research_artist_youtube(artist_name: str, max_results: int = 5) -> Dict:
    """
    Research artist on YouTube to find most popular videos.

    Args:
        artist_name: Name of the artist/performer to search
        max_results: Number of top videos to return (default: 5)

    Returns:
        Dict with:
        - channel: Channel info (if found)
        - top_videos: List of most popular videos
        - total_views: Total views across top videos
        - subscriber_count: Channel subscribers (if available)
    """
    settings = get_settings()

    if not settings.youtube_api_key:
        return {
            "error": "YouTube API key not configured",
            "note": "Add YOUTUBE_API_KEY to .env to enable video research",
            "fallback": True,
        }

    try:
        # Step 1: Search for artist's channel
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet",
            "q": artist_name,
            "type": "channel",
            "maxResults": 1,
            "key": settings.youtube_api_key,
        }

        search_resp = requests.get(search_url, params=search_params, timeout=10)

        if search_resp.status_code != 200:
            return {
                "error": f"YouTube API error: {search_resp.status_code}",
                "fallback": True,
            }

        search_data = search_resp.json()

        if not search_data.get("items"):
            # No channel found, search for videos instead
            return _search_videos_only(artist_name, max_results)

        # Get channel info
        channel_item = search_data["items"][0]
        channel_id = channel_item["id"]["channelId"]
        channel_title = channel_item["snippet"]["title"]

        # Step 2: Get channel statistics
        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        channel_params = {
            "part": "statistics,snippet",
            "id": channel_id,
            "key": settings.youtube_api_key,
        }

        channel_resp = requests.get(channel_url, params=channel_params, timeout=10)

        channel_stats = {}
        if channel_resp.status_code == 200:
            channel_data = channel_resp.json()
            if channel_data.get("items"):
                stats = channel_data["items"][0].get("statistics", {})
                channel_stats = {
                    "subscriber_count": int(stats.get("subscriberCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                    "view_count": int(stats.get("viewCount", 0)),
                }

        # Step 3: Search for most popular videos from this artist
        video_search_url = "https://www.googleapis.com/youtube/v3/search"
        video_search_params = {
            "part": "snippet",
            "q": artist_name,
            "type": "video",
            "maxResults": max_results * 2,  # Get extra to filter
            "order": "viewCount",  # Most viewed first
            "key": settings.youtube_api_key,
        }

        video_search_resp = requests.get(video_search_url, params=video_search_params, timeout=10)

        if video_search_resp.status_code != 200:
            return {
                "channel": {
                    "name": channel_title,
                    "id": channel_id,
                    "url": f"https://youtube.com/channel/{channel_id}",
                    **channel_stats,
                },
                "top_videos": [],
                "error": "Failed to fetch videos",
            }

        video_search_data = video_search_resp.json()
        video_ids = [item["id"]["videoId"] for item in video_search_data.get("items", [])]

        if not video_ids:
            return {
                "channel": {
                    "name": channel_title,
                    "id": channel_id,
                    "url": f"https://youtube.com/channel/{channel_id}",
                    **channel_stats,
                },
                "top_videos": [],
                "note": "No videos found",
            }

        # Step 4: Get detailed video statistics
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            "part": "statistics,snippet,contentDetails",
            "id": ",".join(video_ids),
            "key": settings.youtube_api_key,
        }

        videos_resp = requests.get(videos_url, params=videos_params, timeout=10)

        if videos_resp.status_code != 200:
            return {
                "channel": {
                    "name": channel_title,
                    "id": channel_id,
                    "url": f"https://youtube.com/channel/{channel_id}",
                    **channel_stats,
                },
                "top_videos": [],
                "error": "Failed to fetch video details",
            }

        videos_data = videos_resp.json()

        # Parse and sort videos by view count
        videos = []
        for item in videos_data.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})

            video_info = {
                "video_id": item["id"],
                "title": snippet.get("title", ""),
                "url": f"https://youtube.com/watch?v={item['id']}",
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", "")[:200],  # First 200 chars
            }
            videos.append(video_info)

        # Sort by view count descending
        videos.sort(key=lambda x: x["view_count"], reverse=True)
        top_videos = videos[:max_results]

        # Calculate totals
        total_views = sum(v["view_count"] for v in top_videos)
        total_likes = sum(v["like_count"] for v in top_videos)

        return {
            "channel": {
                "name": channel_title,
                "id": channel_id,
                "url": f"https://youtube.com/channel/{channel_id}",
                **channel_stats,
            },
            "top_videos": top_videos,
            "total_views": total_views,
            "total_likes": total_likes,
            "average_views": total_views // len(top_videos) if top_videos else 0,
            "video_count": len(top_videos),
        }

    except Exception as e:
        return {
            "error": f"YouTube research failed: {str(e)}",
            "fallback": True,
        }


def _search_videos_only(artist_name: str, max_results: int = 5) -> Dict:
    """
    Fallback: Search for videos when no channel is found.
    """
    settings = get_settings()

    try:
        video_search_url = "https://www.googleapis.com/youtube/v3/search"
        video_search_params = {
            "part": "snippet",
            "q": artist_name,
            "type": "video",
            "maxResults": max_results * 2,
            "order": "viewCount",
            "key": settings.youtube_api_key,
        }

        video_search_resp = requests.get(video_search_url, params=video_search_params, timeout=10)

        if video_search_resp.status_code != 200:
            return {"error": "Failed to search videos", "fallback": True}

        video_search_data = video_search_resp.json()
        video_ids = [item["id"]["videoId"] for item in video_search_data.get("items", [])]

        if not video_ids:
            return {"top_videos": [], "note": "No videos found"}

        # Get video details
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            "part": "statistics,snippet",
            "id": ",".join(video_ids),
            "key": settings.youtube_api_key,
        }

        videos_resp = requests.get(videos_url, params=videos_params, timeout=10)

        if videos_resp.status_code != 200:
            return {"error": "Failed to fetch video details", "fallback": True}

        videos_data = videos_resp.json()

        videos = []
        for item in videos_data.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})

            video_info = {
                "video_id": item["id"],
                "title": snippet.get("title", ""),
                "url": f"https://youtube.com/watch?v={item['id']}",
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "published_at": snippet.get("publishedAt", ""),
            }
            videos.append(video_info)

        videos.sort(key=lambda x: x["view_count"], reverse=True)
        top_videos = videos[:max_results]

        total_views = sum(v["view_count"] for v in top_videos)

        return {
            "channel": None,
            "top_videos": top_videos,
            "total_views": total_views,
            "average_views": total_views // len(top_videos) if top_videos else 0,
            "note": "Videos found but no official channel identified",
        }

    except Exception as e:
        return {
            "error": f"Video search failed: {str(e)}",
            "fallback": True,
        }


def format_view_count(count: int) -> str:
    """Format view count in human-readable format (1.2M, 500K, etc.)"""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)
