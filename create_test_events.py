#!/usr/bin/env python3
"""
Create test events with venues, ticket tiers, and sample data
"""
import requests
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

def create_venue(name, address, city, state, capacity):
    """Create a venue"""
    response = requests.post(f"{BASE_URL}/api/venues", json={
        "name": name,
        "address": address,
        "city": city,
        "state": state,
        "capacity": capacity
    })
    if response.status_code in [200, 201]:
        venue = response.json()
        print(f"✅ Created venue: {name} (ID: {venue['id']})")
        return venue
    else:
        print(f"❌ Failed to create venue {name}: Status {response.status_code} - {response.text}")
        return None

def create_event(venue_id, name, description, event_datetime, capacity, category="technology"):
    """Create an event"""
    # Split datetime into date and time
    dt = datetime.fromisoformat(event_datetime) if isinstance(event_datetime, str) else event_datetime
    event_date = dt.strftime("%Y-%m-%d")
    event_time = dt.strftime("%H:%M:%S")

    response = requests.post(f"{BASE_URL}/api/events", json={
        "venue_id": venue_id,
        "name": name,
        "description": description,
        "event_date": event_date,
        "event_time": event_time,
        "capacity": capacity,
        "category": category,
        "visibility": "public"
    })
    if response.status_code in [200, 201]:
        event = response.json()
        print(f"✅ Created event: {name} (ID: {event['id']})")
        return event
    else:
        print(f"❌ Failed to create event {name}: Status {response.status_code} - {response.text}")
        return None

def create_ticket_tier(event_id, name, price, quantity):
    """Create a ticket tier"""
    response = requests.post(f"{BASE_URL}/api/events/{event_id}/tiers", json={
        "name": name,
        "description": f"{name} access to the event",
        "price": price,
        "quantity_available": quantity
    })
    if response.status_code in [200, 201]:
        tier = response.json()
        print(f"  ✅ Created tier: {name} - ${price/100:.2f} ({quantity} tickets)")
        return tier
    else:
        print(f"  ❌ Failed to create tier {name}: Status {response.status_code} - {response.text}")
        return None

print("=" * 80)
print("🎫 CREATING TEST EVENTS FOR AI TICKETS PLATFORM")
print("=" * 80)

# Create venues
print("\n📍 Creating Venues...")
venue1 = create_venue(
    "Moscone Center",
    "747 Howard Street",
    "San Francisco",
    "CA",
    5000
)

venue2 = create_venue(
    "Austin Convention Center",
    "500 E Cesar Chavez St",
    "Austin",
    "TX",
    4000
)

venue3 = create_venue(
    "Brooklyn Steel",
    "319 Frost St",
    "Brooklyn",
    "NY",
    1800
)

venue4 = create_venue(
    "The Fillmore",
    "1805 Geary Blvd",
    "San Francisco",
    "CA",
    1315
)

# Create events
print("\n🎉 Creating Events...")

# Event 1: Tech Conference
if venue1:
    event1 = create_event(
        venue1['id'],
        "AI Summit 2026",
        "Join 500+ tech professionals for the premier AI and machine learning conference in San Francisco. "
        "Learn from industry leaders, network with peers, and discover cutting-edge AI applications across industries. "
        "Features keynotes from Google, Meta, and OpenAI executives, hands-on workshops, and startup showcase.",
        (datetime.now() + timedelta(days=60)).isoformat(),
        500,
        "technology"
    )
    if event1:
        create_ticket_tier(event1['id'], "Early Bird", 7900, 100)
        create_ticket_tier(event1['id'], "General Admission", 9900, 300)
        create_ticket_tier(event1['id'], "VIP Access", 29900, 100)

# Event 2: Music Festival
if venue2:
    event2 = create_event(
        venue2['id'],
        "South by Southwest Music Festival",
        "Austin's premier music festival featuring 200+ artists across multiple stages. "
        "Experience indie rock, electronic, hip-hop, and more. 3-day festival pass includes "
        "access to all stages, food vendors, and exclusive after-parties.",
        (datetime.now() + timedelta(days=90)).isoformat(),
        3000,
        "music"
    )
    if event2:
        create_ticket_tier(event2['id'], "Single Day Pass", 8900, 1000)
        create_ticket_tier(event2['id'], "3-Day General", 19900, 1500)
        create_ticket_tier(event2['id'], "VIP 3-Day", 49900, 500)

# Event 3: Comedy Show
if venue3:
    event3 = create_event(
        venue3['id'],
        "Comedy Night: NYC's Best",
        "An evening of laughs with some of New York's hottest comedians. "
        "Featuring headliners from Comedy Central, Netflix specials, and SNL. "
        "Intimate venue, full bar, and guaranteed laughs. 21+ only.",
        (datetime.now() + timedelta(days=30)).isoformat(),
        400,
        "comedy"
    )
    if event3:
        create_ticket_tier(event3['id'], "General Admission", 3500, 300)
        create_ticket_tier(event3['id'], "Front Row", 6500, 50)
        create_ticket_tier(event3['id'], "VIP Table (4 seats)", 25000, 50)

# Event 4: Food & Wine Event
if venue4:
    event4 = create_event(
        venue4['id'],
        "SF Wine & Food Experience",
        "Taste wines from 50+ California wineries paired with gourmet food from SF's top chefs. "
        "Features live jazz music, sommelier-led tastings, and cooking demonstrations. "
        "A portion of proceeds benefits local food banks.",
        (datetime.now() + timedelta(days=45)).isoformat(),
        800,
        "food"
    )
    if event4:
        create_ticket_tier(event4['id'], "General Tasting", 8500, 500)
        create_ticket_tier(event4['id'], "Premium Tasting", 15000, 200)
        create_ticket_tier(event4['id'], "Sommelier Experience", 29900, 100)

# Event 5: Tech Workshop
if venue1:
    event5 = create_event(
        venue1['id'],
        "Build with AI: Hands-On Workshop",
        "Full-day intensive workshop on building AI applications. Learn to use ChatGPT API, "
        "create custom GPTs, and build real AI tools. Includes laptop setup help, "
        "code templates, and 3 months of API credits. Perfect for developers and entrepreneurs.",
        (datetime.now() + timedelta(days=21)).isoformat(),
        150,
        "technology"
    )
    if event5:
        create_ticket_tier(event5['id'], "Individual", 29900, 100)
        create_ticket_tier(event5['id'], "Team (5 seats)", 120000, 50)

print("\n" + "=" * 80)
print("✨ TEST DATA CREATED SUCCESSFULLY!")
print("=" * 80)

print("\n📊 Summary:")
print(f"  • Venues created: 4")
print(f"  • Events created: 5")
print(f"  • Ticket tiers: 15+")

print("\n🌐 Access the platform:")
print(f"  • API Docs: {BASE_URL}/docs")
print(f"  • Health Check: {BASE_URL}/health")
print(f"  • Public Events: {BASE_URL}/events")

print("\n💡 Next steps:")
print("  1. Visit http://127.0.0.1:8000/events to see public event listings")
print("  2. Visit http://127.0.0.1:8000/docs to explore the API")
print("  3. Test the marketing plan PDF export for any event")

print("\n" + "=" * 80)
