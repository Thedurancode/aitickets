#!/usr/bin/env python3
"""
Marketing Plan PDF Export Demo

Demonstrates the automatic generation of comprehensive marketing plan PDFs
including demographics, personas, ad campaigns, budget allocation, timeline, and ROI.
"""
import json
from datetime import datetime, timedelta
from app.services.marketing_plan_pdf import generate_marketing_plan_pdf, create_sample_marketing_timeline


print("=" * 80)
print("📄 MARKETING PLAN PDF EXPORT - DEMONSTRATION")
print("=" * 80)

# ==================== SAMPLE EVENT DATA ====================

event = {
    "name": "AI Summit 2026",
    "date": datetime(2026, 6, 15, 14, 0),
    "description": "Join 500+ tech professionals for the premier AI and machine learning conference in San Francisco. Learn from industry leaders, network with peers, and discover cutting-edge AI applications across industries.",
    "capacity": 500,
    "category": "technology",
    "ticket_tiers": [
        {"name": "General Admission", "price": 9900, "quantity": 400},
        {"name": "VIP Access", "price": 29900, "quantity": 100}
    ]
}

venue = {
    "name": "Convention Center",
    "address": "747 Howard Street",
    "city": "San Francisco",
    "state": "CA"
}

demographics = {
    "population": {
        "5_mile_radius": 125000,
        "10_mile_radius": 450000,
        "25_mile_radius": 1200000,
        "50_mile_radius": 2500000
    },
    "age_distribution": {
        "18-24": 18.5,
        "25-34": 32.1,
        "35-44": 21.3,
        "45-54": 15.2,
        "55+": 12.9
    },
    "income_distribution": {
        "Under $35k": 12.3,
        "$35k-$50k": 14.5,
        "$50k-$75k": 18.9,
        "$75k-$100k": 19.4,
        "$100k-$150k": 15.8,
        "Over $150k": 19.1
    },
    "education": {
        "high_school": 15.2,
        "some_college": 21.3,
        "bachelors": 31.2,
        "graduate_degree": 18.4
    },
    "employment": {
        "tech_sector": 28.4,
        "finance": 12.3,
        "healthcare": 9.8,
        "education": 8.2,
        "retail": 7.1
    },
    "interests": {
        "technology": 34.2,
        "food": 45.3,
        "music": 28.7,
        "sports": 32.1,
        "arts": 22.4
    }
}

personas = [
    {
        "name": "Tech Professional Alex",
        "percentage": 34.2,
        "demographics": {
            "age": "25-34",
            "income": "$75k-$150k",
            "education": "Bachelor's or Master's degree"
        },
        "psychographics": {
            "interests": ["artificial intelligence", "machine learning", "startups", "innovation"],
            "values": ["career growth", "continuous learning", "networking", "cutting-edge technology"]
        },
        "media_consumption": {
            "platforms": ["LinkedIn", "Twitter/X", "Reddit", "Tech blogs"],
            "peak_hours": ["7-9am (commute)", "12-1pm (lunch)", "6-10pm (evening)"]
        },
        "marketing_approach": {
            "messaging": "Advance your AI career. Network with industry leaders.",
            "channels": ["LinkedIn Ads", "Google Search", "Tech newsletters"]
        }
    },
    {
        "name": "Student Sam",
        "percentage": 18.5,
        "demographics": {
            "age": "18-24",
            "income": "$0-$35k",
            "education": "Currently enrolled in college"
        },
        "psychographics": {
            "interests": ["career development", "learning", "internships", "job opportunities"],
            "values": ["education", "networking", "first job", "building skills"]
        },
        "media_consumption": {
            "platforms": ["Instagram", "TikTok", "YouTube", "Discord"],
            "peak_hours": ["10am-12pm", "3-5pm", "9-11pm"]
        },
        "marketing_approach": {
            "messaging": "Launch your tech career. Student discounts available.",
            "channels": ["Instagram Ads", "University partnerships", "Student groups"]
        }
    },
    {
        "name": "Manager Maria",
        "percentage": 15.8,
        "demographics": {
            "age": "35-44",
            "income": "$100k-$200k",
            "education": "Master's degree or MBA"
        },
        "psychographics": {
            "interests": ["leadership", "team development", "AI strategy", "innovation"],
            "values": ["business results", "competitive advantage", "executive networking"]
        },
        "media_consumption": {
            "platforms": ["LinkedIn", "Email newsletters", "Business publications"],
            "peak_hours": ["6-8am (morning routine)", "12-1pm (lunch)", "7-9pm (evening)"]
        },
        "marketing_approach": {
            "messaging": "Lead your team into the AI era. Executive insights.",
            "channels": ["LinkedIn Ads", "Email marketing", "Direct outreach"]
        }
    }
]

