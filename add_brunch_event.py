#!/usr/bin/env python3
"""
Script to add a test brunch event for May 5th at Peru Chicken in Hillsborough, NJ
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.database import SessionLocal, init_db
from app.models import (
    Venue, Event, EventCategory, TicketTier, EventUpdate,
    EventPhoto, EventStatus, TierStatus
)

def add_brunch_event():
    """Add Peru Chicken brunch event to the database"""

    # Initialize database and create tables if needed
    print("Initializing database...")
    init_db()

    # Create database session
    db = SessionLocal()

    try:
        # 1. Create or get the venue
        print("\n1. Setting up Peru Chicken venue...")
        venue = db.query(Venue).filter_by(name="Peru Chicken").first()

        if not venue:
            venue = Venue(
                name="Peru Chicken",
                address="360 US-206, Hillsborough, NJ 08844",
                phone="(908) 431-0012",
                description="Authentic Peruvian rotisserie chicken and traditional dishes in a warm, family-friendly atmosphere. Located in Hillsborough, NJ.",
                logo_url="https://images.unsplash.com/photo-1513639725746-c5d3e861f32b"  # Peruvian food image
            )
            db.add(venue)
            db.flush()
            print(f"✓ Created venue: {venue.name} (ID: {venue.id})")
        else:
            print(f"✓ Using existing venue: {venue.name} (ID: {venue.id})")

        # 2. Create or get the category
        print("\n2. Setting up Food & Dining category...")
        category = db.query(EventCategory).filter_by(name="Food & Dining").first()

        if not category:
            category = EventCategory(
                name="Food & Dining",
                description="Culinary experiences, brunches, dinners, and food festivals"
            )
            db.add(category)
            db.flush()
            print(f"✓ Created category: {category.name}")
        else:
            print(f"✓ Using existing category: {category.name}")

        # 3. Create the brunch event
        print("\n3. Creating Mother's Day Peruvian Brunch event...")

        # Check if event already exists
        existing_event = db.query(Event).filter_by(
            name="Mother's Day Weekend Peruvian Brunch",
            venue_id=venue.id
        ).first()

        if existing_event:
            print(f"✗ Event already exists: {existing_event.name} (ID: {existing_event.id})")
            event = existing_event
        else:
            event = Event(
                name="Mother's Day Weekend Peruvian Brunch",
                description="""🌺 Special Mother's Day Weekend Peruvian Brunch Experience 🌺

Join us for an unforgettable Peruvian brunch celebrating mothers and Cinco de Mayo!

🍳 BRUNCH HIGHLIGHTS:
• Authentic Peruvian breakfast specialties
• Bottomless Pisco Sours and Chicha Morada
• Live Peruvian music performance
• Complimentary rose for all mothers
• Traditional Anticuchos and Ceviche bar
• Lomo Saltado and Aji de Gallina stations
• Tres Leches cake and Alfajores dessert bar

🎵 LIVE ENTERTAINMENT:
Featuring traditional Marinera dancers and live Criolla music from 12:00 PM

👨‍👩‍👧‍👦 FAMILY-FRIENDLY:
Kids under 10 eat free with adult entrée purchase!

📸 PHOTO OPPORTUNITY:
Professional photographer on-site for family portraits with Peruvian backdrop

🎁 SPECIAL GIFT:
All mothers receive a special Peruvian artisan gift bag

⏰ SCHEDULE:
• 11:00 AM - Doors open, welcome Pisco Sour
• 11:30 AM - Brunch service begins
• 12:00 PM - Live entertainment starts
• 2:30 PM - Event concludes

📍 LOCATION:
Peru Chicken - Hillsborough
360 US-206, Hillsborough, NJ 08844

🎟️ RESERVATIONS REQUIRED
Limited seating - Book your table now!

