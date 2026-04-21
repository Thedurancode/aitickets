#!/usr/bin/env python3
"""
Check All Event Publishing Platforms
"""

import sys
import os
from pathlib import Path
import requests

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.config import get_settings
from app.services.event_publisher import get_available_platforms


def check_platform_status():
    """Check status of all event publishing platforms"""

    settings = get_settings()

    print("\n" + "="*70)
    print("🚀 ALL EVENT PUBLISHING PLATFORMS - AI TICKETS")
    print("="*70)

    platforms = get_available_platforms()

    # Group platforms by status
    configured = []
    not_configured = []

    for platform in platforms:
        if platform['configured']:
            configured.append(platform)
        else:
            not_configured.append(platform)

    # Display configured platforms
    print("\n✅ READY TO USE (Configured):")
    print("-" * 50)
    for p in configured:
        print(f"\n📌 {p['name']} ({p['id']})")
        if p['id'] == 'eventbrite':
            print("   • Publish events with tickets")
            print("   • Multiple pricing tiers")
            print("   • Automatic venue creation")
            print("   • Track sales and attendees")
        elif p['id'] == 'social_media':
            print("   • Post to Facebook, Instagram, Twitter, LinkedIn")
            print("   • Schedule posts in advance")
            print("   • Include event images")
            print("   • Cross-post to multiple channels")
        elif p['id'] == 'meta_ads':
            print("   • Create Facebook/Instagram ad campaigns")
            print("   • Geo-targeted advertising")
            print("   • Budget management")
            print("   • Performance tracking")
        elif p['id'] == 'webhooks':
            print("   • Notify external systems")
            print("   • Custom integrations")
            print("   • Real-time event updates")
            print("   • API callbacks")
        elif p['id'] == 'calendar':
            print("   • Google Calendar links")
            print("   • iCal downloads")
            print("   • Outlook integration")
            print("   • Add to calendar buttons")

    # Display not configured platforms
    print("\n⚠️  AVAILABLE BUT NEEDS SETUP:")
    print("-" * 50)
    for p in not_configured:
        print(f"\n📌 {p['name']} ({p['id']})")
        print(f"   Required: {', '.join(p['requires'])}")
        if p['docs_url']:
            print(f"   Setup Guide: {p['docs_url']}")

    # Additional platforms that could be added
    print("\n🔮 ADDITIONAL PLATFORMS (Can Be Added):")
    print("-" * 50)
    additional = [
        {
            "name": "Ticketmaster",
            "description": "World's largest ticket marketplace",
            "features": ["Major venues", "Global reach", "Professional events"]
        },
        {
            "name": "StubHub",
            "description": "Secondary ticket marketplace",
            "features": ["Resale market", "Price optimization", "Fan-to-fan sales"]
        },
        {
            "name": "Meetup",
            "description": "Community event platform",
            "features": ["Local groups", "Recurring events", "Community building"]
        },
        {
            "name": "Facebook Events",
            "description": "Social event discovery",
            "features": ["Social sharing", "RSVP tracking", "Event recommendations"]
        },
        {
            "name": "Dice",
            "description": "Music discovery & ticketing",
            "features": ["Music events", "Artist following", "Personalized recommendations"]
        },
        {
            "name": "RA (Resident Advisor)",
            "description": "Electronic music events",
            "features": ["Club events", "DJ bookings", "Music community"]
        },
        {
            "name": "Universe",
            "description": "DIY event ticketing",
            "features": ["Custom branding", "No platform fees", "Direct payouts"]
        },
        {
            "name": "Tixr",
            "description": "Fan-first ticketing",
            "features": ["Fan data ownership", "Marketing tools", "Analytics"]
        },
        {
            "name": "See Tickets",
            "description": "International ticketing",
            "features": ["Multi-currency", "Global events", "Festival focus"]
        },
        {
            "name": "AXS",
            "description": "Digital ticketing platform",
            "features": ["Mobile tickets", "ID verification", "Transfer protection"]
        }
    ]

    for platform in additional:
        print(f"\n• {platform['name']}")
        print(f"  {platform['description']}")
        print(f"  Features: {', '.join(platform['features'])}")

    # Multi-platform publishing example
    print("\n" + "="*70)
    print("💫 MULTI-PLATFORM PUBLISHING")
    print("="*70)
    print("\nPublish to ALL platforms at once with a single API call:")
    print("\nPOST /api/event-publisher/events/{event_id}/publish")
    print("Body: {\"platforms\": null}  # null = all configured platforms")
    print("\nOr select specific platforms:")
    print('Body: {"platforms": ["eventbrite", "social_media", "meta_ads"]}')

    # Current configuration summary
    print("\n" + "="*70)
    print("📊 YOUR CURRENT SETUP")
    print("="*70)
    print(f"\n✅ Platforms Ready: {len(configured)}")
    for p in configured:
        print(f"   • {p['name']}")

    print(f"\n⚠️  Platforms Needing Setup: {len(not_configured)}")
    for p in not_configured:
        print(f"   • {p['name']}")

    # Quick wins
    print("\n" + "="*70)
    print("🎯 QUICK WINS - Easy to Add")
    print("="*70)
    print("\n1. Bandsintown - Music/Concert Events")
    print("   • Just needs: BANDSINTOWN_APP_ID")
    print("   • Get it at: https://artists.bandsintown.com/support/api")
    print("\n2. Facebook Events (via Meta API)")
    print("   • Uses existing Meta credentials")
    print("   • Can reuse your Meta Ads setup")
    print("\n3. Google Calendar")
    print("   • Already working! (calendar export)")
    print("   • No additional setup needed")

    print("\n" + "="*70)
    print("✨ Multi-platform publishing amplifies your reach!")
    print("="*70 + "\n")


if __name__ == "__main__":
    check_platform_status()