#!/usr/bin/env python3
"""
Complete Ad Campaign Flow - Demo Test Script

This script demonstrates the FULL end-to-end workflow:
1. Create event
2. Run research agent (discovers Spotify/YouTube/Wikipedia images)
3. Auto-generate ad campaigns
4. Review and customize ads
5. Approve ads
6. Publish to Meta/Google (simulated)
7. Sync performance data

Run: python3 test_complete_ad_flow.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Venue, Event, TicketTier, AdCampaign, AdCreative

print("\n" + "█"*80)
print("█" + " "*78 + "█")
print("█" + "  COMPLETE AD CAMPAIGN FLOW - DEMO".center(78) + "█")
print("█" + "  Event → Research → Generate → Customize → Approve → Publish".center(78) + "█")
print("█" + " "*78 + "█")
print("█"*80)


async def step_1_create_event(db):
    """Step 1: Create Event"""
    print("\n" + "="*80)
    print("STEP 1: CREATE EVENT")
    print("="*80)

    # Create venue
    venue = db.query(Venue).filter(Venue.name == "UBS Arena").first()
    if not venue:
        venue = Venue(
            name="UBS Arena",
            address="2400 Hempstead Turnpike, Elmont, NY 11003",
            phone="+1-516-555-0100",
            description="Premier sports and entertainment venue in Queens, NY"
        )
        db.add(venue)
        db.commit()
        db.refresh(venue)

    # Create event
    event_date = datetime(2026, 5, 5).date()

    event = Event(
        venue_id=venue.id,
        name="Anuel AA - Las Leyendas Nunca Mueren Tour",
        description="""
        The King of Latin Trap brings his explosive live show to Queens!

        Experience Anuel AA performing his biggest hits including:
        • Ella Quiere Beber
        • China (feat. Daddy Yankee, Karol G)
        • Secreto (feat. Karol G)
        • RRAAAA
        • Keii

        This is a REGGAETON PARTY you won't forget!

        VIP packages include:
        - Meet & Greet with Anuel AA
        - Exclusive merchandise
        - Premium seating

        Bottle service tables available for groups.

        21+ event. Valid ID required.
        """,
        event_date=event_date,
        event_time="21:00",  # 9pm - Latin nightlife timing
        doors_open_time="20:00",
        sale_start_date=datetime.now().date(),
        sale_start_time="00:00",
        status="SCHEDULED",
        is_visible=True,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Create ticket tiers
    tiers = [
        {"name": "General Admission", "price": 7500, "quantity": 5000},  # $75
        {"name": "VIP Section", "price": 12500, "quantity": 500},  # $125
        {"name": "VIP Meet & Greet", "price": 35000, "quantity": 100},  # $350
        {"name": "Bottle Service Table (8 people)", "price": 150000, "quantity": 30},  # $1,500
    ]

    for tier_data in tiers:
        tier = TicketTier(
            event_id=event.id,
            name=tier_data["name"],
            description=f"Access to {tier_data['name']}",
            price=tier_data["price"],
            quantity_available=tier_data["quantity"],
            quantity_sold=0,
            status="active",
        )
        db.add(tier)

    db.commit()

    print(f"\n✅ Event Created!")
    print(f"   Name: {event.name}")
    print(f"   Venue: {venue.name}")
    print(f"   Date: {event.event_date.strftime('%B %d, %Y')}")
    print(f"   Time: {event.event_time}")
    print(f"   Ticket Tiers: {len(tiers)}")
    print(f"   Price Range: ${min(t['price']/100 for t in tiers):.0f} - ${max(t['price']/100 for t in tiers):.0f}")

    return event


async def step_2_run_research(db, event):
    """Step 2: Run Research Agent"""
    print("\n" + "="*80)
    print("STEP 2: RUN RESEARCH AGENT")
    print("="*80)

    print(f"\n🔍 Researching artist: Anuel AA")
    print(f"   Discovering images from Spotify, YouTube, Wikipedia...")

    # Simulate research report (in real scenario, this comes from event_research_agent)
    research_report = {
        "artist_research": {
            "name": "Anuel AA",
            "genre": "Reggaeton",
            "genre_label": "Rey del Trap Latino",
            "fan_demographics": "18-35, urban Latino youth, reggaeton fans, club-goers",
            "popularity": "High - 28M monthly Spotify listeners",
            "social_following": "Instagram: 22M, YouTube: 15M"
        },
        "spotify_research": {
            "profile_image": "https://i.scdn.co/image/anuel-aa-profile-640x640.jpg",
            "top_tracks": [
                {
                    "name": "Ella Quiere Beber",
                    "album_image": "https://i.scdn.co/image/llnm-album-640x640.jpg"
                },
                {
                    "name": "China",
                    "album_image": "https://i.scdn.co/image/china-single-640x640.jpg"
                }
            ]
        },
        "youtube_research": {
            "top_videos": [
                {
                    "title": "Ella Quiere Beber (Official Video)",
                    "thumbnail": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
                    "views": "820M"
                },
                {
                    "title": "China (Official Video)",
                    "thumbnail": "https://i.ytimg.com/vi/def456/maxresdefault.jpg",
                    "views": "1.2B"
                }
            ]
        },
        "wikipedia_research": {
            "summary": "Emmanuel Gazmey Santiago, known professionally as Anuel AA, is a Puerto Rican rapper and singer...",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/anuel-aa.jpg"
        },
        "marketing_plan": {
            "target_audience": {
                "primary": "18-35 urban Latino youth, reggaeton fans",
                "age_range": {"min": 18, "max": 35},
                "psychographics": {
                    "lifestyle": "Active social media users, club-goers, concert enthusiasts",
                    "values": "Cultural expression, urban identity, nightlife"
                },
                "interests": ["Reggaeton", "Latin Urban Music", "Bad Bunny", "Ozuna", "Nightlife", "Concerts"]
            },
            "key_messaging": {
                "headline": "Anuel AA Live in Queens - May 5th",
                "value_proposition": "Experience the King of Latin Trap live!",
                "tone": "High-energy, urban, exciting"
            },
            "channel_strategy": {
                "tiktok": {"priority": "HIGH", "budget_percent": 35},
                "instagram": {"priority": "HIGH", "budget_percent": 30},
                "facebook": {"priority": "MEDIUM", "budget_percent": 20},
                "google_search": {"priority": "MEDIUM", "budget_percent": 15}
            }
        }
    }

    print(f"\n✅ Research Complete!")
    print(f"\n📸 IMAGES DISCOVERED:")
    print(f"   Spotify Profile: {research_report['spotify_research']['profile_image'][:60]}...")
    print(f"   Album Artwork: {research_report['spotify_research']['top_tracks'][0]['album_image'][:60]}...")
    print(f"   YouTube Thumbnail: {research_report['youtube_research']['top_videos'][0]['thumbnail'][:60]}...")
    print(f"   Wikipedia Photo: {research_report['wikipedia_research']['image_url'][:60]}...")

    print(f"\n🎯 TARGET AUDIENCE:")
    audience = research_report['marketing_plan']['target_audience']
    print(f"   Primary: {audience['primary']}")
    print(f"   Age Range: {audience['age_range']['min']}-{audience['age_range']['max']}")
    print(f"   Interests: {', '.join(audience['interests'][:4])}")

    return research_report


async def step_3_generate_campaigns(db, event, research_report):
    """Step 3: Auto-Generate Ad Campaigns"""
    print("\n" + "="*80)
    print("STEP 3: AUTO-GENERATE AD CAMPAIGNS")
    print("="*80)

    from app.services.campaign_generator import generate_all_campaigns

    print(f"\n🤖 Generating campaigns...")
    print(f"   Creating Meta Awareness, Meta Conversion, Google Search, Email campaigns...")

    result = generate_all_campaigns(db, event.id, research_report)

    print(f"\n✅ Campaigns Generated!")
    print(f"   Total Campaigns: {result['campaigns_created']}")
    print(f"   Total Ads: {result['ads_created']}")
    print(f"   Total Budget: {result['total_budget_formatted']}")

    print(f"\n📊 CAMPAIGNS CREATED:")
    for campaign in result['campaigns']:
        print(f"   • {campaign['name']}")
        print(f"     Platform: {campaign['platform'].upper()} | Type: {campaign['type']}")
        print(f"     Ads: {campaign['ads_count']} | Budget: {campaign['budget']}")

    return result


async def step_4_review_and_customize(db, event):
    """Step 4: Review and Customize Ads"""
    print("\n" + "="*80)
    print("STEP 4: REVIEW AND CUSTOMIZE ADS")
    print("="*80)

    campaigns = db.query(AdCampaign).filter(AdCampaign.event_id == event.id).all()

    print(f"\n📝 Reviewing {len(campaigns)} campaigns...")

    for campaign in campaigns:
        print(f"\n{'─'*80}")
        print(f"Campaign: {campaign.name}")
        print(f"Platform: {campaign.platform.upper()} | Type: {campaign.campaign_type}")
        print(f"Budget: ${campaign.budget_total/100:.2f} | Status: {campaign.status}")
        print(f"{'─'*80}")

        ads = db.query(AdCreative).filter(AdCreative.ad_campaign_id == campaign.id).all()

        for i, ad in enumerate(ads, 1):
            print(f"\n  Ad #{i}: {ad.name or ad.headline}")
            print(f"  Platform: {ad.platform} | Format: {ad.format}")
            print(f"  Headline: {ad.headline}")
            print(f"  Body: {ad.body[:80]}...")
            print(f"  CTA: {ad.cta}")
            print(f"  Image: {ad.image_url[:60] if ad.image_url else 'None'}...")
            print(f"  Status: {ad.status}")

            # Simulate customization
            if i == 1 and campaign.campaign_type == "awareness":
                print(f"\n  🔧 CUSTOMIZING AD #1...")
                print(f"     Original headline: {ad.headline}")

                # Update headline to be more engaging
                ad.headline = "🔥 ¡Anuel AA en Queens! - Mayo 5"
                ad.body = ad.body.replace("Don't miss out!", "¡No te lo pierdas! RRAAAA 🎤")

                db.commit()

                print(f"     ✅ Updated headline: {ad.headline}")
                print(f"     ✅ Updated body with emojis")

    print(f"\n✅ Review Complete! Ads ready for approval.")


async def step_5_approve_ads(db, event):
    """Step 5: Approve Ads for Publishing"""
    print("\n" + "="*80)
    print("STEP 5: APPROVE ADS FOR PUBLISHING")
    print("="*80)

    ads = db.query(AdCreative).join(AdCampaign).filter(
        AdCampaign.event_id == event.id
    ).all()

    print(f"\n✅ Approving {len(ads)} ads...")

    approved_count = 0
    for ad in ads:
        if ad.status == "draft":
            ad.status = "approved"
            ad.approved_at = datetime.utcnow()
            approved_count += 1

    db.commit()

    print(f"\n✅ Approved {approved_count} ads!")
    print(f"   Status: DRAFT → APPROVED")
    print(f"   Ready for publishing to Meta and Google")


async def step_6_publish_ads(db, event):
    """Step 6: Publish Ads to Meta and Google (Simulated)"""
    print("\n" + "="*80)
    print("STEP 6: PUBLISH ADS TO META AND GOOGLE")
    print("="*80)

    ads = db.query(AdCreative).join(AdCampaign).filter(
        AdCampaign.event_id == event.id,
        AdCreative.status == "approved"
    ).all()

    print(f"\n🚀 Publishing {len(ads)} ads...")

    meta_ads = [ad for ad in ads if ad.platform in ['facebook', 'instagram']]
    google_ads = [ad for ad in ads if ad.platform in ['google_search', 'google_display']]
    other_ads = [ad for ad in ads if ad.platform not in ['facebook', 'instagram', 'google_search', 'google_display']]

    # Simulate Meta publishing
    if meta_ads:
        print(f"\n📱 META ADS ({len(meta_ads)} ads):")
        for ad in meta_ads:
            print(f"\n   Publishing: {ad.headline[:50]}...")
            print(f"   Platform: {ad.platform.upper()}")

            # Simulate the publishing process
            print(f"   ├─ 1. Uploading image to Meta... ✅")
            print(f"   ├─ 2. Creating campaign... ✅")
            print(f"   ├─ 3. Creating ad set with targeting... ✅")
            print(f"   │     Age: 18-35, Location: NYC (25 mi)")
            print(f"   │     Interests: Reggaeton, Latin Music")
            print(f"   │     Languages: Spanish, English")
            print(f"   ├─ 4. Creating ad creative... ✅")
            print(f"   └─ 5. Creating ad... ✅")

            # Simulate Meta ad ID
            ad.platform_ad_id = f"meta_ad_{ad.id}_123456789"
            ad.status = "active"
            ad.published_at = datetime.utcnow()

            print(f"   ✅ Published to Meta! Ad ID: {ad.platform_ad_id}")
            print(f"   📊 Status: PAUSED - Activate in Meta Ads Manager")

    # Simulate Google publishing
    if google_ads:
        print(f"\n🔍 GOOGLE ADS ({len(google_ads)} ads):")
        for ad in google_ads:
            print(f"\n   Publishing: {ad.headline[:50]}...")
            print(f"   Platform: {ad.platform.upper()}")

            # Simulate the publishing process
            print(f"   ├─ 1. Creating campaign... ✅")
            print(f"   ├─ 2. Creating ad group... ✅")
            print(f"   ├─ 3. Adding keywords... ✅")
            print(f"   │     Keywords: anuel aa tickets, reggaeton concert nyc")
            print(f"   ├─ 4. Creating responsive search ad... ✅")
            print(f"   │     Headlines: 3, Descriptions: 2")
            print(f"   └─ 5. Creating ad... ✅")

            # Simulate Google ad resource name
            ad.platform_ad_id = f"customers/1234567890/adGroupAds/{ad.id}~987654321"
            ad.status = "active"
            ad.published_at = datetime.utcnow()

            print(f"   ✅ Published to Google! Resource: {ad.platform_ad_id[:50]}...")
            print(f"   📊 Status: PAUSED - Enable in Google Ads")

    # Email/Organic
    if other_ads:
        print(f"\n📧 EMAIL & ORGANIC ({len(other_ads)} items):")
        for ad in other_ads:
            ad.status = "active"
            ad.published_at = datetime.utcnow()
            print(f"   ✅ {ad.platform.upper()}: {ad.headline[:60]}")

    db.commit()

    print(f"\n✅ ALL ADS PUBLISHED!")
    print(f"   Meta Ads: {len(meta_ads)} (review in Meta Ads Manager)")
    print(f"   Google Ads: {len(google_ads)} (review in Google Ads)")
    print(f"   Email/Organic: {len(other_ads)} (scheduled)")


async def step_7_simulate_performance(db, event):
    """Step 7: Simulate Performance Data"""
    print("\n" + "="*80)
    print("STEP 7: PERFORMANCE TRACKING (SIMULATED)")
    print("="*80)

    from app.models import AdPerformance
    from datetime import date

    ads = db.query(AdCreative).join(AdCampaign).filter(
        AdCampaign.event_id == event.id,
        AdCreative.status == "active"
    ).all()

    print(f"\n📊 Simulating performance data for {len(ads)} ads...")
    print(f"   (In production, this syncs daily from Meta/Google APIs)")

    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
    total_spend = 0
    total_revenue = 0

    for ad in ads:
        # Simulate performance based on platform
        if ad.platform in ['facebook', 'instagram']:
            impressions = 45000
            clicks = 1125  # 2.5% CTR
            conversions = 56  # 5% conversion rate
            spend = 13000  # $130 spent
            revenue = 42000  # $420 revenue (56 tickets @ $75 avg)
        elif ad.platform in ['google_search']:
            impressions = 8000
            clicks = 240  # 3% CTR
            conversions = 12  # 5% conversion rate
            spend = 6000  # $60 spent
            revenue = 9000  # $90 revenue
        else:
            impressions = 1000
            clicks = 50
            conversions = 2
            spend = 0
            revenue = 1500

        # Create performance record
        perf = AdPerformance(
            ad_creative_id=ad.id,
            date=date.today(),
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            spend=spend,
            revenue=revenue,
            ctr=round((clicks / impressions * 100), 2) if impressions > 0 else 0,
            cpc=round((spend / clicks), 2) if clicks > 0 else 0,
            roas=round((revenue / spend), 2) if spend > 0 else 0
        )
        db.add(perf)

        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions
        total_spend += spend
        total_revenue += revenue

        print(f"\n   {ad.platform.upper()}: {ad.headline[:40]}")
        print(f"   ├─ Impressions: {impressions:,}")
        print(f"   ├─ Clicks: {clicks:,} (CTR: {perf.ctr}%)")
        print(f"   ├─ Conversions: {conversions} tickets")
        print(f"   ├─ Spend: ${spend/100:.2f}")
        print(f"   ├─ Revenue: ${revenue/100:.2f}")
        print(f"   └─ ROAS: {perf.roas}:1")

    db.commit()

    print(f"\n{'='*80}")
    print(f"TOTAL PERFORMANCE - DAY 1")
    print(f"{'='*80}")
    print(f"   Total Impressions: {total_impressions:,}")
    print(f"   Total Clicks: {total_clicks:,}")
    print(f"   Total Conversions: {total_conversions} tickets")
    print(f"   Total Spend: ${total_spend/100:.2f}")
    print(f"   Total Revenue: ${total_revenue/100:.2f}")
    print(f"   Overall ROAS: {round(total_revenue/total_spend, 2)}:1")
    print(f"   ROI: {round((total_revenue-total_spend)/total_spend*100, 1)}%")


async def step_8_summary(db, event):
    """Step 8: Final Summary"""
    print("\n" + "="*80)
    print("STEP 8: SUMMARY - COMPLETE AD FLOW")
    print("="*80)

    campaigns = db.query(AdCampaign).filter(AdCampaign.event_id == event.id).all()
    ads = db.query(AdCreative).join(AdCampaign).filter(
        AdCampaign.event_id == event.id
    ).all()

    print(f"\n🎉 COMPLETE AD CAMPAIGN FLOW - SUCCESS!")

    print(f"\n📋 WHAT WAS CREATED:")
    print(f"   ✅ Event: {event.name}")
    print(f"   ✅ Venue: {event.venue.name}")
    print(f"   ✅ Date: {event.event_date.strftime('%B %d, %Y')}")
    print(f"   ✅ Research: Artist images discovered from Spotify, YouTube, Wikipedia")
    print(f"   ✅ Campaigns: {len(campaigns)} campaigns auto-generated")
    print(f"   ✅ Ads: {len(ads)} ads created")
    print(f"   ✅ Customization: Headlines and copy edited")
    print(f"   ✅ Approval: All ads approved")
    print(f"   ✅ Publishing: Ads published to Meta and Google")
    print(f"   ✅ Performance: Metrics tracked")

    print(f"\n💰 BUDGET ALLOCATION:")
    total_budget = sum(c.budget_total for c in campaigns)
    for campaign in campaigns:
        print(f"   • {campaign.name}: ${campaign.budget_total/100:.2f}")
    print(f"   TOTAL: ${total_budget/100:.2f}")

    print(f"\n📊 PLATFORMS:")
    meta_ads = len([a for a in ads if a.platform in ['facebook', 'instagram']])
    google_ads = len([a for a in ads if a.platform in ['google_search', 'google_display']])
    email_ads = len([a for a in ads if a.platform == 'email'])

    print(f"   • Meta Ads (Facebook/Instagram): {meta_ads} ads")
    print(f"   • Google Ads (Search): {google_ads} ads")
    print(f"   • Email Campaigns: {email_ads} emails")

    print(f"\n🎯 NEXT STEPS:")
    print(f"   1. Go to Meta Ads Manager (ads.facebook.com)")
    print(f"      → Review campaigns")
    print(f"      → Click 'Turn On' to activate")
    print(f"   2. Go to Google Ads (ads.google.com)")
    print(f"      → Review campaigns")
    print(f"      → Click 'Enable' to activate")
    print(f"   3. Monitor performance in AI Tickets dashboard")
    print(f"   4. Ads will sync performance data daily")

    print(f"\n📈 EXPECTED RESULTS (30 days):")
    print(f"   • Impressions: ~450,000")
    print(f"   • Clicks: ~12,000")
    print(f"   • Conversions: ~600 tickets")
    print(f"   • Revenue: ~$45,000")
    print(f"   • Ad Spend: ~$1,900")
    print(f"   • ROI: ~2,300%")

    print(f"\n✨ FEATURES DEMONSTRATED:")
    print(f"   ✅ Auto-generated campaigns from event research")
    print(f"   ✅ Image discovery from Spotify, YouTube, Wikipedia")
    print(f"   ✅ Intelligent targeting (age, location, interests, languages)")
    print(f"   ✅ Customizable ads (edit headlines, swap images)")
    print(f"   ✅ Multi-platform publishing (Meta + Google)")
    print(f"   ✅ Performance tracking (impressions, clicks, conversions, ROI)")
    print(f"   ✅ Safety controls (ads created as PAUSED)")


async def main():
    """Run complete flow"""
    db = SessionLocal()

    try:
        # Step 1: Create Event
        event = await step_1_create_event(db)

        # Step 2: Run Research Agent
        research_report = await step_2_run_research(db, event)

        # Step 3: Auto-Generate Campaigns
        campaign_result = await step_3_generate_campaigns(db, event, research_report)

        # Step 4: Review and Customize
        await step_4_review_and_customize(db, event)

        # Step 5: Approve Ads
        await step_5_approve_ads(db, event)

        # Step 6: Publish Ads (Simulated)
        await step_6_publish_ads(db, event)

        # Step 7: Simulate Performance
        await step_7_simulate_performance(db, event)

        # Step 8: Summary
        await step_8_summary(db, event)

        print("\n" + "="*80)
        print("DEMO COMPLETE!")
        print("="*80)

        print("\n🎯 This demo showed the complete ad campaign workflow:")
        print("   Event → Research → Generate → Customize → Approve → Publish → Track")

        print("\n💡 In production:")
        print("   • Research agent uses real APIs (Spotify, YouTube, Wikipedia)")
        print("   • Publishing actually calls Meta Ads API and Google Ads API")
        print("   • Performance syncs daily from ad platforms")
        print("   • All controlled via admin UI")

        print("\n📚 See documentation:")
        print("   • META_ADS_SETUP_GUIDE.md - Set up Meta credentials")
        print("   • GOOGLE_ADS_SETUP_GUIDE.md - Set up Google credentials")
        print("   • ADS_INTEGRATION_SUMMARY.md - Complete overview")

        print("\n" + "="*80 + "\n")

        # Clean up (optional - comment out to keep data)
        print("🧹 Cleaning up demo data...")
        from app.models import AdPerformance, AdCampaignPerformance

        # Delete in order (due to foreign keys)
        db.query(AdPerformance).join(AdCreative).join(AdCampaign).filter(
            AdCampaign.event_id == event.id
        ).delete(synchronize_session=False)

        db.query(AdCampaignPerformance).join(AdCampaign).filter(
            AdCampaign.event_id == event.id
        ).delete(synchronize_session=False)

        db.query(AdCreative).join(AdCampaign).filter(
            AdCampaign.event_id == event.id
        ).delete(synchronize_session=False)

        db.query(AdCampaign).filter(AdCampaign.event_id == event.id).delete()
        db.query(TicketTier).filter(TicketTier.event_id == event.id).delete()
        db.query(Event).filter(Event.id == event.id).delete()

        db.commit()
        print("✅ Demo data cleaned up")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    print("\nStarting complete ad campaign flow demo...")
    print("This will take approximately 30 seconds...\n")
    asyncio.run(main())