ad_campaigns = [
    {
        "segment": {"name": "Tech Professional Alex", "percentage": 34.2},
        "meta_ads": [
            {
                "platform": "LinkedIn",
                "headline": "AI Summit 2026 - Advance Your Tech Career",
                "primary_text": "Join 500+ tech professionals at San Francisco's premier AI conference. Learn from industry leaders, network with peers, and discover cutting-edge applications. Limited seats available.",
                "targeting": {
                    "age": "25-34",
                    "location": "San Francisco, CA + 25 miles",
                    "interests": ["Artificial Intelligence", "Machine Learning", "Technology"],
                    "job_titles": ["Software Engineer", "Data Scientist", "ML Engineer"],
                    "behaviors": "Early technology adopters"
                }
            },
            {
                "platform": "Facebook",
                "headline": "The AI Conference Tech Leaders Attend",
                "primary_text": "Network with 500+ AI professionals. Hands-on workshops, expert speakers, and real-world case studies. Early bird pricing ends soon!",
                "targeting": {
                    "age": "25-34",
                    "location": "San Francisco, CA + 25 miles",
                    "interests": ["Technology", "Artificial Intelligence", "Professional Development"]
                }
            }
        ],
        "google_ads": [
            {
                "platform": "Google Search",
                "headline": "AI Summit SF 2026 | June 15",
                "description": "Premier AI Conference. 500+ Tech Pros. Expert Speakers. Register Now!",
                "keywords": ["ai conference san francisco", "machine learning summit", "tech conference 2026"]
            }
        ],
        "email_marketing": {
            "subject": "You're Invited: AI Summit 2026 - San Francisco",
            "preview_text": "Join 500+ tech professionals for the premier AI conference",
            "content_highlights": [
                "Keynote speakers from Google, Meta, OpenAI",
                "Hands-on AI/ML workshops",
                "Networking with 500+ professionals",
                "Early bird pricing: Save $40"
            ]
        },
        "expected_reach": 85000,
        "estimated_ctr": 2.8,
        "suggested_budget": 150000,
        "suggested_budget_formatted": "$1,500"
    },
    {
        "segment": {"name": "Student Sam", "percentage": 18.5},
        "meta_ads": [
            {
                "platform": "Instagram",
                "headline": "🚀 Launch Your Tech Career - AI Summit 2026",
                "primary_text": "STUDENT SPECIAL: 40% OFF with code STUDENT40. Learn from industry leaders, build your network, and land your dream job in AI.",
                "targeting": {
                    "age": "18-24",
                    "location": "San Francisco, CA + 50 miles",
                    "education_status": "In college",
                    "schools": ["Stanford University", "UC Berkeley", "San Jose State"]
                }
            }
        ],
        "google_ads": [
            {
                "platform": "Google Display",
                "headline": "Student Discount: AI Summit 2026",
                "description": "40% off for students. Learn AI/ML from experts. Network with professionals.",
                "placements": ["University websites", "Student portals", "Career services"]
            }
        ],
        "email_marketing": {
            "subject": "🎓 Student Discount: AI Summit 2026 (40% OFF)",
            "preview_text": "Limited student tickets - Use code STUDENT40",
            "content_highlights": [
                "Exclusive 40% student discount",
                "Career fair with top tech companies",
                "Resume reviews and mentorship",
                "Student networking session"
            ]
        },
        "expected_reach": 25000,
        "estimated_ctr": 3.5,
        "suggested_budget": 75000,
        "suggested_budget_formatted": "$750"
    },
    {
        "segment": {"name": "Manager Maria", "percentage": 15.8},
        "meta_ads": [
            {
                "platform": "LinkedIn",
                "headline": "Executive AI Training for Leaders",
                "primary_text": "Transform your team with AI. Join C-suite executives and senior leaders for strategic insights on implementing AI across your organization. VIP access includes exclusive dinner.",
                "targeting": {
                    "age": "35-54",
                    "location": "San Francisco, CA + 25 miles",
                    "job_titles": ["Director", "VP", "Senior Manager", "C-Level"],
                    "company_size": "50+ employees"
                }
            }
        ],
        "google_ads": [
            {
                "platform": "Google Search",
                "headline": "AI Strategy for Executives | SF",
                "description": "VIP Summit for Tech Leaders. Strategic AI Implementation. June 15, 2026.",
                "keywords": ["ai for executives", "ai strategy", "executive summit ai"]
            }
        ],
        "email_marketing": {
            "subject": "AI Strategy Summit for Executives - June 15",
            "preview_text": "VIP experience with exclusive executive dinner",
            "content_highlights": [
                "C-suite panel: AI implementation strategies",
                "VIP executive dinner and networking",
                "1-on-1 consultation sessions",
                "AI ROI case studies"
            ]
        },
        "expected_reach": 15000,
        "estimated_ctr": 2.2,
        "suggested_budget": 75000,
        "suggested_budget_formatted": "$750"
    }
]

