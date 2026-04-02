#!/usr/bin/env python3
"""
Venue-Aware Demographic Intelligence Demo

Shows how the system automatically:
1. Analyzes venue location demographics
2. Creates targeted audience personas
3. Composes custom ads for each persona
4. Optimizes advertising radius
5. Allocates budget intelligently
"""
import json

print("=" * 80)
print("🎯 VENUE-AWARE DEMOGRAPHIC INTELLIGENCE & AD COMPOSER")
print("=" * 80)

# ==================== 1. VENUE DEMOGRAPHIC ANALYSIS ====================

print("\n\n📍 1. ANALYZE VENUE LOCATION & DEMOGRAPHICS")
print("─" * 80)

print("🎤 Input: Analyze Convention Center, San Francisco")
print("\n🔧 Agent Actions:")
print("   → Geocode venue address → Get lat/long coordinates")
print("   → Query US Census Bureau API → Population, age, income, education")
print("   → Query Google Places API → Nearby POIs, foot traffic")
print("   → Analyze 5/10/25 mile radius demographics")
print("   → Generate audience personas")

print("\n✅ Demographic Analysis:")
demographics = {
    "venue": {
        "name": "Convention Center",
        "city": "San Francisco",
        "state": "CA",
        "coordinates": {"lat": 37.7749, "lng": -122.4194}
    },
    "population": {
        "5_mile_radius": "125,000",
        "10_mile_radius": "450,000",
        "25_mile_radius": "1,200,000"
    },
    "age_distribution": {
        "18-24": "18.5%  ← College students, entry-level",
        "25-34": "32.1%  ← PRIMARY TARGET (tech professionals)",
        "35-44": "21.3%  ← Established professionals",
        "45-54": "14.2%",
        "55-64": "9.1%",
        "65+": "4.8%"
    },
    "income_distribution": {
        "under_35k": "15.2%",
        "35k-50k": "18.3%",
        "50k-75k": "22.1%",
        "75k-100k": "19.4%  ← Middle management",
        "100k-150k": "15.8%  ← Senior professionals",
        "over_150k": "9.2%   ← Executives/founders"
    },
    "education": {
        "high_school": "22.1%",
        "some_college": "28.3%",
        "bachelors": "31.2%  ← Tech workers",
        "graduate_degree": "18.4%  ← Specialists/managers"
    },
    "employment_sectors": {
        "tech_sector": "28.4%  🎯 PRIMARY AUDIENCE",
        "finance": "12.3%",
        "healthcare": "11.2%",
        "education": "8.9%",
        "other": "39.2%"
    },
    "interests": {
        "technology": "34.2%  🚀 High tech interest",
        "music": "28.7%",
        "food_dining": "45.3%",
        "fitness": "31.8%",
        "arts_culture": "27.4%"
    }
}
print(json.dumps(demographics, indent=2))

# ==================== 2. AUDIENCE PERSONAS ====================

print("\n\n👥 2. GENERATED AUDIENCE PERSONAS")
print("─" * 80)

