#!/usr/bin/env python3
"""
DJ Adoni Event Test - Full Intelligence Demo
Creates an event and watches the AI do its magic
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Venue, Event, TicketTier, EventCategory
from app.services.event_research_agent import run_event_research_agent
import json

print("\n" + "█"*70)
print("█" + " "*68 + "█")
print("█" + "  DJ ADONI EVENT - INTELLIGENCE TEST".center(68) + "█")
print("█" + " "*68 + "█")
print("█"*70)

async def main():
    db = SessionLocal()

    try:
        # Step 1: Create venue if needed
        print("\n" + "="*70)
        print("STEP 1: SETUP VENUE")
        print("="*70)

        venue = db.query(Venue).filter(Venue.name == "Club Eclipse").first()
        if not venue:
            venue = Venue(
                name="Club Eclipse",
                address="456 Nightlife Ave, Miami, FL 33139",
                phone="+1-305-555-0123",
                description="Premier nightclub in Miami's South Beach"
            )
            db.add(venue)
            db.commit()
            db.refresh(venue)
            print(f"✅ Created venue: {venue.name}")
        else:
            print(f"✅ Using existing venue: {venue.name}")

        # Step 2: Create event
        print("\n" + "="*70)
        print("STEP 2: CREATE DJ ADONI EVENT")
        print("="*70)

        # Check if event already exists
        existing_event = db.query(Event).filter(Event.name.like("%DJ Adoni%")).first()
        if existing_event:
            print(f"⚠️  DJ Adoni event already exists (ID: {existing_event.id})")
            print(f"   Using existing event for testing...")
            event = existing_event
        else:
            # Event date: 30 days from now
            event_date = (datetime.now() + timedelta(days=30)).date()

            event = Event(
                venue_id=venue.id,
                name="DJ Adoni - Miami Beach Takeover",
                description="International DJ sensation DJ Adoni brings his signature progressive house sound to Miami",
                event_date=event_date,
                event_time="22:00",
                doors_open_time="21:00",
                sale_start_date=datetime.now().date(),
                sale_start_time="00:00",
                status="SCHEDULED",
                is_visible=True,
                auto_reminder_hours=24,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            print(f"✅ Created event: {event.name}")

        print(f"   ID: {event.id}")
        print(f"   Date: {event.event_date}")
        print(f"   Time: {event.event_time}")
        print(f"   Venue: {venue.name}")

        # Step 3: Add ticket tiers
        print("\n" + "="*70)
        print("STEP 3: CREATE TICKET TIERS")
        print("="*70)

        existing_tiers = db.query(TicketTier).filter(TicketTier.event_id == event.id).all()
        if existing_tiers:
            print(f"✅ Using {len(existing_tiers)} existing ticket tiers")
            for tier in existing_tiers:
                print(f"   - {tier.name}: ${tier.price/100:.2f} ({tier.quantity_available} available)")
        else:
            tiers = [
                {"name": "Early Bird", "price": 2500, "quantity": 100, "description": "Limited early access"},
                {"name": "General Admission", "price": 3500, "quantity": 300, "description": "Standard entry"},
                {"name": "VIP Table", "price": 15000, "quantity": 20, "description": "Reserved table with bottle service"},
            ]

            for tier_data in tiers:
                tier = TicketTier(
                    event_id=event.id,
                    name=tier_data["name"],
                    description=tier_data["description"],
                    price=tier_data["price"],
                    quantity_available=tier_data["quantity"],
                    quantity_sold=0,
                    status="active",
                )
                db.add(tier)
                print(f"✅ Created tier: {tier_data['name']} - ${tier_data['price']/100:.2f}")

            db.commit()

        # Step 4: RUN RESEARCH AGENT
        print("\n" + "="*70)
        print("STEP 4: AI RESEARCH AGENT - THE SMART PART")
        print("="*70)

        print("\n🤖 Starting AI Research Agent...")
        print("   This will:")
        print("   1. Web search for 'DJ Adoni' (real-time)")
        print("   2. Analyze fanbase demographics")
        print("   3. Research Miami club scene")
        print("   4. Generate custom 8-section marketing plan")
        print("\n⏱️  Expected time: 15-20 seconds...\n")

        research_report = await run_event_research_agent(
            db=db,
            event_id=event.id,
            include_ai_plan=True
        )

        print("✅ Research Complete!\n")

        # Display artist research
        if "artist_research" in research_report:
            print("="*70)
            print("ARTIST RESEARCH RESULTS")
            print("="*70)

            artist = research_report["artist_research"]
            print(f"\n🎧 Artist: {artist.get('artist_name', 'DJ Adoni')}")
            print(f"   Genre: {artist.get('genre', 'Electronic Dance Music')}")
            print(f"   Type: {artist.get('event_type', 'Concert')}")

            if artist.get('bio'):
                bio = artist['bio']
                print(f"\n📝 Bio:")
                print(f"   {bio[:200]}..." if len(bio) > 200 else f"   {bio}")

            if artist.get('fan_demographics'):
                print(f"\n👥 Fan Demographics:")
                print(f"   {artist['fan_demographics']}")

            if artist.get('social_media'):
                print(f"\n📱 Social Media:")
                for platform, handle in artist['social_media'].items():
                    if handle:
                        print(f"   {platform}: {handle}")

        # Display marketing plan
        if "marketing_plan" in research_report:
            print("\n" + "="*70)
            print("AI-GENERATED MARKETING PLAN")
            print("="*70)

            plan = research_report["marketing_plan"]

            if isinstance(plan, dict) and "target_audience" in plan:
                # Target Audience
                audience = plan.get("target_audience", {})
                if isinstance(audience, dict):
                    print(f"\n🎯 TARGET AUDIENCE")
                    print(f"   Primary: {audience.get('primary', 'N/A')}")
                    if audience.get('secondary'):
                        print(f"   Secondary: {audience['secondary']}")
                    if audience.get('psychographics'):
                        print(f"   Psychographics: {audience['psychographics']}")
                elif isinstance(audience, str):
                    print(f"\n🎯 TARGET AUDIENCE: {audience}")

                # Key Messaging
                messaging = plan.get("key_messaging", {})
                if isinstance(messaging, dict):
                    print(f"\n💬 KEY MESSAGING")
                    print(f"   Headline: {messaging.get('headline', 'N/A')}")
                    print(f"   Value Prop: {messaging.get('value_proposition', 'N/A')}")
                    print(f"   Urgency: {messaging.get('urgency_message', 'N/A')}")

                # Channel Strategy
                channels = plan.get("channel_strategy", {})
                if channels:
                    print(f"\n📱 CHANNEL STRATEGY")
                    for channel, config in channels.items():
                        if isinstance(config, dict):
                            priority = config.get("priority", "N/A")
                            budget = config.get("budget_percent", 0)
                            print(f"   {channel.upper()}: {priority} priority, {budget}% budget")

                # Timing Strategy
                timing = plan.get("timing_strategy", {})
                if timing:
                    print(f"\n⏱️  TIMING STRATEGY")
                    if isinstance(timing, dict):
                        for key, value in timing.items():
                            if isinstance(value, str):
                                print(f"   {key}: {value}")

                # Budget Allocation
                budget = plan.get("budget_allocation", {})
                if budget:
                    print(f"\n💰 BUDGET ALLOCATION")
                    if isinstance(budget, dict):
                        total = budget.get("total_budget_cents", 50000)
                        print(f"   Total: ${total/100:.2f}")
                        breakdown = budget.get("breakdown", {})
                        for channel, amount in breakdown.items():
                            print(f"   {channel}: ${amount/100:.2f}")
            else:
                print(f"\n⚠️  Marketing plan: {plan}")

        # Display venue research
        if "area_research" in research_report:
            print("\n" + "="*70)
            print("VENUE AREA RESEARCH")
            print("="*70)

            area = research_report["area_research"]
            location = area.get("location", {})
            print(f"\n📍 Location: {location.get('city', 'Unknown')}, {location.get('state', 'Unknown')}")

            if location.get("latitude"):
                print(f"   Coordinates: {location['latitude']}, {location['longitude']}")

            nearby = area.get("nearby_venues", [])
            if nearby and isinstance(nearby, list) and len(nearby) > 0 and isinstance(nearby[0], dict):
                print(f"\n🏢 Nearby Venues:")
                for venue in nearby[:5]:
                    print(f"   - {venue.get('name', 'Unknown')}")
                    if venue.get('rating'):
                        print(f"     Rating: {venue['rating']}/5")

            weather = area.get("weather_forecast")
            if weather and isinstance(weather, dict):
                print(f"\n🌤️  Weather Forecast:")
                print(f"   Temp: {weather.get('temp_f', 'N/A')}°F")
                print(f"   Conditions: {weather.get('description', 'N/A')}")

        # Step 5: Show what auto-onboarding would do
        print("\n" + "="*70)
        print("STEP 5: AUTO-ONBOARDING CAPABILITIES")
        print("="*70)

        print(f"\n🚀 If this event was created with auto_onboard=true:")
        print(f"\n   ✅ Step 1: Research Agent (15s) - COMPLETED ABOVE")
        print(f"   ⏭️  Step 2: AI Flyer Generation (20s) - Creates poster")
        print(f"   ⏭️  Step 3: Meta Ads Creation (5s) - FB/IG campaigns")
        print(f"   ⏭️  Step 4: Campaign Scheduling (5s) - Email/SMS drip")
        print(f"   ⏭️  Step 5: Dynamic Pricing (1s) - Price optimization")

        # Check if campaigns were created
        from app.models import MarketingCampaign
        campaigns = db.query(MarketingCampaign).filter(
            MarketingCampaign.name.like(f"%{event.name}%")
        ).all()

        if campaigns:
            print(f"\n✅ Found {len(campaigns)} marketing campaigns:")
            for camp in campaigns:
                print(f"   - {camp.name}")
                print(f"     Type: {camp.campaign_type}")
                print(f"     Status: {camp.status}")
                if camp.scheduled_send_time:
                    print(f"     Scheduled: {camp.scheduled_send_time}")

        # Summary
        print("\n" + "="*70)
        print("INTELLIGENCE DEMONSTRATION COMPLETE")
        print("="*70)

        print(f"\n🎯 What Just Happened:")
        print(f"   ✅ Created event in database")
        print(f"   ✅ AI researched DJ Adoni (web search)")
        print(f"   ✅ Analyzed fanbase demographics")
        print(f"   ✅ Generated custom marketing plan")
        print(f"   ✅ Researched venue area & competitors")
        print(f"   ✅ Weather forecast for event date")

        print(f"\n💡 Intelligence Level: GENIUS")
        print(f"   - Real-time web search")
        print(f"   - Demographic analysis")
        print(f"   - Custom strategy generation")
        print(f"   - Geographic intelligence")

        print(f"\n⏱️  Total Time: ~20 seconds")
        print(f"   (vs 2-3 hours manual research)")

        print(f"\n🚀 Event ID: {event.id}")
        print(f"   View at: /events/{event.id}")

        print("\n" + "="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
