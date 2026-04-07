#!/usr/bin/env python
"""
Demo Test: Bad Bunny Concert at Prudential Center
Shows all the intelligent features and data returned by the AI Tickets platform
"""

import asyncio
import json
from datetime import datetime, timedelta
from pprint import pprint

# Simulating the complete flow for a Bad Bunny concert

async def create_bad_bunny_event_demo():
    """
    Simulates creating a Bad Bunny concert and shows all the AI responses
    """

    print("=" * 80)
    print("🎤 BAD BUNNY CONCERT - PRUDENTIAL CENTER")
    print("AI TICKETS PLATFORM DEMO")
    print("=" * 80)

    # 1. EVENT CREATION
    event_data = {
        "name": "Bad Bunny - Most Wanted Tour",
        "description": "Bad Bunny brings his Most Wanted Tour to Newark! Experience the biggest reggaeton show of 2024.",
        "venue": {
            "name": "Prudential Center",
            "address": "25 Lafayette Street, Newark, NJ 07102",
            "phone": "(973) 757-6000",
            "capacity": 19500
        },
        "date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
        "time": "20:00",
        "doors_open": "19:00",
        "categories": ["Concert", "Latin", "Reggaeton"]
    }

    print("\n📅 EVENT DETAILS:")
    print(f"  Name: {event_data['name']}")
    print(f"  Venue: {event_data['venue']['name']}")
    print(f"  Date: {event_data['date']}")
    print(f"  Capacity: {event_data['venue']['capacity']:,} seats")

    # 2. TICKET TIERS
    ticket_tiers = [
        {"name": "VIP Floor", "price_cents": 45000, "quantity": 500},  # $450
        {"name": "Premium Lower Bowl", "price_cents": 25000, "quantity": 3000},  # $250
        {"name": "Lower Bowl", "price_cents": 15000, "quantity": 6000},  # $150
        {"name": "Upper Bowl", "price_cents": 7500, "quantity": 10000}  # $75
    ]

    print("\n🎫 TICKET TIERS:")
    for tier in ticket_tiers:
        print(f"  {tier['name']}: ${tier['price_cents']/100:.0f} x {tier['quantity']:,} seats")

    total_revenue_potential = sum(t['price_cents'] * t['quantity'] for t in ticket_tiers) / 100
    print(f"  Total Revenue Potential: ${total_revenue_potential:,.0f}")

    # 3. AI RESEARCH AGENT RESULTS
    print("\n🔍 AI RESEARCH AGENT DISCOVERIES:")

    artist_research = {
        "artist_name": "Bad Bunny (Benito Antonio Martínez Ocasio)",
        "genre": "Reggaeton, Latin Trap, Alternative Reggaeton",
        "bio": "Puerto Rican superstar who revolutionized Latin music. Most streamed artist globally on Spotify 2020-2022. Known for breaking language barriers and stadium tours.",
        "achievements": [
            "3x Grammy Award winner",
            "10x Latin Grammy winner",
            "First Spanish-language act to headline Coachella",
            "Spotify's most-streamed artist globally (3 years)",
            "#1 Billboard 200 album with 'Un Verano Sin Ti'"
        ],
        "social_media": {
            "instagram": "@badbunnypr (45.6M followers)",
            "spotify": "79M monthly listeners",
            "youtube": "46.3M subscribers",
            "tiktok": "@badbunny (6.2M followers)"
        },
        "similar_artists": ["J Balvin", "Ozuna", "Daddy Yankee", "Rauw Alejandro", "Anuel AA"],
        "fan_demographics": {
            "age_range": "18-35",
            "gender_split": "60% female, 40% male",
            "interests": ["Latin Music", "Reggaeton", "Fashion", "Puerto Rico", "Latino Culture"],
            "languages": ["Spanish (primary)", "English (secondary)"]
        },
        "top_songs": [
            "Me Porto Bonito",
            "Tití Me Preguntó",
            "Moscow Mule",
            "Ojitos Lindos",
            "Dakiti"
        ],
        "venue_history": "Sold out Madison Square Garden 3 nights in a row",
        "ticket_demand": "EXTREMELY HIGH - Previous tours sold out in minutes"
    }

    print(f"  Artist: {artist_research['artist_name']}")
    print(f"  Genre: {artist_research['genre']}")
    print(f"  Spotify: {artist_research['social_media']['spotify']}")
    print(f"  Instagram: {artist_research['social_media']['instagram']}")
    print(f"  Top Achievement: {artist_research['achievements'][0]}")
    print(f"  Demand Level: {artist_research['ticket_demand']}")

    # 4. GEO-TARGETING INTELLIGENCE
    print("\n📍 GEO-TARGETING INTELLIGENCE:")

    geo_analysis = {
        "venue_coordinates": (40.7336, -74.1710),  # Prudential Center
        "target_radius": 25,  # miles
        "cities_covered": [
            "Newark, NJ (0 miles)",
            "New York City, NY (11 miles)",
            "Jersey City, NJ (8 miles)",
            "Elizabeth, NJ (6 miles)",
            "Paterson, NJ (17 miles)",
            "Staten Island, NY (15 miles)",
            "Bronx, NY (19 miles)",
            "Brooklyn, NY (16 miles)"
        ],
        "population_reach": "8.3 million people",
        "latino_population": "2.4 million (29%)",
        "competitor_venues": [
            "Madison Square Garden (11 miles)",
            "Barclays Center (16 miles)",
            "MetLife Stadium (8 miles)"
        ]
    }

    print(f"  Target Radius: {geo_analysis['target_radius']} miles from venue")
    print(f"  Population Reach: {geo_analysis['population_reach']}")
    print(f"  Latino Population: {geo_analysis['latino_population']}")
    print(f"  Major Cities: {', '.join(geo_analysis['cities_covered'][:3])}")

    # 5. SMART BUDGET CALCULATION
    print("\n💰 AI BUDGET STRATEGIST:")

    budget_calc = {
        "base_budget": 500,  # $5/day
        "adjustments": {
            "premium_event": 1.5,  # 150% for high ticket prices
            "large_venue": 1.3,   # 130% for 19,500 capacity
            "moderate_urgency": 1.0,  # 45 days out
            "high_demand_artist": 1.5  # 150% for Bad Bunny popularity
        },
        "final_daily_budget_cents": 14625,  # $146.25/day
        "campaign_duration": 45,  # days
        "total_budget": 658125,  # $6,581.25 total
        "expected_roas": 4.2,
        "reasoning": "Bad Bunny commands premium pricing. High Latino population density in target area. Previous sellout history suggests aggressive marketing warranted."
    }

    final_multiplier = 1.5 * 1.3 * 1.0 * 1.5
    print(f"  Base Budget: ${budget_calc['base_budget']/100}/day")
    print(f"  Multiplier: {final_multiplier:.2f}x (premium + large + demand)")
    print(f"  Final Daily: ${budget_calc['final_daily_budget_cents']/100:.2f}/day")
    print(f"  Total Campaign: ${budget_calc['total_budget']/100:,.2f} over {budget_calc['campaign_duration']} days")
    print(f"  Expected ROAS: {budget_calc['expected_roas']}x")

    # 6. AD CAMPAIGN GENERATION
    print("\n📢 GENERATED AD CAMPAIGNS (9 variations):")

    campaigns = [
        {
            "name": "Awareness - Bad Bunny Newark",
            "platform": "Meta",
            "objective": "REACH",
            "budget_cents": 4388,  # 30% of daily
            "headline": "Bad Bunny Live at Prudential Center! 🔥",
            "body": "El Conejo Malo is coming to Newark! Experience the Most Wanted Tour. Don't miss the reggaeton event of the year.",
            "image": "spotify_artist_image.jpg",
            "cta": "LEARN_MORE",
            "targeting": {
                "ages": "18-35",
                "interests": ["Bad Bunny", "Reggaeton", "Latin Music"],
                "languages": ["Spanish", "English"],
                "radius": "25 miles from venue"
            }
        },
        {
            "name": "Spanish Language - Latino Audience",
            "platform": "Meta",
            "objective": "TRAFFIC",
            "budget_cents": 5850,  # 40% of daily
            "headline": "¡Bad Bunny en Nueva Jersey! 🇵🇷",
            "body": "No te pierdas al Conejo Malo en vivo! Most Wanted Tour llega al Prudential Center. Boletos ya disponibles. PERREO HASTA EL AMANECER!",
            "cta": "COMPRAR_BOLETOS",
            "targeting": {
                "languages": ["Spanish"],
                "interests": ["Puerto Rico", "Reggaeton", "Latino Culture"],
                "custom_audience": "Latino affinity"
            }
        },
        {
            "name": "VIP Experience Campaign",
            "platform": "Meta",
            "objective": "CONVERSIONS",
            "budget_cents": 2925,  # 20% of daily
            "headline": "VIP Floor Seats - Meet & Greet Available",
            "body": "Get exclusive VIP access to Bad Bunny. Limited floor seats with premium perks. This is your chance to be closest to the action!",
            "cta": "GET_TICKETS",
            "targeting": {
                "income": "Top 25%",
                "behaviors": ["Premium brand affinity", "Frequent travelers"]
            }
        },
        {
            "name": "Google Search - Bad Bunny Tickets",
            "platform": "Google",
            "budget_cents": 2925,  # 20% of daily
            "keywords": [
                "bad bunny newark tickets",
                "bad bunny prudential center",
                "bad bunny new jersey 2024",
                "bad bunny most wanted tour",
                "reggaeton concerts newark"
            ],
            "headlines": [
                "Bad Bunny Newark | Official Tickets",
                "Prudential Center | May 15",
                "Most Wanted Tour | Get Tickets"
            ]
        },
        {
            "name": "YouTube Pre-Roll - Concert Footage",
            "platform": "YouTube",
            "budget_cents": 1462,  # 10% of daily
            "video": "bad_bunny_concert_highlights.mp4",
            "targeting": {
                "interests": ["Latin Music Videos", "Concert Footage"],
                "channels": ["Bad Bunny Official", "Latin Music Channels"]
            }
        }
    ]

    for i, campaign in enumerate(campaigns[:3], 1):  # Show first 3
        print(f"\n  Campaign {i}: {campaign['name']}")
        print(f"    Budget: ${campaign['budget_cents']/100:.2f}/day")
        print(f"    Headline: {campaign['headline']}")
        print(f"    Platform: {campaign['platform']}")

    print("\n  ... and 6 more campaigns")

    # 7. CUSTOMER SEGMENTATION STRATEGY
    print("\n👥 CUSTOMER SEGMENTATION STRATEGY:")

    segments = {
        "vip_super_fans": {
            "description": "Die-hard Bad Bunny fans willing to pay premium",
            "size": "5% of audience",
            "target_tier": "VIP Floor ($450)",
            "messaging": "Exclusive access, meet & greet possibility",
            "expected_conversion": "8%"
        },
        "regular_fans": {
            "description": "Fans who've streamed his music regularly",
            "size": "25% of audience",
            "target_tier": "Lower Bowl ($150-250)",
            "messaging": "Don't miss your favorite songs live",
            "expected_conversion": "5%"
        },
        "latino_community": {
            "description": "Spanish-speaking community celebration",
            "size": "35% of audience",
            "target_tier": "All tiers",
            "messaging": "Cultural event, community gathering",
            "expected_conversion": "4%"
        },
        "casual_listeners": {
            "description": "Know hit songs, curious about live show",
            "size": "35% of audience",
            "target_tier": "Upper Bowl ($75)",
            "messaging": "Experience the phenomenon",
            "expected_conversion": "2%"
        }
    }

    for segment_name, segment_data in segments.items():
        print(f"  {segment_name}: {segment_data['size']} - Target: {segment_data['target_tier']}")

    # 8. PREDICTED OUTCOMES
    print("\n📊 AI PREDICTIONS:")

    predictions = {
        "sellout_probability": 94,
        "days_to_sellout": 12,
        "expected_gross_revenue": 2150000,  # $2.15M
        "expected_attendance": 18500,
        "vip_sellout_hours": 3,
        "social_media_reach": 2500000,
        "walk_up_sales_percent": 2,
        "refund_rate": 0.5,
        "weather_risk": "Low (indoor venue)",
        "competing_events": "None identified in date range"
    }

    print(f"  Sellout Probability: {predictions['sellout_probability']}%")
    print(f"  Expected Sellout: {predictions['days_to_sellout']} days")
    print(f"  Revenue Forecast: ${predictions['expected_gross_revenue']:,.0f}")
    print(f"  VIP Sellout Time: {predictions['vip_sellout_hours']} hours")

    # 9. AUTOMATION TRIGGERS SET UP
    print("\n⚡ AUTOMATED TRIGGERS CONFIGURED:")

    triggers = [
        "✓ When VIP < 50 tickets → Send 'Almost Gone' campaign",
        "✓ When 90% sold → Trigger 'Final Tickets' urgency",
        "✓ When sold out → Pause all ads instantly",
        "✓ If sales stall → Launch 24-hour flash sale",
        "✓ 1 week before → Send reminder to all buyers",
        "✓ Day of event → Send logistics (parking, doors)",
        "✓ If rain forecast → Send 'Event is indoors' reassurance"
    ]

    for trigger in triggers:
        print(f"  {trigger}")

    # 10. REAL-TIME MONITORING METRICS
    print("\n📈 REAL-TIME MONITORING DASHBOARD:")

    metrics = {
        "tickets_available": 19500,
        "current_sales_velocity": 0,
        "ads_running": 9,
        "current_spend_per_hour": 6.09,  # $146.25/24
        "impressions_per_hour": 2847,
        "clicks_per_hour": 142,
        "conversions_per_hour": 8,
        "current_roas": 0,  # Will populate once sales begin
        "trending_on_social": False,
        "competitor_alerts": []
    }

    print(f"  Tickets Available: {metrics['tickets_available']:,}")
    print(f"  Active Campaigns: {metrics['ads_running']}")
    print(f"  Hourly Ad Spend: ${metrics['current_spend_per_hour']:.2f}")
    print(f"  Hourly Impressions: {metrics['impressions_per_hour']:,}")

    # 11. NATURAL LANGUAGE UNDERSTANDING
    print("\n🗣️ VOICE AGENT CAPABILITIES:")

    voice_commands = [
        "How many VIP tickets do we have left for Bad Bunny?",
        "Send a promo code to everyone who bought upper bowl",
        "Increase the ad budget by 50% for Bad Bunny",
        "Show me the sales velocity for the last hour",
        "Create a flash sale for 20% off upper bowl only",
        "Check in the Rodriguez family of 5",
        "Send a Spanish language reminder tomorrow at noon"
    ]

    print("  Sample commands the AI understands:")
    for cmd in voice_commands[:3]:
        print(f"    • '{cmd}'")

    # SUMMARY
    print("\n" + "=" * 80)
    print("💡 INTELLIGENCE SUMMARY")
    print("=" * 80)

    print(f"""
  The AI has automatically:
  • Researched Bad Bunny's entire background and fanbase
  • Identified 2.4M Latino population in 25-mile radius
  • Calculated optimal budget of $146.25/day
  • Generated 9 targeted ad campaigns in English & Spanish
  • Set up geo-fencing around Prudential Center
  • Created VIP, regular, and budget pricing strategies
  • Configured real-time monitoring and triggers
  • Predicted 94% sellout probability in 12 days
  • Prepared for $2.15M in revenue

  All of this happens AUTOMATICALLY when you create the event!
    """)

    return {
        "event": event_data,
        "research": artist_research,
        "geo": geo_analysis,
        "budget": budget_calc,
        "campaigns": campaigns,
        "predictions": predictions
    }

if __name__ == "__main__":
    print("\n🚀 Starting Bad Bunny Concert Demo...\n")
    result = asyncio.run(create_bad_bunny_event_demo())
    print("\n✅ Demo Complete!")
    print("\nFull data structure returned to voice agent for processing.")