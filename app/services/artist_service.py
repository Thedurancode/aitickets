"""
Artist Service - Save and retrieve artist research data.

Provides intelligent artist data management:
- Check if artist already exists before researching
- Save all research discoveries permanently
- Track artist growth over time
- Provide cross-event intelligence
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Artist, ArtistResearch, Event

logger = logging.getLogger(__name__)


def find_or_create_artist(db: Session, artist_name: str) -> Artist:
    """
    Find existing artist or create new one.
    Uses fuzzy matching to handle slight name variations.
    """
    # First try exact match
    artist = db.query(Artist).filter(
        func.lower(Artist.name) == artist_name.lower()
    ).first()

    if artist:
        logger.info(f"Found existing artist: {artist.name} (ID: {artist.id})")
        return artist

    # Try fuzzy match for variations (e.g., "Bad Bunny" vs "Bad Bunny Tour")
    # Check if name contains known artist
    potential_match = db.query(Artist).filter(
        func.lower(Artist.name).contains(artist_name.lower().split()[0])
    ).first()

    if potential_match and len(artist_name.split()[0]) > 3:  # Avoid false matches on short words
        logger.info(f"Found potential artist match: {potential_match.name}")
        # Could prompt user to confirm match here
        return potential_match

    # Create new artist
    artist = Artist(name=artist_name)
    db.add(artist)
    db.commit()
    logger.info(f"Created new artist: {artist_name} (ID: {artist.id})")

    return artist


def save_artist_research(
    db: Session,
    artist: Artist,
    research_data: Dict[str, Any],
    event_id: Optional[int] = None,
    trigger: str = "event_creation"
) -> ArtistResearch:
    """
    Save comprehensive artist research data.
    Updates Artist record and creates historical snapshot.
    """
    logger.info(f"Saving research for artist: {artist.name}")

    # Update main Artist record with latest data
    if "spotify" in research_data:
        spotify = research_data["spotify"]
        artist.spotify_id = spotify.get("id")
        artist.spotify_followers = spotify.get("followers")
        artist.spotify_monthly_listeners = spotify.get("monthly_listeners")
        artist.spotify_popularity = spotify.get("popularity")
        artist.spotify_top_tracks = json.dumps(spotify.get("top_tracks", []))
        artist.spotify_genres = json.dumps(spotify.get("genres", []))
        artist.spotify_image_url = spotify.get("image_url")

    if "youtube" in research_data:
        youtube = research_data["youtube"]

        # Handle channel info (nested structure)
        channel = youtube.get("channel", {})
        if channel:
            artist.youtube_channel_id = channel.get("id")
            artist.youtube_channel_name = channel.get("name")
            artist.youtube_subscribers = channel.get("subscriber_count")
            artist.youtube_view_count = channel.get("view_count")
            artist.youtube_video_count = channel.get("video_count")

        # Save top videos (sorted by views)
        top_videos = youtube.get("top_videos", [])
        if top_videos:
            # Store simplified version with key info
            videos_to_save = []
            for video in top_videos[:5]:  # Save top 5 most viewed
                videos_to_save.append({
                    "video_id": video.get("video_id"),
                    "title": video.get("title"),
                    "url": video.get("url"),
                    "view_count": video.get("view_count"),
                    "published_at": video.get("published_at"),
                    "thumbnail": video.get("thumbnail")
                })
            artist.youtube_latest_videos = json.dumps(videos_to_save)

    if "social_media" in research_data:
        social = research_data["social_media"]
        artist.instagram_handle = social.get("instagram")
        artist.instagram_followers = social.get("instagram_followers")
        artist.twitter_handle = social.get("twitter")
        artist.twitter_followers = social.get("twitter_followers")
        artist.tiktok_handle = social.get("tiktok")
        artist.tiktok_followers = social.get("tiktok_followers")
        artist.facebook_page = social.get("facebook")
        artist.facebook_likes = social.get("facebook_likes")

    if "artist_info" in research_data:
        info = research_data["artist_info"]
        artist.genre = info.get("genre")
        artist.sub_genres = json.dumps(info.get("sub_genres", []))
        artist.bio = info.get("bio")
        artist.achievements = json.dumps(info.get("achievements", []))
        artist.similar_artists = json.dumps(info.get("similar_artists", []))
        artist.country_of_origin = info.get("country_of_origin")
        artist.active_since_year = info.get("active_since_year")

    if "fan_demographics" in research_data:
        demographics = research_data["fan_demographics"]
        artist.fan_demographics = json.dumps(demographics)
        artist.primary_markets = json.dumps(research_data.get("primary_markets", []))
        artist.fan_interests = json.dumps(research_data.get("fan_interests", []))

    # Performance metrics (if available from historical data)
    if "performance_metrics" in research_data:
        metrics = research_data["performance_metrics"]
        artist.average_ticket_price = metrics.get("average_ticket_price")
        artist.typical_venue_size = metrics.get("typical_venue_size")
        artist.sellout_velocity = metrics.get("sellout_velocity")

    # Update research metadata
    artist.last_researched_at = datetime.now(timezone.utc)
    artist.research_version += 1 if artist.research_version else 1
    artist.data_source = research_data.get("data_source", "automated_research")
    artist.confidence_score = calculate_data_completeness(research_data)

    # Create historical snapshot
    research_snapshot = ArtistResearch(
        artist_id=artist.id,
        event_id=event_id,
        research_data=json.dumps(research_data),
        trigger=trigger,
        spotify_listeners_snapshot=artist.spotify_monthly_listeners,
        instagram_followers_snapshot=artist.instagram_followers,
        youtube_subscribers_snapshot=artist.youtube_subscribers,
        sources_checked=json.dumps(research_data.get("sources_checked", [])),
        data_completeness=artist.confidence_score,
        research_duration_ms=research_data.get("research_duration_ms")
    )
    db.add(research_snapshot)

    db.commit()
    logger.info(f"Saved research snapshot ID: {research_snapshot.id}")

    return research_snapshot


def get_artist_with_history(db: Session, artist_id: int) -> Dict[str, Any]:
    """
    Get artist with growth metrics and historical data.
    """
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        return None

    # Get historical snapshots
    history = db.query(ArtistResearch).filter(
        ArtistResearch.artist_id == artist_id
    ).order_by(ArtistResearch.researched_at.desc()).limit(10).all()

    # Calculate growth metrics
    growth_metrics = {}
    if len(history) >= 2:
        latest = history[0]
        previous = history[-1]

        if latest.spotify_listeners_snapshot and previous.spotify_listeners_snapshot:
            growth_metrics["spotify_growth"] = {
                "absolute": latest.spotify_listeners_snapshot - previous.spotify_listeners_snapshot,
                "percentage": ((latest.spotify_listeners_snapshot - previous.spotify_listeners_snapshot)
                              / previous.spotify_listeners_snapshot * 100)
            }

        if latest.instagram_followers_snapshot and previous.instagram_followers_snapshot:
            growth_metrics["instagram_growth"] = {
                "absolute": latest.instagram_followers_snapshot - previous.instagram_followers_snapshot,
                "percentage": ((latest.instagram_followers_snapshot - previous.instagram_followers_snapshot)
                              / previous.instagram_followers_snapshot * 100)
            }

    return {
        "artist": {
            "id": artist.id,
            "name": artist.name,
            "genre": artist.genre,
            "spotify_listeners": artist.spotify_monthly_listeners,
            "instagram_followers": artist.instagram_followers,
            "last_researched": artist.last_researched_at.isoformat() if artist.last_researched_at else None
        },
        "growth_metrics": growth_metrics,
        "research_history": [
            {
                "id": r.id,
                "researched_at": r.researched_at.isoformat(),
                "spotify_listeners": r.spotify_listeners_snapshot,
                "instagram_followers": r.instagram_followers_snapshot,
                "completeness": r.data_completeness
            }
            for r in history
        ]
    }


def should_refresh_research(artist: Artist) -> bool:
    """
    Determine if artist research should be refreshed.

    Refresh if:
    - Never researched
    - Last research > 30 days old
    - Missing critical data
    """
    if not artist.last_researched_at:
        return True

    # Check age of data
    # Make sure both datetimes are timezone-aware
    if artist.last_researched_at.tzinfo is None:
        # If last_researched_at is naive, assume it's UTC
        from datetime import timezone as tz
        last_researched = artist.last_researched_at.replace(tzinfo=tz.utc)
    else:
        last_researched = artist.last_researched_at

    days_old = (datetime.now(timezone.utc) - last_researched).days
    if days_old > 30:
        return True

    # Check data completeness
    if not artist.spotify_id or not artist.instagram_handle:
        return True

    return False


def calculate_data_completeness(research_data: Dict[str, Any]) -> float:
    """
    Calculate how complete the research data is (0.0 to 1.0).
    """
    total_fields = 0
    filled_fields = 0

    # Check Spotify data
    spotify_fields = ["id", "followers", "monthly_listeners", "top_tracks", "image_url"]
    if "spotify" in research_data:
        for field in spotify_fields:
            total_fields += 1
            if research_data["spotify"].get(field):
                filled_fields += 1

    # Check YouTube data
    if "youtube" in research_data:
        youtube = research_data["youtube"]
        # Check for channel info
        if youtube.get("channel"):
            channel_fields = ["id", "subscriber_count", "view_count"]
            for field in channel_fields:
                total_fields += 1
                if youtube["channel"].get(field):
                    filled_fields += 1
        # Check for videos
        total_fields += 1
        if youtube.get("top_videos"):
            filled_fields += 1

    # Check social media
    social_fields = ["instagram", "twitter", "tiktok"]
    if "social_media" in research_data:
        for field in social_fields:
            total_fields += 1
            if research_data["social_media"].get(field):
                filled_fields += 1

    # Check artist info
    info_fields = ["genre", "bio", "similar_artists"]
    if "artist_info" in research_data:
        for field in info_fields:
            total_fields += 1
            if research_data["artist_info"].get(field):
                filled_fields += 1

    return filled_fields / total_fields if total_fields > 0 else 0.0


def get_similar_artists(db: Session, artist_id: int) -> list:
    """
    Get artists marked as similar to this artist.
    """
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist or not artist.similar_artists:
        return []

    similar_names = json.loads(artist.similar_artists)

    # Find these artists in our database
    similar_artists = db.query(Artist).filter(
        Artist.name.in_(similar_names)
    ).all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "genre": a.genre,
            "spotify_listeners": a.spotify_monthly_listeners
        }
        for a in similar_artists
    ]


def get_artist_insights(db: Session, artist_id: int) -> Dict[str, Any]:
    """
    Generate insights about an artist based on their data and history.
    """
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        return None

    # Get all events for this artist
    events = db.query(Event).filter(Event.artist_id == artist_id).all()

    insights = {
        "artist_name": artist.name,
        "total_events": len(events),
        "data_quality": artist.confidence_score,
        "insights": []
    }

    # Insight 1: Popularity tier
    if artist.spotify_monthly_listeners:
        if artist.spotify_monthly_listeners > 50000000:
            insights["insights"].append({
                "type": "popularity",
                "message": f"Superstar artist with {artist.spotify_monthly_listeners:,} monthly Spotify listeners",
                "recommendation": "Maximize venue capacity and premium pricing"
            })
        elif artist.spotify_monthly_listeners > 10000000:
            insights["insights"].append({
                "type": "popularity",
                "message": f"Major artist with {artist.spotify_monthly_listeners:,} monthly listeners",
                "recommendation": "Large venues recommended, strong demand expected"
            })

    # Insight 2: Growth trajectory
    research_history = db.query(ArtistResearch).filter(
        ArtistResearch.artist_id == artist_id
    ).order_by(ArtistResearch.researched_at.desc()).limit(5).all()

    if len(research_history) >= 2:
        latest = research_history[0]
        oldest = research_history[-1]
        if latest.spotify_listeners_snapshot and oldest.spotify_listeners_snapshot:
            growth_rate = ((latest.spotify_listeners_snapshot - oldest.spotify_listeners_snapshot)
                          / oldest.spotify_listeners_snapshot * 100)
            if growth_rate > 20:
                insights["insights"].append({
                    "type": "growth",
                    "message": f"Rapidly growing artist: +{growth_rate:.1f}% listener growth",
                    "recommendation": "Book now before prices increase"
                })

    # Insight 3: Best markets
    if artist.primary_markets:
        markets = json.loads(artist.primary_markets)
        if markets:
            insights["insights"].append({
                "type": "markets",
                "message": f"Strong in: {', '.join(markets[:3])}",
                "recommendation": "Focus marketing on these regions"
            })

    # Insight 4: Similar artist performance
    if artist.similar_artists:
        similar_names = json.loads(artist.similar_artists)
        insights["insights"].append({
            "type": "similar_artists",
            "message": f"Similar to: {', '.join(similar_names[:3])}",
            "recommendation": "Use similar targeting and pricing strategies"
        })

    return insights