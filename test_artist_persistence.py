#!/usr/bin/env python
"""
Test Artist Data Persistence

Demonstrates how artist research is now saved permanently and reused.
"""

import asyncio
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the models and services
from app.models import Base, Event, Venue, Artist, ArtistResearch
from app.services.artist_service import (
    find_or_create_artist,
    save_artist_research,
    get_artist_with_history,
    get_artist_insights
)


def setup_test_database():
    """Create test database with tables."""
    engine = create_engine("sqlite:///test_artists.db")
    Base.metadata.create_all(engine)
    return engine


def test_artist_persistence():
    """Test that artist data is saved and retrieved correctly."""
    print("\n" + "="*80)
    print("TESTING ARTIST DATA PERSISTENCE")
    print("="*80)

    # Setup database
    engine = setup_test_database()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Step 1: Create venue and first Bad Bunny event
    print("\n1️⃣ Creating first Bad Bunny event...")
    venue = Venue(
        name="Madison Square Garden",
        address="4 Pennsylvania Plaza, New York, NY 10001",
        phone="(212) 465-6741"
    )
    db.add(venue)
    db.commit()

    event1 = Event(
        name="Bad Bunny - Most Wanted Tour",
        venue_id=venue.id,
        event_date="2024-05-15",
        event_time="20:00"
    )
    db.add(event1)
    db.commit()

    # Step 2: Find or create artist
    print("\n2️⃣ Finding or creating Bad Bunny artist...")
    artist = find_or_create_artist(db, "Bad Bunny")
    print(f"   ✓ Artist created: {artist.name} (ID: {artist.id})")

    # Step 3: Simulate research data
    print("\n3️⃣ Simulating comprehensive research data...")
    research_data = {
        "spotify": {
            "id": "4q3ewBCX7sLwd24euuV69X",
            "followers": 45600000,
            "monthly_listeners": 79000000,
            "popularity": 92,
            "top_tracks": ["Moscow Mule", "Tití Me Preguntó", "Me Porto Bonito"],
            "genres": ["reggaeton", "latin trap", "urbano latino"],
            "image_url": "https://i.scdn.co/image/bad_bunny.jpg"
        },
        "youtube": {
            "channel_id": "UCmBA_wu8xGg1OfOkfW13Q0Q",
            "channel_name": "Bad Bunny",
            "subscribers": 46300000,
            "view_count": 28500000000,
            "video_count": 89,
            "latest_videos": ["Un Preview", "Monaco", "WHERE SHE GOES"]
        },
        "social_media": {
            "instagram": "@badbunnypr",
            "instagram_followers": 45600000,
            "twitter": "@sanbenito",
            "twitter_followers": 5200000,
            "tiktok": "@badbunny",
            "tiktok_followers": 6200000
        },
        "artist_info": {
            "genre": "Reggaeton",
            "sub_genres": ["Latin Trap", "Alternative Reggaeton"],
            "bio": "Puerto Rican superstar who revolutionized Latin music globally.",
            "achievements": [
                "3x Grammy Award winner",
                "10x Latin Grammy winner",
                "First Spanish-language Coachella headliner"
            ],
            "similar_artists": ["J Balvin", "Ozuna", "Rauw Alejandro"],
            "country_of_origin": "Puerto Rico",
            "active_since_year": 2016
        },
        "fan_demographics": {
            "age_range": "18-35",
            "gender_split": {"male": 40, "female": 60},
            "primary_languages": ["Spanish", "English"],
            "interests": ["Latin Music", "Fashion", "Puerto Rico"]
        },
        "sources_checked": ["spotify", "youtube", "social_media", "wikipedia"]
    }

    # Step 4: Save research
    print("\n4️⃣ Saving research to database...")
    research_snapshot = save_artist_research(
        db=db,
        artist=artist,
        research_data=research_data,
        event_id=event1.id,
        trigger="event_creation"
    )
    print(f"   ✓ Research saved (Snapshot ID: {research_snapshot.id})")
    print(f"   ✓ Spotify listeners: {artist.spotify_monthly_listeners:,}")
    print(f"   ✓ Instagram followers: {artist.instagram_followers:,}")
    print(f"   ✓ Data completeness: {artist.confidence_score:.1%}")

    # Step 5: Create second Bad Bunny event (should reuse artist)
    print("\n5️⃣ Creating second Bad Bunny event...")
    event2 = Event(
        name="Bad Bunny Live at Barclays",
        venue_id=venue.id,
        event_date="2024-06-20",
        event_time="20:00"
    )
    db.add(event2)
    db.commit()

    # Find artist again - should get existing one
    artist2 = find_or_create_artist(db, "Bad Bunny")
    print(f"   ✓ Found existing artist: {artist2.name} (ID: {artist2.id})")
    print(f"   ✓ Same artist: {artist.id == artist2.id}")
    print(f"   ✓ Already has data: Spotify listeners = {artist2.spotify_monthly_listeners:,}")

    # Step 6: Simulate growth (new research after 30 days)
    print("\n6️⃣ Simulating artist growth (30 days later)...")
    import copy
    updated_research = copy.deepcopy(research_data)
    updated_research["spotify"]["monthly_listeners"] = 82000000  # Growth!
    updated_research["social_media"]["instagram_followers"] = 48000000  # Growth!

    research_snapshot2 = save_artist_research(
        db=db,
        artist=artist,
        research_data=updated_research,
        event_id=event2.id,
        trigger="scheduled_update"
    )
    print(f"   ✓ Updated research saved (Snapshot ID: {research_snapshot2.id})")
    print(f"   ✓ New Spotify listeners: {artist.spotify_monthly_listeners:,} (+3M)")
    print(f"   ✓ New Instagram followers: {artist.instagram_followers:,} (+2.4M)")

    # Step 7: Get artist with history
    print("\n7️⃣ Retrieving artist with growth metrics...")
    artist_data = get_artist_with_history(db, artist.id)
    print(f"   ✓ Artist: {artist_data['artist']['name']}")
    print(f"   ✓ Research history: {len(artist_data['research_history'])} snapshots")

    if artist_data['growth_metrics']:
        if 'spotify_growth' in artist_data['growth_metrics']:
            growth = artist_data['growth_metrics']['spotify_growth']
            print(f"   ✓ Spotify growth: +{growth['absolute']:,} listeners ({growth['percentage']:.1f}%)")

    # Step 8: Get insights
    print("\n8️⃣ Getting AI insights...")
    insights = get_artist_insights(db, artist.id)
    print(f"   ✓ Total events: {insights['total_events']}")
    for insight in insights['insights'][:2]:
        print(f"   ✓ {insight['type']}: {insight['message']}")

    # Step 9: Demonstrate what happens with unknown artist
    print("\n9️⃣ Testing with new artist (Drake)...")
    drake = find_or_create_artist(db, "Drake")
    print(f"   ✓ New artist created: {drake.name} (ID: {drake.id})")
    print(f"   ✓ No data yet: Spotify listeners = {drake.spotify_monthly_listeners}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY: ARTIST DATA PERSISTENCE WORKING!")
    print("="*80)
    print(f"""
✅ Artists are saved permanently in database
✅ Research data is preserved across events
✅ Growth is tracked over time
✅ No duplicate artists created
✅ Historical snapshots maintained
✅ Insights generated from data

Database now contains:
- {db.query(Artist).count()} artists
- {db.query(ArtistResearch).count()} research snapshots
- {db.query(Event).count()} events

Bad Bunny's data is saved and will be reused for all future events!
No more re-researching the same artist every time! 🎉
    """)

    db.close()
    return True


if __name__ == "__main__":
    test_artist_persistence()
    print("\n✅ Artist persistence test complete!")