budget_allocation = {
    "total_budget": 300000,
    "total_budget_formatted": "$3,000",
    "by_channel": [
        {"channel": "Meta Ads (Facebook/Instagram)", "budget": 120000, "budget_formatted": "$1,200", "percentage": 40, "expected_roi": "4.5x"},
        {"channel": "Google Ads (Search/Display)", "budget": 90000, "budget_formatted": "$900", "percentage": 30, "expected_roi": "3.8x"},
        {"channel": "Email Marketing", "budget": 30000, "budget_formatted": "$300", "percentage": 10, "expected_roi": "8.0x"},
        {"channel": "Social Media (Organic)", "budget": 30000, "budget_formatted": "$300", "percentage": 10, "expected_roi": "5.2x"},
        {"channel": "Affiliates/Influencers", "budget": 30000, "budget_formatted": "$300", "percentage": 10, "expected_roi": "6.5x"}
    ],
    "by_persona": [
        {"segment": "Tech Professional Alex", "budget": 150000, "budget_formatted": "$1,500", "percentage": 50},
        {"segment": "Student Sam", "budget": 75000, "budget_formatted": "$750", "percentage": 25},
        {"segment": "Manager Maria", "budget": 75000, "budget_formatted": "$750", "percentage": 25}
    ]
}

timeline = create_sample_marketing_timeline(event["date"])

roi_projections = {
    "expected_impressions": 250000,
    "expected_clicks": 5000,
    "expected_conversions": 300,
    "expected_tickets": 375,
    "expected_revenue": 4987500,  # $49,875
    "expected_revenue_formatted": "$49,875.00",
    "marketing_cost": 300000,
    "net_profit": 4687500,
    "net_profit_formatted": "$46,875.00",
    "roi_multiplier": 16.63
}

# ==================== GENERATE PDF ====================

print("\n📊 GENERATING MARKETING PLAN PDF...")
print("─" * 80)

print("\n✅ Event Details:")
print(f"   Name: {event['name']}")
print(f"   Date: {event['date'].strftime('%B %d, %Y')}")
print(f"   Venue: {venue['name']}, {venue['city']}, {venue['state']}")
print(f"   Capacity: {event['capacity']} attendees")

print("\n✅ Marketing Budget:")
print(f"   Total: {budget_allocation['total_budget_formatted']}")
print(f"   Channels: {len(budget_allocation['by_channel'])}")
print(f"   Target Personas: {len(personas)}")

