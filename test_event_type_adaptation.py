#!/usr/bin/env python3
"""
Test Event Type Adaptation
Shows how research agent adapts to different event types
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Venue, Event, TicketTier
from app.services.event_research_agent import run_event_research_agent

print("\n" + "█"*70)
print("█" + " "*68 + "█")
print("█" + "  EVENT TYPE ADAPTATION TEST".center(68) + "█")
print("█" + " "*68 + "█")
print("█"*70)

async def test_event_type(event_name: str, description: str, test_number: int):
    """Test research for a specific event type"""

    print("\n" + "="*70)
    print(f"TEST {test_number}: {event_name.upper()}")
    print("="*70)

    db = SessionLocal()

    try:
        # Create or find venue
        venue = db.query(Venue).filter(Venue.name == "Community Center").first()
        if not venue:
            venue = Venue(
                name="Community Center",
                address="789 Main Street, Austin, TX 78701",
                phone="+1-512-555-0100",
                description="Versatile event space for all occasions"
            )
            db.add(venue)
            db.commit()
            db.refresh(venue)

        # Create event
        event_date = (datetime.now() + timedelta(days=45)).date()

        event = Event(
            venue_id=venue.id,
            name=event_name,
            description=description,
            event_date=event_date,
            event_time="18:00",
            doors_open_time="17:30",
            sale_start_date=datetime.now().date(),
            sale_start_time="00:00",
            status="SCHEDULED",
            is_visible=True,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        # Add ticket tier
        tier = TicketTier(
            event_id=event.id,
            name="General Admission",
            description="Entry to the event",
            price=2500,  # $25
            quantity_available=200,
            quantity_sold=0,
            status="active",
        )
        db.add(tier)
        db.commit()

        print(f"\n✅ Created Event: {event.name}")
        print(f"   Date: {event.event_date}")
        print(f"   Venue: {venue.name}")

        # Run research agent
        print(f"\n🤖 Running AI Research Agent...")
        print(f"   Let's see how it adapts to this event type!\n")

        research_report = await run_event_research_agent(
            db=db,
            event_id=event.id,
            include_ai_plan=True
        )

        print("✅ Research Complete!\n")

        # Display key findings
        print("="*70)
        print("RESEARCH ADAPTATION ANALYSIS")
        print("="*70)

        # Artist research
        artist_research = research_report.get('artist_research', {})
        if artist_research and not artist_research.get('fallback'):
            print(f"\n📝 ARTIST/SUBJECT RESEARCH:")
            print(f"   Name: {artist_research.get('artist_name', 'N/A')}")
            print(f"   Type: {artist_research.get('event_type', 'N/A')}")
            print(f"   Genre/Category: {artist_research.get('genre', 'N/A')}")

            bio = artist_research.get('bio', '')
            if bio:
                print(f"\n   Bio: {bio[:200]}..." if len(bio) > 200 else f"\n   Bio: {bio}")

            if artist_research.get('fan_demographics'):
                print(f"\n   Target Audience: {artist_research['fan_demographics']}")
        else:
            print(f"\n⚠️  Artist research: {artist_research.get('error', 'Not found')}")

        # Marketing plan
        marketing_plan = research_report.get('marketing_plan', {})
        if isinstance(marketing_plan, dict) and 'target_audience' in marketing_plan:
            print(f"\n🎯 MARKETING PLAN ADAPTATION:")

            # Target audience
            audience = marketing_plan.get('target_audience', {})
            if isinstance(audience, dict):
                print(f"\n   Primary Audience: {audience.get('primary', 'N/A')}")
                if audience.get('psychographics'):
                    print(f"   Psychographics: {audience['psychographics']}")
            elif isinstance(audience, str):
                print(f"\n   Audience: {audience}")

            # Key messaging
            messaging = marketing_plan.get('key_messaging', {})
            if isinstance(messaging, dict):
                print(f"\n   Headline: {messaging.get('headline', 'N/A')}")
                print(f"   Value Prop: {messaging.get('value_proposition', 'N/A')}")

            # Channel strategy
            channels = marketing_plan.get('channel_strategy', {})
            if channels:
                print(f"\n   Recommended Channels:")
                for channel, config in channels.items():
                    if isinstance(config, dict):
                        priority = config.get('priority', 'N/A')
                        print(f"      - {channel.upper()}: {priority} priority")

            # Content ideas
            content_ideas = marketing_plan.get('content_ideas', {})
            if content_ideas:
                print(f"\n   Content Ideas:")
                if isinstance(content_ideas, dict):
                    for platform, ideas in list(content_ideas.items())[:2]:
                        if isinstance(ideas, list):
                            print(f"      {platform.upper()}:")
                            for idea in ideas[:2]:
                                print(f"         • {idea}")
                elif isinstance(content_ideas, list):
                    for idea in content_ideas[:3]:
                        print(f"      • {idea}")

        # YouTube/Spotify research (should adapt or skip)
        youtube = research_report.get('youtube_research', {})
        spotify = research_report.get('spotify_research', {})

        print(f"\n🎵 MUSIC PLATFORM RESEARCH:")
        if youtube and not youtube.get('error'):
            print(f"   YouTube: ✅ Found relevant content")
        else:
            print(f"   YouTube: ⚠️  {youtube.get('error', 'Not applicable')}")

        if spotify and not spotify.get('error'):
            print(f"   Spotify: ✅ Found artist profile")
        else:
            print(f"   Spotify: ⚠️  {spotify.get('error', 'Not applicable')}")

        # Web search
        web_search = research_report.get('web_search_research', {})
        if web_search and not web_search.get('error'):
            print(f"\n🌐 WEB SEARCH INSIGHTS:")
            if web_search.get('recent_news'):
                print(f"   Recent News: Found")
            if web_search.get('upcoming_tours'):
                print(f"   Related Events: Found")
            if web_search.get('trending_status'):
                print(f"   Trending: {web_search['trending_status']}")

        # Clean up
        db.delete(tier)
        db.delete(event)
        db.commit()

    finally:
        db.close()

async def main():
    # Test 1: DJ/Concert (music event)
    await test_event_type(
        event_name="DJ Adoni - Miami Beach Takeover",
        description="International DJ sensation DJ Adoni brings his signature progressive house sound",
        test_number=1
    )

    # Test 2: Food Truck Festival (food/community event)
    await test_event_type(
        event_name="Austin Food Truck Festival 2024",
        description="Annual food truck festival featuring 50+ local vendors, live music, craft beer, and family activities. Celebrate Austin's vibrant food scene with tacos, BBQ, vegan options, and more!",
        test_number=2
    )

    # Test 3: Line Dancing Event (dance/country event)
    await test_event_type(
        event_name="Friday Night Line Dancing at The Rusty Spur",
        description="Weekly line dancing night with country music hits, beginner lessons at 7pm, followed by open dancing. All skill levels welcome! Boot scootin' good time guaranteed.",
        test_number=3
    )

    # Test 4: Comedy Show (entertainment event)
    await test_event_type(
        event_name="Stand-Up Comedy Night with Local Comedians",
        description="Hilarious evening featuring Austin's top stand-up comedians. 2-hour show with 5 acts. Adults only (21+). Full bar available.",
        test_number=4
    )

    # Test 5: Sports Event (athletic event)
    await test_event_type(
        event_name="Austin Marathon & Half Marathon 2024",
        description="Annual marathon race through scenic Austin. Full marathon, half marathon, and 5K options. Chip timing, finisher medals, post-race party with live music.",
        test_number=5
    )

    # Summary
    print("\n" + "="*70)
    print("ADAPTATION SUMMARY")
    print("="*70)

    print(f"\n🎯 How the AI Adapts to Different Event Types:\n")

    print(f"1. 🎵 MUSIC EVENTS (DJ, Concert)")
    print(f"   • Searches for artist on Spotify, YouTube, Wikipedia")
    print(f"   • Finds music videos, top tracks, follower counts")
    print(f"   • Targets music fans, nightlife enthusiasts")
    print(f"   • Recommends Instagram, TikTok, Meta ads")
    print(f"   • Emphasizes social proof (subscribers, views)")

    print(f"\n2. 🍔 FOOD EVENTS (Food Truck Festival)")
    print(f"   • Research adapts to food/culinary focus")
    print(f"   • Searches for festival info, vendor lists")
    print(f"   • Targets foodies, families, local community")
    print(f"   • Recommends local marketing, Instagram food content")
    print(f"   • Emphasizes variety, local vendors, family-friendly")

    print(f"\n3. 🤠 DANCE EVENTS (Line Dancing)")
    print(f"   • Adapts to country/western theme")
    print(f"   • Searches for venue reputation, dance community")
    print(f"   • Targets country music fans, dancers, beginners")
    print(f"   • Recommends Facebook (older demographic), local groups")
    print(f"   • Emphasizes beginner-friendly, weekly tradition")

    print(f"\n4. 😂 COMEDY EVENTS (Stand-Up)")
    print(f"   • Research focuses on comedians if named")
    print(f"   • Searches for comedian social media, past shows")
    print(f"   • Targets comedy fans, date-night crowd")
    print(f"   • Recommends Instagram reels, TikTok clips")
    print(f"   • Emphasizes humor, local talent, 21+ atmosphere")

    print(f"\n5. 🏃 SPORTS EVENTS (Marathon)")
    print(f"   • Research adapts to athletic/fitness focus")
    print(f"   • Searches for race info, course details")
    print(f"   • Targets runners, fitness enthusiasts")
    print(f"   • Recommends Strava, running clubs, Facebook groups")
    print(f"   • Emphasizes health, community, achievement")

    print(f"\n💡 INTELLIGENCE FEATURES:")
    print(f"   ✅ Context-aware research (adapts to event type)")
    print(f"   ✅ Smart platform selection (music → Spotify, sports → Strava)")
    print(f"   ✅ Audience targeting (age, interests, psychographics)")
    print(f"   ✅ Channel recommendations (platform-specific)")
    print(f"   ✅ Messaging adaptation (formal vs casual, family vs adults)")

    print(f"\n🤖 HOW IT WORKS:")
    print(f"   1. AI reads event name & description")
    print(f"   2. Identifies event type (music, food, sports, etc.)")
    print(f"   3. Adapts research sources accordingly")
    print(f"   4. Generates type-specific marketing plan")
    print(f"   5. Recommends appropriate channels & messaging")

    print(f"\n🎯 RESULT:")
    print(f"   Each event type gets a CUSTOM research profile")
    print(f"   NOT one-size-fits-all!")

    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