personas = [
    {
        "name": "Tech Professional Alex",
        "percentage": "34.2% of population",
        "profile": {
            "age": "28 years old",
            "job": "Software Engineer at tech startup",
            "income": "$120,000/year",
            "education": "Bachelor's in Computer Science",
            "location": "SOMA, San Francisco"
        },
        "psychographics": {
            "goals": ["Career advancement", "Networking", "Learning new skills"],
            "pain_points": ["Limited networking opportunities", "Keeping up with tech trends"],
            "values": ["Innovation", "Efficiency", "Continuous learning"],
            "daily_routine": [
                "7am: Check TechCrunch, HackerNews",
                "9am-6pm: Work at tech company",
                "7pm: LinkedIn scrolling, tech podcasts",
                "Weekends: Side projects, meetups"
            ]
        },
        "media_consumption": {
            "platforms": "LinkedIn (daily), Reddit (r/programming), Twitter/X",
            "content": "Tech news, tutorials, career advice",
            "peak_hours": "7-9am commute, 6-10pm evenings"
        },
        "buying_behavior": {
            "decision_factors": ["ROI on career", "Networking quality", "Speaker lineup"],
            "price_sensitivity": "Low (will pay for quality)",
            "preferred_channels": "LinkedIn ads, Google search, tech blogs"
        }
    },
    {
        "name": "Student Sam",
        "percentage": "18.5% of population",
        "profile": {
            "age": "22 years old",
            "job": "Computer Science student + part-time intern",
            "income": "$25,000/year",
            "education": "Junior at SF State University",
            "location": "Near university campus"
        },
        "psychographics": {
            "goals": ["Land first tech job", "Build portfolio", "Learn from professionals"],
            "pain_points": ["Limited budget", "Lack of industry connections"],
            "values": ["Learning", "Affordability", "Career launch"],
            "daily_routine": [
                "Classes 9am-3pm",
                "Study/coding 4-7pm",
                "Instagram/TikTok 8-11pm"
            ]
        },
        "media_consumption": {
            "platforms": "Instagram, TikTok, Discord, Reddit",
            "content": "Coding tutorials, memes, student life",
            "peak_hours": "8-11pm evenings, weekends"
        },
        "buying_behavior": {
            "decision_factors": ["Price (huge factor)", "Recruiting opportunities", "Student discount"],
            "price_sensitivity": "Very high",
            "preferred_channels": "Instagram ads, Facebook, university partnerships"
        }
    },
    {
        "name": "Manager Maria",
        "percentage": "15.8% of population",
        "profile": {
            "age": "38 years old",
            "job": "Engineering Manager at Fortune 500",
            "income": "$180,000/year",
            "education": "Master's in Engineering",
            "location": "Financial District"
        },
        "psychographics": {
            "goals": ["Team development", "Executive networking", "Industry insights"],
            "pain_points": ["Time constraints", "Finding quality events"],
            "values": ["Leadership", "Quality over quantity", "Strategic networking"],
            "daily_routine": [
                "6am: Email/news",
                "8am-6pm: Meetings, management",
                "8pm: Family time then professional reading"
            ]
        },
        "media_consumption": {
            "platforms": "LinkedIn, Email newsletters, Business Insider",
            "content": "Leadership content, industry analysis, best practices",
            "peak_hours": "6-8am mornings, 8-10pm evenings"
        },
        "buying_behavior": {
            "decision_factors": ["Speaker quality", "Executive attendance", "Time efficiency"],
            "price_sensitivity": "Low (company pays or tax deductible)",
            "preferred_channels": "Email campaigns, LinkedIn, industry publications"
        }
    }
]

for i, persona in enumerate(personas, 1):
    print(f"\n[Persona {i}] {persona['name']} ({persona['percentage']})")
    print(f"   Profile: {persona['profile']['age']}, {persona['profile']['job']}")
    print(f"   Income: {persona['profile']['income']}")
    print(f"   Goals: {', '.join(persona['psychographics']['goals'][:2])}")
    print(f"   Best channels: {persona['buying_behavior']['preferred_channels']}")

# ==================== 3. AUTO-COMPOSED ADS ====================

print("\n\n📱 3. AUTO-COMPOSED TARGETED ADS")
print("─" * 80)

print("\n🎤 Request: Compose ads for AI Summit 2026 at Convention Center")
print("\n🔧 Agent Process:")
print("   → Identify event category: Technology")
print("   → Match to persona: Tech Professional Alex (34.2%)")
print("   → Analyze demographics: Age 25-34, Income $75k+")
print("   → Select platforms: LinkedIn (primary), Instagram (secondary)")
print("   → Compose personalized ad copy")
print("   → Set targeting parameters")

print("\n✅ Generated Ad Campaigns:")

ad_campaign_1 = {
    "persona": "Tech Professional Alex",
    "platform": "LinkedIn",
    "ad_creative": {
        "headline": "AI Summit 2026 - Advance Your Tech Career",
        "primary_text": (
            "Join 500+ tech professionals at San Francisco's premier AI conference.\n\n"
            "✓ Network with industry leaders from Google, Meta, OpenAI\n"
            "✓ Discover emerging AI technologies before your competitors\n"
            "✓ Accelerate your career with exclusive insights\n\n"
            "Convention Center | June 15, 2026"
        ),
        "call_to_action": "Get Tickets",
        "image_suggestion": "Professional networking scene, diverse tech professionals engaging"
    },
    "targeting": {
        "location": "San Francisco, CA + 25 miles",
        "age": "25-34",
        "job_titles": [
            "Software Engineer",
            "Machine Learning Engineer",
            "Data Scientist",
            "Product Manager",
            "Developer"
        ],
        "interests": [
            "Artificial Intelligence",
            "Machine Learning",
            "Technology",
            "Software Development"
        ],
        "behaviors": "Early technology adopters",
        "company_size": "50-10,000+ employees"
    },
    "budget": {
        "daily": "$75",
        "total_campaign": "$2,100",
        "expected_reach": "85,000 professionals",
        "expected_clicks": "1,700 (2.0% CTR)",
        "expected_conversions": "85 tickets (5% conversion)",
        "cost_per_ticket": "$24.70",
        "revenue_per_ticket": "$99.00",
        "ROI": "4.0x"
    }
}

