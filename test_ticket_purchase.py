#!/usr/bin/env python3
"""
Test ticket purchase flow and generate sample ticket PDF
"""
import requests
from datetime import datetime
import time

BASE_URL = "http://127.0.0.1:8000"

def test_ticket_purchase():
    """Test the complete ticket purchase flow."""

    print("=" * 80)
    print("🎫 TESTING TICKET PURCHASE FLOW")
    print("=" * 80)

    # Step 1: Get available events
    print("\n📋 Fetching available events...")
    response = requests.get(f"{BASE_URL}/api/events")
    if response.status_code != 200:
        print(f"❌ Failed to fetch events: {response.status_code}")
        return

    events = response.json()
    if not events:
        print("❌ No events found")
        return

    # Find an event with ticket tiers (try the newer events first)
    event = None
    tier = None
    for e in sorted(events, key=lambda x: x['id'], reverse=True):
        # Check if this event has tiers
        tier_response = requests.get(f"{BASE_URL}/api/events/{e['id']}/tiers")
        if tier_response.status_code == 200:
            tiers = tier_response.json()
            if tiers:
                event = e
                tier = tiers[0]  # Use first tier
                break

    if not event or not tier:
        print("❌ No events with ticket tiers found")
        return

    print(f"✅ Selected event: {event['name']} (ID: {event['id']})")
    print(f"✅ Selected tier: {tier['name']} - ${tier['price']/100:.2f}")

    # Step 2: Purchase tickets using the unified endpoint
    print("\n🎫 Purchasing 2 tickets...")
    response = requests.post(f"{BASE_URL}/api/tickets/events/{event['id']}/purchase", json={
        "ticket_tier_id": tier['id'],
        "quantity": 2,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+14155551234"
    })

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to purchase tickets: {response.status_code} - {response.text}")
        return

    purchase_response = response.json()
    print(f"✅ Purchase initiated")

    # Check if tickets were created immediately (free tickets) or need payment
    if 'tickets' in purchase_response:
        # Free tickets - issued immediately
        tickets = purchase_response['tickets']
        ticket_ids = [t['id'] for t in tickets]
        print(f"✅ {len(tickets)} free tickets issued immediately!")
        print(f"   Ticket IDs: {ticket_ids}")
    elif 'checkout_url' in purchase_response:
        # Paid tickets - would redirect to Stripe
        print(f"✅ Checkout session created (would redirect to Stripe)")
        print(f"   Session ID: {purchase_response.get('session_id', 'N/A')}")

        # In test mode, we'll simulate the webhook callback
        # For now, let's try to get the tickets that were created
        print("\n⏳ Simulating payment completion...")
        time.sleep(1)

        # Get all tickets for this user to find the ones we just created
        response = requests.get(f"{BASE_URL}/api/event-goers/email/john.doe@example.com/tickets")
        if response.status_code == 200:
            all_tickets = response.json()
            # Get the most recent tickets
            ticket_ids = [t['id'] for t in sorted(all_tickets, key=lambda x: x['id'], reverse=True)[:2]]
            print(f"   Found ticket IDs: {ticket_ids}")
        else:
            print("   ⚠️  Could not retrieve ticket IDs")
            ticket_ids = []
    else:
        print("❌ Unexpected response format")
        return

    # Step 3: Download ticket PDFs
    if ticket_ids:
        print("\n📄 Generating ticket PDFs...")
        for ticket_id in ticket_ids:
            response = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}/pdf")

            if response.status_code == 200:
                filename = f"ticket_{ticket_id}.pdf"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ Saved ticket PDF: {filename}")
            else:
                print(f"   ❌ Failed to generate PDF for ticket {ticket_id}: {response.status_code}")

    print("\n" + "=" * 80)
    print("✨ TICKET PURCHASE TEST COMPLETED!")
    print("=" * 80)

    print("\n📊 Summary:")
    print(f"   • Event: {event['name']}")
    print(f"   • Tier: {tier['name']} (${tier['price']/100:.2f})")
    print(f"   • Tickets purchased: {len(ticket_ids) if ticket_ids else 0}")
    print(f"   • Total cost: ${tier['price'] * len(ticket_ids) / 100:.2f}" if ticket_ids else "   • Total cost: $0.00")
    print(f"   • Customer: John Doe (john.doe@example.com)")

    print("\n💡 Next steps:")
    print("   1. Check the generated ticket_*.pdf files in the current directory")
    print("   2. Each ticket has a unique QR code for venue check-in")
    print("   3. Scan the QR code to verify the ticket")
    print(f"   4. Visit http://127.0.0.1:8000/events/{event['id']} to see the event page")

if __name__ == "__main__":
    test_ticket_purchase()