print("\n✅ Expected Results:")
print(f"   Impressions: {roi_projections['expected_impressions']:,}")
print(f"   Clicks: {roi_projections['expected_clicks']:,}")
print(f"   Tickets Sold: {roi_projections['expected_tickets']}")
print(f"   Revenue: {roi_projections['expected_revenue_formatted']}")
print(f"   ROI: {roi_projections['roi_multiplier']}x")

print("\n🔧 Generating PDF with:")
print("   ✓ Executive Summary")
print("   ✓ Event Overview with Ticket Tiers")
print("   ✓ Demographic Analysis (Census data)")
print("   ✓ 3 Target Audience Personas")
print("   ✓ Multi-Channel Ad Campaigns")
print("   ✓ Budget Allocation Tables")
print("   ✓ Marketing Timeline (14 milestones)")
print("   ✓ ROI Projections & Metrics")
print("   ✓ KPI Tracking Plan")

# Generate the PDF
pdf_bytes = generate_marketing_plan_pdf(
    event=event,
    venue=venue,
    demographics=demographics,
    personas=personas,
    ad_campaigns=ad_campaigns,
    budget_allocation=budget_allocation,
    timeline=timeline,
    roi_projections=roi_projections
)

# Save to file
output_filename = f"marketing_plan_ai_summit_2026_{datetime.now().strftime('%Y%m%d')}.pdf"

with open(output_filename, 'wb') as f:
    f.write(pdf_bytes)

file_size_kb = len(pdf_bytes) / 1024

print(f"\n✅ PDF GENERATED SUCCESSFULLY!")
print(f"\n📄 File Details:")
print(f"   Filename: {output_filename}")
print(f"   Size: {file_size_kb:.1f} KB")
print(f"   Pages: ~15-20 pages")

print("\n📋 PDF Contents:")
print("   1. Cover Page - Event title, date, venue")
print("   2. Executive Summary - Key metrics at a glance")
print("   3. Event Overview - Details, description, ticket tiers")
print("   4. Demographic Analysis - Population, age, income, education, employment")
print("   5. Target Personas - 3 detailed audience profiles")
print("   6. Marketing Strategy - Multi-channel approach")
print("   7. Budget Allocation - By channel and persona")
print("   8. Marketing Timeline - 14 milestones from launch to post-event")
print("   9. ROI Projections - Expected performance metrics")
print("   10. KPI Tracking Plan - 10 key metrics to monitor")
print("   11. Conclusion - Next steps and recommendations")

print("\n🎯 Sample Insights from PDF:")
print("\n   Demographic Highlights:")
print(f"   • {demographics['population']['25_mile_radius']:,} people within 25 miles")
print(f"   • {demographics['age_distribution']['25-34']}% aged 25-34 (prime target)")
print(f"   • {demographics['employment']['tech_sector']}% work in tech sector")
print(f"   • {demographics['education']['bachelors'] + demographics['education']['graduate_degree']}% have bachelor's or higher")

print("\n   Top Audience Personas:")
for i, persona in enumerate(personas, 1):
    print(f"   {i}. {persona['name']} ({persona['percentage']}%)")
    print(f"      → {persona['marketing_approach']['messaging']}")

print("\n   Budget Breakdown:")
for channel in budget_allocation['by_channel'][:3]:
    print(f"   • {channel['channel']}: {channel['budget_formatted']} ({channel['percentage']}%) - ROI: {channel['expected_roi']}")

print("\n   Marketing Timeline Highlights:")
for milestone in timeline[:5]:
    print(f"   • {milestone['timeline']}: {milestone['activity']}")

print("\n" + "=" * 80)
print("🎉 MARKETING PLAN PDF READY!")
print("=" * 80)

print(f"\n✨ Open the file: {output_filename}")
print("\n💡 This PDF can be:")
print("   • Shared with stakeholders for approval")
print("   • Used to guide marketing execution")
print("   • Updated as campaign progresses")
print("   • Included in post-event analysis")

print("\n🚀 API ENDPOINT:")
print("   POST /api/venue-intelligence/marketing-plan/{event_id}/pdf")
print("   Returns: Downloadable PDF file")

print("\n" + "=" * 80 + "\n")
