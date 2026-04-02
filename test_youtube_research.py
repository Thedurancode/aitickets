#!/usr/bin/env python3
"""
Test YouTube Research - Find artist's most popular videos
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from app.database import SessionLocal
from app.models import Event
from app.services.youtube_research import research_artist_youtube, format_view_count
from app.services.event_research_agent import run_event_research_agent

print("\n" + "█"*70)
print("█" + " "*68 + "█")
print("█" + "  YOUTUBE RESEARCH TEST - DJ ADONI".center(68) + "█")
print("█" + " "*68 + "█")
print("█"*70)

async def main():
    # Test 1: Direct YouTube research
    print("\n" + "="*70)
    print("TEST 1: DIRECT YOUTUBE RESEARCH")
    print("="*70)

    print("\n🔍 Searching YouTube for: DJ Adoni")
    print("   Looking for:")
    print("   - Official channel")
    print("   - Most viewed videos")
    print("   - Subscriber count")
    print("   - Total views\n")

    youtube_data = research_artist_youtube("DJ Adoni", max_results=5)

    if youtube_data.get("error"):
        print(f"⚠️  {youtube_data['error']}")
        print(f"   {youtube_data.get('note', '')}")
        print(f"\n💡 To enable: Add YOUTUBE_API_KEY to .env")
        print(f"   Get key at: https://console.cloud.google.com/apis/credentials")
    else:
        print("✅ YouTube Research Complete!\n")

        # Channel info
        if youtube_data.get("channel"):
            channel = youtube_data["channel"]
            print("📺 CHANNEL FOUND")
            print(f"   Name: {channel.get('name', 'Unknown')}")
            print(f"   URL: {channel.get('url', 'N/A')}")

            if channel.get("subscriber_count"):
                subs = format_view_count(channel["subscriber_count"])
                print(f"   Subscribers: {subs}")

            if channel.get("video_count"):
                print(f"   Videos: {channel['video_count']}")

            if channel.get("view_count"):
                views = format_view_count(channel["view_count"])
                print(f"   Total Views: {views}")

        # Top videos
        if youtube_data.get("top_videos"):
            videos = youtube_data["top_videos"]
            print(f"\n🎬 TOP {len(videos)} VIDEOS")

            for i, video in enumerate(videos, 1):
                print(f"\n   {i}. {video['title'][:60]}...")
                print(f"      URL: {video['url']}")
                print(f"      Views: {format_view_count(video['view_count'])}")
                print(f"      Likes: {format_view_count(video['like_count'])}")

            # Summary stats
            print(f"\n📊 SUMMARY STATS")
            total_views = youtube_data.get("total_views", 0)
            avg_views = youtube_data.get("average_views", 0)
            print(f"   Total Views (top {len(videos)}): {format_view_count(total_views)}")
            print(f"   Average Views: {format_view_count(avg_views)}")

    # Test 2: Integrated with research agent
    print("\n" + "="*70)
    print("TEST 2: INTEGRATED RESEARCH AGENT")
    print("="*70)

    db = SessionLocal()
    try:
        # Find DJ Adoni event
        event = db.query(Event).filter(Event.name.like("%DJ Adoni%")).first()

        if not event:
            print("⚠️  DJ Adoni event not found")
            print("   Run: python3 test_dj_adoni.py first")
            return

        print(f"\n🎵 Running full research for: {event.name}")
        print("   This includes:")
        print("   1. Artist web search")
        print("   2. YouTube video research")
        print("   3. Venue area research")
        print("   4. Marketing plan generation\n")

        research_report = await run_event_research_agent(
            db=db,
            event_id=event.id,
            include_ai_plan=True
        )

        print("✅ Full Research Complete!\n")

        # Display YouTube results from integrated research
        if "youtube_research" in research_report:
            youtube = research_report["youtube_research"]

            if youtube.get("error"):
                print(f"⚠️  YouTube: {youtube['error']}")
            else:
                print("📺 YOUTUBE RESULTS (from integrated research)")

                if youtube.get("channel"):
                    channel = youtube["channel"]
                    print(f"   Channel: {channel.get('name', 'Unknown')}")
                    if channel.get("subscriber_count"):
                        print(f"   Subscribers: {format_view_count(channel['subscriber_count'])}")

                if youtube.get("top_videos"):
                    print(f"\n   Top Videos Found: {len(youtube['top_videos'])}")
                    for i, video in enumerate(youtube["top_videos"][:3], 1):
                        print(f"   {i}. {video['title'][:50]}...")
                        print(f"      {format_view_count(video['view_count'])} views")

        # Show how this enriches the marketing plan
        if "marketing_plan" in research_report:
            plan = research_report["marketing_plan"]
            if isinstance(plan, dict) and "content_ideas" in plan:
                print(f"\n💡 MARKETING PLAN ENHANCEMENT")
                print(f"   YouTube data can be used for:")
                print(f"   - Embedding videos on event page")
                print(f"   - Sharing most popular videos in ads")
                print(f"   - Including in email campaigns")
                print(f"   - Social proof (view counts)")

    finally:
        db.close()

    # Summary
    print("\n" + "="*70)
    print("YOUTUBE RESEARCH - INTELLIGENCE BOOST")
    print("="*70)

    print(f"\n🎯 What This Adds:")
    print(f"   ✅ Official artist channel discovery")
    print(f"   ✅ Most viewed videos with links")
    print(f"   ✅ Social proof (subscriber counts, views)")
    print(f"   ✅ Video content for event pages")
    print(f"   ✅ Marketing material for campaigns")

    print(f"\n💡 Intelligence Level: VERY HIGH")
    print(f"   - Real-time YouTube API integration")
    print(f"   - Automatic video ranking by views")
    print(f"   - Channel statistics")
    print(f"   - Content discovery")

    print(f"\n📝 Setup Required:")
    print(f"   1. Get YouTube Data API v3 key")
    print(f"      → https://console.cloud.google.com/apis/credentials")
    print(f"   2. Add to .env: YOUTUBE_API_KEY=your_key_here")
    print(f"   3. Restart server")

    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
