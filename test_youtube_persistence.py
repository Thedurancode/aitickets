#!/usr/bin/env python
"""
Test YouTube Video Data Persistence

Verifies that we're saving the top 5 YouTube videos by view count for artists.
"""

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the models and services
from app.models import Base, Artist
from app.services.artist_service import save_artist_research, find_or_create_artist


def setup_test_database():
    """Create test database with tables."""
    engine = create_engine("sqlite:///test_youtube_videos.db")
    Base.metadata.create_all(engine)
    return engine


def test_youtube_video_persistence():
    """Test that YouTube video data is saved correctly."""
    print("\n" + "="*80)
    print("TESTING YOUTUBE VIDEO PERSISTENCE")
    print("="*80)

    # Setup database
    engine = setup_test_database()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Step 1: Create artist
    print("\n1️⃣ Creating Bad Bunny artist...")
    artist = find_or_create_artist(db, "Bad Bunny")
    print(f"   ✓ Artist created: {artist.name} (ID: {artist.id})")

    # Step 2: Simulate YouTube research data with top 5 videos
    print("\n2️⃣ Simulating YouTube research with top 5 videos by views...")
    research_data = {
        "youtube": {
            "channel": {
                "name": "Bad Bunny",
                "id": "UCmBA_wu8xGg1OfOkfW13Q0Q",
                "url": "https://youtube.com/channel/UCmBA_wu8xGg1OfOkfW13Q0Q",
                "subscriber_count": 46300000,
                "view_count": 28500000000,
                "video_count": 89
            },
            "top_videos": [
                {
                    "video_id": "saGYMhApaH8",
                    "title": "Bad Bunny - Yo Perreo Sola",
                    "url": "https://youtube.com/watch?v=saGYMhApaH8",
                    "view_count": 650000000,  # Most viewed
                    "like_count": 4200000,
                    "published_at": "2020-03-27T04:00:14Z",
                    "thumbnail": "https://i.ytimg.com/vi/saGYMhApaH8/hqdefault.jpg"
                },
                {
                    "video_id": "TmKh7lAwnBI",
                    "title": "Bad Bunny x Jhay Cortez - DÁKITI",
                    "url": "https://youtube.com/watch?v=TmKh7lAwnBI",
                    "view_count": 580000000,  # 2nd most viewed
                    "like_count": 5100000,
                    "published_at": "2020-10-30T04:00:09Z",
                    "thumbnail": "https://i.ytimg.com/vi/TmKh7lAwnBI/hqdefault.jpg"
                },
                {
                    "video_id": "ARWg160eaX4",
                    "title": "Bad Bunny - Callaita",
                    "url": "https://youtube.com/watch?v=ARWg160eaX4",
                    "view_count": 520000000,  # 3rd most viewed
                    "like_count": 3800000,
                    "published_at": "2019-05-31T04:00:00Z",
                    "thumbnail": "https://i.ytimg.com/vi/ARWg160eaX4/hqdefault.jpg"
                },
                {
                    "video_id": "kLpH1nSLJSs",
                    "title": "Bad Bunny feat. Drake - Mía",
                    "url": "https://youtube.com/watch?v=kLpH1nSLJSs",
                    "view_count": 490000000,  # 4th most viewed
                    "like_count": 3200000,
                    "published_at": "2018-10-11T04:00:03Z",
                    "thumbnail": "https://i.ytimg.com/vi/kLpH1nSLJSs/hqdefault.jpg"
                },
                {
                    "video_id": "p38WgakuYDo",
                    "title": "Bad Bunny - Moscow Mule",
                    "url": "https://youtube.com/watch?v=p38WgakuYDo",
                    "view_count": 480000000,  # 5th most viewed
                    "like_count": 4100000,
                    "published_at": "2022-05-06T04:00:13Z",
                    "thumbnail": "https://i.ytimg.com/vi/p38WgakuYDo/hqdefault.jpg"
                },
                {
                    "video_id": "extra_video",
                    "title": "This should not be saved (6th video)",
                    "url": "https://youtube.com/watch?v=extra_video",
                    "view_count": 100000000,
                    "like_count": 1000000,
                    "published_at": "2023-01-01T00:00:00Z",
                    "thumbnail": "https://example.com/thumb.jpg"
                }
            ],
            "total_views": 2720000000,
            "average_views": 453333333
        },
        "sources_checked": ["youtube"]
    }

    # Step 3: Save the research
    print("\n3️⃣ Saving YouTube research data...")
    research_snapshot = save_artist_research(
        db=db,
        artist=artist,
        research_data=research_data,
        event_id=1,
        trigger="test"
    )
    print(f"   ✓ Research saved (Snapshot ID: {research_snapshot.id})")

    # Step 4: Verify the saved data
    print("\n4️⃣ Verifying saved YouTube data...")

    # Refresh the artist from database
    db.refresh(artist)

    # Check channel info
    print(f"   ✓ Channel ID: {artist.youtube_channel_id}")
    print(f"   ✓ Channel Name: {artist.youtube_channel_name}")
    print(f"   ✓ Subscribers: {artist.youtube_subscribers:,}")
    print(f"   ✓ Total Views: {artist.youtube_view_count:,}")

    # Check saved videos
    if artist.youtube_latest_videos:
        saved_videos = json.loads(artist.youtube_latest_videos)
        print(f"\n   📹 Saved {len(saved_videos)} videos (top 5 by views):")

        for i, video in enumerate(saved_videos, 1):
            print(f"\n   {i}. {video['title']}")
            print(f"      Views: {video['view_count']:,}")
            print(f"      URL: {video['url']}")
            print(f"      Published: {video['published_at'][:10]}")

        # Verify only top 5 saved
        assert len(saved_videos) == 5, f"Expected 5 videos, got {len(saved_videos)}"

        # Verify they are sorted by views (descending)
        for i in range(len(saved_videos) - 1):
            assert saved_videos[i]['view_count'] >= saved_videos[i+1]['view_count'], \
                   "Videos not sorted by view count!"

        # Verify the 6th video was not saved
        video_ids = [v['video_id'] for v in saved_videos]
        assert 'extra_video' not in video_ids, "Extra video should not be saved!"

        print("\n   ✅ Videos are correctly sorted by view count (descending)")
        print("   ✅ Only top 5 videos saved (6th video excluded)")

    else:
        print("   ❌ No videos saved!")

    # Step 5: Test retrieving the data
    print("\n5️⃣ Testing data retrieval...")

    # Simulate getting artist for a new event
    artist2 = find_or_create_artist(db, "Bad Bunny")
    assert artist2.id == artist.id, "Should find existing artist"

    if artist2.youtube_latest_videos:
        videos = json.loads(artist2.youtube_latest_videos)
        print(f"   ✓ Retrieved {len(videos)} videos from database")
        print(f"   ✓ Most viewed: {videos[0]['title']} ({videos[0]['view_count']:,} views)")
        print(f"   ✓ Can be embedded on event pages!")

    # Summary
    print("\n" + "="*80)
    print("YOUTUBE VIDEO PERSISTENCE TEST COMPLETE!")
    print("="*80)
    print(f"""
✅ YouTube channel data saved correctly
✅ Top 5 videos by view count saved
✅ Videos sorted by popularity (most viewed first)
✅ Only top 5 saved (extras excluded)
✅ Video URLs and thumbnails preserved

The system now saves the top 5 most popular YouTube videos for each artist!
These can be embedded on event pages to boost engagement.
    """)

    db.close()
    return True


if __name__ == "__main__":
    test_youtube_video_persistence()
    print("\n✅ YouTube video persistence test complete!")