print(json.dumps(ad_campaign_1, indent=2))

print("\n" + "─" * 80)

ad_campaign_2 = {
    "persona": "Student Sam",
    "platform": "Instagram",
    "ad_creative": {
        "headline": "🚀 Launch Your Tech Career",
        "primary_text": (
            "AI Summit 2026\n"
            "📍 SF Convention Center\n"
            "🗓️ June 15\n\n"
            "🎓 STUDENT SPECIAL: 40% OFF\n\n"
            "✨ Meet hiring companies\n"
            "✨ Learn from industry experts\n"
            "✨ Build your network\n\n"
            "Use code: STUDENT40\n"
            "Limited early bird tickets!"
        ),
        "call_to_action": "Get Student Tickets",
        "image_suggestion": "Young, diverse students learning coding, modern campus vibe"
    },
    "targeting": {
        "location": "San Francisco, CA + 10 miles (university area)",
        "age": "18-24",
        "education": ["In college", "Recent college graduate (1-2 years)"],
        "interests": [
            "Computer Science",
            "Programming",
            "Startups",
            "Career Development"
        ],
        "behaviors": "Students, tech enthusiasts",
        "schools": [
            "Stanford University",
            "UC Berkeley",
            "San Francisco State",
            "City College of SF"
        ]
    },
    "budget": {
        "daily": "$35",
        "total_campaign": "$980",
        "expected_reach": "45,000 students",
        "expected_clicks": "1,350 (3.0% CTR - students very engaged)",
        "expected_conversions": "54 tickets (4% conversion)",
        "cost_per_ticket": "$18.15",
        "revenue_per_ticket": "$59.00 (discounted)",
        "ROI": "3.25x"
    }
}

print(json.dumps(ad_campaign_2, indent=2))

# ==================== 4. OPTIMAL RADIUS ANALYSIS ====================

print("\n\n🎯 4. OPTIMAL ADVERTISING RADIUS OPTIMIZATION")
print("─" * 80)

print("\n🔧 Agent Analysis:")
print("   → Analyze population at 5, 10, 25, 50 mile radius")
print("   → Calculate target demographic concentration")
print("   → Factor in transportation accessibility")
print("   → Consider ad competition/CPM at each radius")
print("   → Select optimal balance of reach vs cost")

radius_comparison = {
    "5_mile_radius": {
        "population": "125,000",
        "target_demographic": "42,750 tech professionals",
        "pros": ["Highest concentration", "Best transportation access"],
        "cons": ["High ad competition", "Higher CPM ($15-20)", "Limited reach"],
        "cost_efficiency": "2.5 / 5"
    },
    "10_mile_radius": {
        "population": "450,000",
        "target_demographic": "153,900 tech professionals",
        "pros": ["Good concentration", "Reasonable CPM", "Includes suburbs"],
        "cons": ["Moderate competition"],
        "cost_efficiency": "3.5 / 5"
    },
    "25_mile_radius": {
        "population": "1,200,000",
        "target_demographic": "410,400 tech professionals",
        "pros": [
            "Excellent reach",
            "Lower CPM ($8-12)",
            "Low competition",
            "Includes Peninsula/East Bay"
        ],
        "cons": ["Some may not travel"],
        "cost_efficiency": "5.0 / 5  ⭐ OPTIMAL"
    },
    "50_mile_radius": {
        "population": "2,500,000",
        "target_demographic": "855,000 tech professionals",
        "pros": ["Maximum reach", "Lowest CPM"],
        "cons": ["Too far for most attendees", "Wasted impressions"],
        "cost_efficiency": "2.0 / 5"
    }
}

print("\n✅ Radius Analysis:")
print(json.dumps(radius_comparison, indent=2))

print("\n\n💡 RECOMMENDATION: 25-Mile Radius")
print("   Reaches 410,400 target demographic")
print("   Lower ad costs ($8-12 CPM vs $15-20)")
print("   Covers SF + Peninsula + East Bay tech hubs")
print("   Expected campaign cost: $2,500-$3,500")

# ==================== 5. COMPLETE MARKETING STRATEGY ====================