Note: Vegetarian and gluten-free options available upon request.""",
                venue_id=venue.id,
                event_date="2024-05-05",  # May 5th, 2024
                event_time="11:00",  # 11:00 AM
                doors_open_time="10:45",  # 15 minutes before
                sale_start_date="2024-04-01",  # Tickets go on sale April 1st
                sale_start_time="10:00",
                status=EventStatus.SCHEDULED,
                image_url="https://images.unsplash.com/photo-1555396273-367ea4eb4db5",  # Restaurant brunch image
                promo_video_url="https://www.youtube.com/watch?v=PERU_BRUNCH",
                promoter_name="Peru Chicken Restaurant",
                promoter_email="events@peruchicken.com",
                promoter_phone="(908) 431-0012",
                auto_reminder_hours=24,  # Send reminder 24 hours before
                auto_reminder_use_sms=True,  # Use SMS for reminders
                uploads_open=True  # Accept photo uploads from attendees
            )
            db.add(event)
            db.flush()

            # Add category association
            event.categories.append(category)
            db.flush()

            print(f"✓ Created event: {event.name} (ID: {event.id})")

        # 4. Create ticket tiers
        print("\n4. Setting up ticket tiers...")

        # Check if tiers already exist
        existing_tiers = db.query(TicketTier).filter_by(event_id=event.id).count()

        if existing_tiers > 0:
            print(f"✗ Ticket tiers already exist for this event ({existing_tiers} tiers)")
        else:
            tiers = [
                TicketTier(
                    event_id=event.id,
                    name="Adult Brunch",
                    description="Full brunch buffet with bottomless drinks",
                    price=7500,  # Price in cents: $75.00
                    quantity_available=48,  # 48 available
                    quantity_sold=12,  # 12 sold
                    status=TierStatus.ACTIVE
                ),
                TicketTier(
                    event_id=event.id,
                    name="Adult Brunch (No Alcohol)",
                    description="Full brunch buffet with non-alcoholic beverages",
                    price=5500,  # Price in cents: $55.00
                    quantity_available=18,  # 18 available
                    quantity_sold=2,  # 2 sold
                    status=TierStatus.ACTIVE
                ),
                TicketTier(
                    event_id=event.id,
                    name="VIP Mother's Package",
                    description="Premium seating, champagne, special gift, and spa voucher",
                    price=12500,  # Price in cents: $125.00
                    quantity_available=7,  # 7 available
                    quantity_sold=3,  # 3 sold
                    status=TierStatus.ACTIVE
                )
            ]

            for tier in tiers:
                db.add(tier)
                print(f"  ✓ Added tier: {tier.name} - ${tier.price/100:.2f} ({tier.quantity_available} available, {tier.quantity_sold} sold)")

        # 5. Add event updates
        print("\n5. Adding event updates...")

        existing_updates = db.query(EventUpdate).filter_by(event_id=event.id).count()
        if existing_updates > 0:
            print(f"✗ Event updates already exist ({existing_updates} updates)")
        else:
            updates = [
                EventUpdate(
                    event_id=event.id,
                    update_type="announcement",
                    message="Early Bird Special! Book before April 20th and save 10% with code MADRE10"
                ),
                EventUpdate(
                    event_id=event.id,
                    update_type="announcement",
                    message="Limited VIP Packages Available! Only 10 VIP Mother's Packages available - includes premium seating and special gifts!"
                ),
                EventUpdate(
                    event_id=event.id,
                    update_type="announcement",
                    message="Live Music Confirmed! We're excited to announce Los Hermanos Paz will be performing live Peruvian music!"
                )
            ]

            for update in updates:
                db.add(update)
                print(f"  ✓ Added update: {update.update_type} - {update.message[:50]}...")

        # 6. Add event photos
        print("\n6. Adding event photos...")

        existing_photos = db.query(EventPhoto).filter_by(event_id=event.id).count()
        if existing_photos > 0:
            print(f"✗ Event photos already exist ({existing_photos} photos)")
        else:
            photos = [
                EventPhoto(
                    event_id=event.id,
                    photo_url="https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c",
                    uploaded_by_name="Peru Chicken Team",
                    media_type="photo"
                ),
                EventPhoto(
                    event_id=event.id,
                    photo_url="https://images.unsplash.com/photo-1504674900247-0877df9cc836",
                    uploaded_by_name="Peru Chicken Team",
                    media_type="photo"
                ),
                EventPhoto(
                    event_id=event.id,
                    photo_url="https://images.unsplash.com/photo-1414235077428-338989a2e8c0",
                    uploaded_by_name="Peru Chicken Team",
                    media_type="photo"
                )
            ]

            for photo in photos:
                db.add(photo)
                print(f"  ✓ Added photo from: {photo.uploaded_by_name}")

        # Commit all changes
        db.commit()

        print("\n" + "="*60)
        print("✅ BRUNCH EVENT SUCCESSFULLY CREATED!")
        print("="*60)
        print(f"\n📍 Venue: {venue.name}")
        print(f"📅 Date: May 5, 2024 at 11:00 AM")
        print(f"🎫 Tickets: Multiple tiers available")
        print(f"💵 Price: Starting at $55")
        print(f"🏷️ Event ID: {event.id}")

        print("\n🎯 Quick Actions:")
        print("  • View event: GET /api/events/" + str(event.id))
        print("  • Purchase tickets: POST /api/tickets/purchase")
        print("  • Check availability: GET /api/ticket-tiers?event_id=" + str(event.id))

        print("\n🎤 Voice Commands You Can Try:")
        print('  • "Show me the Peru Chicken brunch event"')
        print('  • "How many tickets are left for the Mother\'s Day brunch?"')
        print('  • "Purchase 2 VIP tickets for the Peru Chicken event"')
        print('  • "Send a reminder about the brunch to all ticket holders"')

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()
        print("\n✓ Database connection closed")

if __name__ == "__main__":
    add_brunch_event()
    print("\n🎉 Script completed successfully!")