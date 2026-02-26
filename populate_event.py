"""Populate an event with all possible fields for testing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Event, EventCategory, EventPhoto, TicketTier, Venue, TierStatus, EventStatus
from datetime import datetime, timedelta
import random

db = SessionLocal()

try:
    # Create or update a venue
    venue = db.query(Venue).filter(Venue.name == "Scotiabank Arena").first()
    if not venue:
        venue = Venue(
            name="Scotiabank Arena",
            address="40 Bay St, Toronto, ON M5J 2W2, Canada",
            phone="+1 (416) 815-5500",
            description="Premier sports and entertainment venue in downtown Toronto.",
            logo_url="https://upload.wikimedia.org/wikipedia/en/thumb/5/57/Scotiabank_Arena_%282018%29.svg/200px-Scotiabank_Arena_%282018%29.svg.png",
        )
        db.add(venue)
        db.commit()
        db.refresh(venue)
        print(f"✓ Created venue: {venue.name}")
    else:
        venue.logo_url = "https://upload.wikimedia.org/wikipedia/en/thumb/5/57/Scotiabank_Arena_%282018%29.svg/200px-Scotiabank_Arena_%282018%29.svg.png"
        venue.phone = "+1 (416) 815-5500"
        venue.description = "Premier sports and entertainment venue in downtown Toronto."
        db.commit()
        print(f"✓ Updated venue: {venue.name}")

    # Create categories
    categories_to_create = [
        {"name": "Sports", "description": "Sporting events and games", "color": "#CE1141"},
        {"name": "Concerts", "description": "Live music performances", "color": "#1E88E5"},
        {"name": "Comedy", "description": "Stand-up comedy shows", "color": "#FFA726"},
        {"name": "Networking", "description": "Business and professional networking", "color": "#66BB6A"},
    ]

    categories = []
    for cat_data in categories_to_create:
        cat = db.query(EventCategory).filter(EventCategory.name == cat_data["name"]).first()
        if not cat:
            cat = EventCategory(**cat_data)
            db.add(cat)
            db.commit()
            db.refresh(cat)
            print(f"✓ Created category: {cat.name}")
        else:
            cat.description = cat_data["description"]
            cat.color = cat_data["color"]
            db.commit()
        categories.append(cat)

    # Create or update the event with all fields
    event = db.query(Event).filter(Event.id == 1).first()
    if not event:
        event = Event(venue_id=venue.id)
        db.add(event)
        db.commit()
        db.refresh(event)

    # Update all event fields
    event.name = "Toronto Raptors vs Golden State Warriors"
    event.description = """Don't miss this epic NBA showdown as the Toronto Raptors host the Golden State Warriors!

🏀 What to Expect:
- High-intensity NBA action featuring some of the league's biggest stars
- Pre-game fan zone with interactive games and giveaways
- Half-time show featuring special performances
- Exclusive merchandise available only at the arena

📍 Venue Highlights:
- Premium seating options with court-side views
- Multiple food and beverage options throughout the arena
- Easy access via public transit (Union Station)

🎫 Ticket Information:
- Doors open 90 minutes before tip-off
- Early bird fans can catch warm-ups starting 60 minutes prior
- All tickets include access to pre-game fan zone