print("\n\n🎯 5. COMPLETE VENUE-BASED MARKETING STRATEGY")
print("=" * 80)

strategy = {
    "event": "AI Summit 2026",
    "venue": "Convention Center, San Francisco",
    "target_audience": "Tech professionals in SF Bay Area",
    
    "demographic_insights": [
        "✅ 34.2% tech sector employment (vs 12% national avg)",
        "✅ 32.1% aged 25-34 (prime target)",
        "✅ 50% earn $75k+ (can afford $99 ticket)",
        "✅ 49.6% have Bachelor's+ (educated audience)"
    ],
    
    "audience_segments": [
        {"segment": "Tech Professionals", "percentage": "50%", "budget": "$1,500"},
        {"segment": "Students", "percentage": "25%", "budget": "$750"},
        {"segment": "Managers/Executives", "percentage": "25%", "budget": "$750"}
    ],
    
    "channel_strategy": {
        "LinkedIn": {
            "budget": "40%",
            "targeting": "Job titles + interests + behaviors",
            "expected_ROI": "4.0x"
        },
        "Instagram": {
            "budget": "30%",
            "targeting": "Age + education + interests",
            "expected_ROI": "3.25x"
        },
        "Google_Search": {
            "budget": "20%",
            "targeting": "Keywords + location",
            "expected_ROI": "3.5x"
        },
        "Retargeting": {
            "budget": "10%",
            "targeting": "Website visitors",
            "expected_ROI": "5.0x"
        }
    },
    
    "geography": {
        "primary_radius": "25 miles from venue",
        "includes": ["San Francisco", "Peninsula", "East Bay", "South Bay"],
        "excludes": ["Areas 50+ miles (too far)"]
    },
    
    "messaging_by_persona": {
        "Tech_Professionals": "Career advancement + exclusive insights",
        "Students": "Affordable learning + recruiting opportunities",
        "Managers": "Leadership insights + executive networking"
    },
    
    "expected_results": {
        "total_impressions": "250,000-300,000",
        "total_clicks": "5,000-6,000",
        "ticket_sales": "200-250",
        "revenue": "$19,800-$24,750",
        "marketing_cost": "$3,000",
        "ROI": "6.6x - 8.25x",
        "cost_per_acquisition": "$12-$15"
    }
}

print(json.dumps(strategy, indent=2))

print("\n\n" + "=" * 80)
print("✨ SUMMARY: VENUE-AWARE INTELLIGENCE")
print("=" * 80)

print("""
The AI agent automatically:

1. 📍 Analyzed venue location (Convention Center, SF)
   → Found 1.2M people within 25 miles
   → Identified 34.2% tech sector employment
   → Discovered 32.1% aged 25-34 (prime target)

2. 👥 Generated 3 detailed audience personas
   → Tech Professional Alex (34.2%) - $120k income, LinkedIn user
   → Student Sam (18.5%) - Budget-conscious, Instagram user
   → Manager Maria (15.8%) - Decision maker, email/LinkedIn

3. 📱 Composed targeted ads for each persona
   → LinkedIn ad for professionals ($99 ticket)
   → Instagram ad for students ($59 with STUDENT40 code)
   → Email campaign for managers (VIP tier)

4. 🎯 Optimized advertising radius
   → Analyzed 5, 10, 25, 50 mile radius
   → Selected 25 miles (optimal reach/cost balance)
   → Targets 410,400 tech professionals

5. 💰 Allocated $3,000 budget intelligently
   → 50% to tech professionals (highest ROI)
   → 25% to students (volume play)
   → 25% to managers (premium tier)

6. 📊 Projected results
   → 250k impressions, 5k clicks
   → 200-250 ticket sales
   → $20k-25k revenue
   → 6.6x - 8.25x ROI

ALL AUTOMATED. Just provide venue location and event type.
Agent handles demographics, personas, ad copy, targeting, and budget.
""")

print("=" * 80)
print("🚀 READY TO USE")
print("=" * 80)
print("\nEndpoints:")
print("  GET  /api/venue-intelligence/analyze-venue/{venue_id}")
print("  POST /api/venue-intelligence/compose-ads?event_id={event_id}")
print("  POST /api/venue-intelligence/optimize-radius?event_id={event_id}")
print("\nVoice:")
print("  'Analyze the demographics around Convention Center'")
print("  'Compose targeted ads for my event at this venue'")
print("  'What's the best advertising radius for my event?'")
print("=" * 80 + "\n")
