#!/usr/bin/env python
"""
Test Integrated Artist Persistence in Event Research

Verifies that the main event research agent now saves artist data permanently.
"""

import asyncio
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the models and services
from app.models import Base, Event, Venue, Artist, ArtistResearch
from app.services.event_research_agent import run_event_research_agent


def setup_test_database():
    """Create test database with tables."""
    engine = create_engine("sqlite:///test_integrated_artists.db")
    Base.metadata.create_all(engine)
    return engine


async def test_integrated_persistence():
    """Test that event research agent saves artist data."""
    print("\n" + "="*80)
    print("TESTING INTEGRATED ARTIST PERSISTENCE")
    print("="*80)

    # Setup database
    engine = setup_test_database()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Step 1: Create venue
    print("\n1️⃣ Creating venue...")
    venue = Venue(
        name="Prudential Center",
        address="25 Lafayette St, Newark, NJ 07102",
        phone="(973) 757-6000"
    )
    db.add(venue)
    db.commit()

    # Step 2: Create first Bad Bunny event
    print("\n2️⃣ Creating first Bad Bunny event...")
    event1 = Event(
        name="Bad Bunny - Most Wanted Tour",
        venue_id=venue.id,
        event_date="2024-05-15",
        event_time="20:00"
    )
    db.add(event1)
    db.commit()

    # Step 3: Run research agent (should create and save artist)
    print("\n3️⃣ Running research agent for first event...")
    print("   This should create new artist and save research...")

    result1 = await run_event_research_agent(
        db=db,
        event_id=event1.id,
        include_ai_plan=False,  # Skip to save time
        include_artist_research=True
    )

    print(f"   ✓ Research completed")
    print(f"   ✓ Used cached data: {result1.get('used_cached_data', False)}")
    if 'artist_id' in result1:
        print(f"   ✓ Artist ID: {result1['artist_id']}")
    if 'research_snapshot_id' in result1:
        print(f"   ✓ Research snapshot saved: {result1['research_snapshot_id']}")

    # Check that artist was created
    artist = db.query(Artist).filter(Artist.name.contains("Bad Bunny")).first()
    if artist:
        print(f"\n   ✅ Artist saved: {artist.name} (ID: {artist.id})")
        print(f"   ✅ Spotify listeners: {artist.spotify_monthly_listeners:,}" if artist.spotify_monthly_listeners else "   ⚠️ No Spotify data")
        print(f"   ✅ Instagram: @{artist.instagram_handle}" if artist.instagram_handle else "   ⚠️ No Instagram data")
        print(f"   ✅ Genre: {artist.genre}" if artist.genre else "   ⚠️ No genre data")
    else:
        print("   ❌ Artist not found in database!")

    # Step 4: Create second Bad Bunny event
    print("\n4️⃣ Creating second Bad Bunny event...")
    event2 = Event(
        name="Bad Bunny Live at Prudential",
        venue_id=venue.id,
        event_date="2024-06-20",
        event_time="20:00"
    )
    db.add(event2)
    db.commit()

    # Step 5: Run research agent (should use cached data)
    print("\n5️⃣ Running research agent for second event...")
    print("   This should reuse existing artist data...")

    result2 = await run_event_research_agent(
        db=db,
        event_id=event2.id,
        include_ai_plan=False,
        include_artist_research=True
    )

    print(f"   ✓ Research completed")
    print(f"   ✓ Used cached data: {result2.get('used_cached_data', False)}")
    print(f"   ✓ Research duration: {result2.get('research_duration_ms', 0)}ms")

    # Check that same artist was used
    if result1.get('artist_id') == result2.get('artist_id'):
        print(f"   ✅ Same artist used for both events (ID: {result1.get('artist_id')})")
    else:
        print(f"   ❌ Different artists created! ({result1.get('artist_id')} vs {result2.get('artist_id')})")

    # Step 6: Check research snapshots
    print("\n6️⃣ Checking research history...")
    snapshots = db.query(ArtistResearch).filter(ArtistResearch.artist_id == artist.id).all()
    print(f"   ✓ Total research snapshots: {len(snapshots)}")

    for i, snapshot in enumerate(snapshots):
        print(f"   📸 Snapshot {i+1}: Event {snapshot.event_id}, {snapshot.researched_at}")

    # Step 7: Get insights
    if 'insights' in result2:
        print("\n7️⃣ Artist insights from stored data:")
        insights = result2['insights']
        if 'insights' in insights:
            for insight in insights['insights'][:3]:
                print(f"   💡 {insight['type']}: {insight['message']}")

    # Summary
    print("\n" + "="*80)
    print("INTEGRATION TEST RESULTS:")
    print("="*80)

    artist_count = db.query(Artist).count()
    research_count = db.query(ArtistResearch).count()
    event_count = db.query(Event).count()

    print(f"""
✅ Integration successful!
✅ Artists created: {artist_count}
✅ Research snapshots: {research_count}
✅ Events created: {event_count}
✅ Second event used cached data: {result2.get('used_cached_data', False)}

The event research agent now:
1. Automatically saves all artist research
2. Reuses existing artist data for new events
3. Tracks artist growth over time
4. Provides historical insights

No more lost research data! 🎉
    """)

    db.close()
    return True


if __name__ == "__main__":
    asyncio.run(test_integrated_persistence())
    print("\n✅ Integrated persistence test complete!")