This is a must-see event for basketball fans and sports enthusiasts alike!"""

    event.image_url = "https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=1200&h=800&fit=crop"
    event.promo_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    event.post_event_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    event.event_date = "2026-03-15"
    event.event_time = "19:30"
    event.doors_open_time = "18:00"

    # Set ticket sale start to 3 days from now (for demo)
    sale_start = datetime.now() + timedelta(days=3)
    event.sale_start_date = sale_start.strftime("%Y-%m-%d")
    event.sale_start_time = "10:00"

    event.status = EventStatus.SCHEDULED
    event.is_visible = True
    event.uploads_open = True
    event.auto_reminder_hours = 24
    event.auto_reminder_use_sms = True

    # Promoter info
    event.promoter_name = "Maple Leaf Sports & Entertainment"
    event.promoter_email = "events@mlse.com"
    event.promoter_phone = "+1 (416) 815-5400"

    db.commit()
    print(f"✓ Updated event: {event.name}")

    # Link categories to event
    event.categories = categories
    db.commit()
    print(f"✓ Linked {len(categories)} categories to event")

    # Clear existing ticket tiers
    db.query(TicketTier).filter(TicketTier.event_id == event.id).delete()

    # Create 3 ticket tiers
    ticket_tiers = [
        {
            "name": "VIP Courtside",
            "description": " courtside seats with premium dining, dedicated concierge service, and post-game player access.",
            "price": 25000,  # $250.00
            "quantity_available": 50,
            "quantity_sold": 35,
            "status": TierStatus.ACTIVE,
        },
        {
            "name": "Premium seating",
            "description": "Great seats with excellent views of all the action. Includes access to VIP lounge and complimentary beverages.",
            "price": 12000,  # $120.00
            "quantity_available": 500,
            "quantity_sold": 420,
            "status": TierStatus.ACTIVE,
        },
        {
            "name": "General Admission",
            "description": "Affordable seats with great views. Perfect for fans who want to enjoy the game without breaking the bank.",
            "price": 5500,  # $55.00
            "quantity_available": 2000,
            "quantity_sold": 1500,
            "status": TierStatus.ACTIVE,
        },
    ]

    for tier_data in ticket_tiers:
        tier = TicketTier(event_id=event.id, **tier_data)
        db.add(tier)

    db.commit()
    print(f"✓ Created {len(ticket_tiers)} ticket tiers")

    # Clear existing photos and add new ones
    db.query(EventPhoto).filter(EventPhoto.event_id == event.id).delete()

    photos = [
        {
            "photo_url": "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=800&h=600&fit=crop",
            "uploaded_by_name": "Raptors Photography Team",
            "media_type": "photo",
            "moderation_status": "approved",
        },
        {
            "photo_url": "https://images.unsplash.com/photo-1519861531473-9200262188bf?w=800&h=600&fit=crop",
            "uploaded_by_name": "MLSE Media",
            "media_type": "photo",
            "moderation_status": "approved",
        },
        {
            "photo_url": "https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=800&h=600&fit=crop",
            "uploaded_by_name": "Fan Submission",
            "media_type": "photo",
            "moderation_status": "approved",
        },
        {
            "photo_url": "https://images.unsplash.com/photo-1526279167291-0a844c7c3654?w=800&h=600&fit=crop",
            "uploaded_by_name": "Arena Staff",
            "media_type": "photo",
            "moderation_status": "approved",
        },
        {
            "photo_url": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800&h=600&fit=crop",
            "uploaded_by_name": "Sports Illustrated",
            "media_type": "photo",
            "moderation_status": "approved",
        },
    ]

    for photo_data in photos:
        photo = EventPhoto(event_id=event.id, **photo_data)
        db.add(photo)

    db.commit()
    print(f"✓ Added {len(photos)} event photos")

    print("\n" + "="*60)
    print("✅ Event fully populated with all fields!")
    print("="*60)
    print(f"\nEvent ID: {event.id}")
    print(f"Name: {event.name}")
    print(f"Date: {event.event_date} at {event.event_time}")
    print(f"Doors Open: {event.doors_open_time}")
    print(f"Tickets Go On Sale: {event.sale_start_date} at {event.sale_start_time}")
    print(f"Venue: {venue.name}")
    print(f"Categories: {', '.join([c.name for c in categories])}")
    print(f"Ticket Tiers: {len(ticket_tiers)}")
    print(f"Photos: {len(photos)}")
    print(f"\nView at: http://127.0.0.1:8080/events/{event.id}")
    print("="*60)

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
    raise
finally:
    db.close()
