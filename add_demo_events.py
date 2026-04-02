"""
Add Demo Events

Creates diverse demo events to showcase the AI Tickets system:
- Latin music concerts (reggaeton, bachata, salsa)
- Food festivals
- Line dancing events
- Jazz concerts
- Hip hop shows

Run with: python3 add_demo_events.py
"""
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Event, Venue, TicketTier

def create_demo_events():
    """Create diverse demo events."""
    db = SessionLocal()

    try:
        # Check if venues exist, create if not
        venue1 = db.query(Venue).filter(Venue.name == "UBS Arena").first()
        if not venue1:
            venue1 = Venue(
                name="UBS Arena",
                address="2400 Hempstead Turnpike, Elmont, NY 11003"
            )
            db.add(venue1)
            db.flush()
            print(f"✅ Created venue: {venue1.name}")

        venue2 = db.query(Venue).filter(Venue.name == "Barclays Center").first()
        if not venue2:
            venue2 = Venue(
                name="Barclays Center",
                address="620 Atlantic Ave, Brooklyn, NY 11217"
            )
            db.add(venue2)
            db.flush()
            print(f"✅ Created venue: {venue2.name}")

        venue3 = db.query(Venue).filter(Venue.name == "Brooklyn Steel").first()
        if not venue3:
            venue3 = Venue(
                name="Brooklyn Steel",
                address="319 Frost St, Brooklyn, NY 11222"
            )
            db.add(venue3)
            db.flush()
            print(f"✅ Created venue: {venue3.name}")

        venue4 = db.query(Venue).filter(Venue.name == "Central Park SummerStage").first()
        if not venue4:
            venue4 = Venue(
                name="Central Park SummerStage",
                address="Rumsey Playfield, Central Park, New York, NY 10021"
            )
            db.add(venue4)
            db.flush()
            print(f"✅ Created venue: {venue4.name}")

        db.commit()

        # Demo events list
        demo_events = [
            {
                "name": "Anuel AA - Las Leyendas Nunca Mueren Tour",
                "description": "Latin trap and reggaeton superstar Anuel AA brings his explosive energy to NYC. Experience the hits from LLNM including 'Ella Quiere Beber', 'China', and 'Secreto'. Special guest performances TBA.",
                "venue": venue1,
                "event_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
                "doors_open": "19:00",
                "event_time": "21:00",
                "tiers": [
                    {"name": "General Admission", "price": 7500, "quantity": 5000},
                    {"name": "Floor Standing", "price": 12500, "quantity": 3000},
                    {"name": "VIP Seating", "price": 25000, "quantity": 500},
                    {"name": "Meet & Greet Package", "price": 150000, "quantity": 50}
                ]
            },
            {
                "name": "Romeo Santos - King of Bachata Returns",
                "description": "The King of Bachata returns to NYC! Romeo Santos performs his greatest hits plus new music. Featuring 'Propuesta Indecente', 'Eres Mía', and more. A night of romance and rhythm.",
                "venue": venue2,
                "event_date": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
                "doors_open": "19:30",
                "event_time": "21:00",
                "tiers": [
                    {"name": "Upper Bowl", "price": 5900, "quantity": 4000},
                    {"name": "Lower Bowl", "price": 9900, "quantity": 3000},
                    {"name": "Floor", "price": 15900, "quantity": 2000},
                    {"name": "VIP Package", "price": 35000, "quantity": 100}
                ]
            },
            {
                "name": "NYC Salsa Festival 2026",
                "description": "Three days of non-stop salsa! Featuring Marc Anthony, Willie Colón, and Gilberto Santa Rosa. Live bands, dance workshops, and authentic Latin cuisine. ¡Vamos a bailar!",
                "venue": venue4,
                "event_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
                "doors_open": "14:00",
                "event_time": "16:00",
                "tiers": [
                    {"name": "General Admission", "price": 8900, "quantity": 3000},
                    {"name": "VIP Access", "price": 17900, "quantity": 500},
                    {"name": "3-Day Pass", "price": 22900, "quantity": 1000}
                ]
            },
            {
                "name": "Brooklyn Food Truck Festival - Spring Edition",
                "description": "50+ food trucks, live music, and craft beer garden! Featuring cuisines from around the world: tacos, BBQ, ramen, falafel, lobster rolls, and more. Family-friendly with kids zone.",
                "venue": venue3,
                "event_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "doors_open": "11:00",
                "event_time": "12:00",
                "tiers": [
                    {"name": "General Admission", "price": 1500, "quantity": 1500},
                    {"name": "VIP Early Access", "price": 3500, "quantity": 200}
                ]
            },
            {
                "name": "Country Line Dancing Night - Boot Scootin' Boogie",
                "description": "Grab your cowboy boots! Free line dancing lessons 7-8pm, then dance the night away to country classics and modern hits. Cash bar and mechanical bull!",
                "venue": venue3,
                "event_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
                "doors_open": "19:00",
                "event_time": "19:30",
                "tiers": [
                    {"name": "General Admission", "price": 2500, "quantity": 800},
                    {"name": "Reserved Table (4 people)", "price": 15000, "quantity": 50}
                ]
            },
            {
                "name": "Blue Note Jazz All-Stars",
                "description": "An intimate evening of world-class jazz featuring Christian McBride, Cecile McLorin Salvant, and special guests. Two sets: 7pm and 9:30pm.",
                "venue": venue3,
                "event_date": (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d"),
                "doors_open": "18:30",
                "event_time": "19:00",
                "tiers": [
                    {"name": "Standing Room", "price": 4500, "quantity": 400},
                    {"name": "Reserved Seating", "price": 7500, "quantity": 300},
                    {"name": "VIP Table (4 seats)", "price": 40000, "quantity": 25}
                ]
            },
            {
                "name": "Travis Scott - Utopia World Tour",
                "description": "RAGE MODE ACTIVATED! Travis Scott brings the Utopia experience to NYC. Expect mind-blowing visuals, special effects, and non-stop energy. This is La Flame at his peak.",
                "venue": venue2,
                "event_date": (datetime.now() + timedelta(days=50)).strftime("%Y-%m-%d"),
                "doors_open": "19:00",
                "event_time": "21:00",
                "tiers": [
                    {"name": "General Admission", "price": 8900, "quantity": 6000},
                    {"name": "Floor GA", "price": 14900, "quantity": 4000},
                    {"name": "VIP Seating", "price": 29900, "quantity": 500},
                    {"name": "Cactus Jack VIP", "price": 99900, "quantity": 100}
                ]
            },
            {
                "name": "Summer Bachata Beach Party",
                "description": "Outdoor bachata festival with sand dance floor! Featuring Aventura reunion, Prince Royce, and Frank Reyes. Sunset sessions, beach vibes, and romantic rhythms all night long.",
                "venue": venue4,
                "event_date": (datetime.now() + timedelta(days=75)).strftime("%Y-%m-%d"),
                "doors_open": "17:00",
                "event_time": "18:00",
                "tiers": [
                    {"name": "Beach GA", "price": 6900, "quantity": 3000},
                    {"name": "Cabana Access", "price": 12900, "quantity": 500},
                    {"name": "VIP Lounge", "price": 25000, "quantity": 200}
                ]
            }
        ]

        created_events = []

        for event_data in demo_events:
            # Check if event already exists
            existing = db.query(Event).filter(
                Event.name == event_data["name"]
            ).first()

            if existing:
                print(f"⏭️  Event already exists: {event_data['name']}")
                continue

            # Create event
            event = Event(
                name=event_data["name"],
                description=event_data["description"],
                venue_id=event_data["venue"].id,
                event_date=event_data["event_date"],
                doors_open_time=event_data["doors_open"],
                event_time=event_data["event_time"],
                is_visible=True
            )
            db.add(event)
            db.flush()

            # Create ticket tiers
            for tier_data in event_data["tiers"]:
                tier = TicketTier(
                    event_id=event.id,
                    name=tier_data["name"],
                    price=tier_data["price"],
                    quantity_available=tier_data["quantity"],
                    quantity_sold=0
                )
                db.add(tier)

            created_events.append(event)
            print(f"✅ Created event: {event.name}")
            print(f"   📍 {event.venue.name}")
            print(f"   📅 {event.event_date}")
            print(f"   🎫 {len(event_data['tiers'])} ticket tiers")
            print()

        db.commit()

        # Summary
        print("=" * 80)
        print(f"✅ Demo Events Created: {len(created_events)}")
        print("=" * 80)
        print()
        print("📊 Summary:")
        print(f"   Total Events: {len(created_events)}")
        print(f"   Latin Music: {len([e for e in created_events if any(word in e.name.lower() for word in ['anuel', 'romeo', 'salsa', 'bachata'])])}")
        print(f"   Food Festivals: {len([e for e in created_events if 'food' in e.name.lower()])}")
        print(f"   Dance Events: {len([e for e in created_events if 'dancing' in e.name.lower()])}")
        print()
        print("🎯 Next Steps:")
        print("   1. View events: http://localhost:8000/events")
        print("   2. Test ad generation: python3 test_complete_ad_flow.py")
        print("   3. Generate campaigns via API: POST /api/ad-campaigns/generate/{event_id}")
        print()

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("Creating Demo Events...")
    print("=" * 80)
    print()
    create_demo_events()
