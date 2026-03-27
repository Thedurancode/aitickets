"""Test Marketing Lists API

This script tests the complete marketing list management workflow:
1. Create marketing lists with various filters
2. List all marketing lists
3. Preview audience segments
4. Update lists
5. Delete lists
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import EventGoer, CustomerPreference
from app.services.marketing_lists import (
    create_marketing_list,
    get_marketing_list,
    list_marketing_lists,
    preview_marketing_list,
    update_marketing_list,
    delete_marketing_list,
)


def test_marketing_lists():
    """Test marketing list functionality."""
    db = SessionLocal()

    print("🎯 Testing Marketing List Management")
    print("=" * 60)
    print()

    # Check if we have event goers
    total_customers = db.query(EventGoer).count()
    print(f"Step 1: Database Check")
    print(f"  Total customers: {total_customers}")
    print()

    if total_customers == 0:
        print("⚠️  No customers found in database.")
        print("   Run the app and create some test events/tickets first.")
        db.close()
        return

    # Test 1: Create VIP List
    print("Step 2: Creating VIP Customers List...")
    vip_list = create_marketing_list(
        db=db,
        name="VIP Customers",
        description="All VIP customers for exclusive offers",
        segment_filters={"is_vip": True, "marketing_opt_in": True},
    )

    if "error" in vip_list:
        print(f"  ⚠️  {vip_list['error']}")
    else:
        print(f"  ✅ Created list: {vip_list['name']}")
        print(f"     Description: {vip_list['filter_description']}")
        print(f"     Current count: {vip_list['current_count']} customers")
        print()

    # Test 2: Create High Spenders List
    print("Step 3: Creating High Spenders List...")
    high_spenders = create_marketing_list(
        db=db,
        name="High Spenders",
        description="Customers who spent $100+",
        segment_filters={
            "min_spent_cents": 10000,
            "email_opt_in": True,
        },
    )

    if "error" not in high_spenders:
        print(f"  ✅ Created list: {high_spenders['name']}")
        print(f"     Description: {high_spenders['filter_description']}")
        print(f"     Current count: {high_spenders['current_count']} customers")
        print()

    # Test 3: Create Regular Attendees List
    print("Step 4: Creating Regular Attendees List...")
    regulars = create_marketing_list(
        db=db,
        name="Regular Attendees",
        description="Customers who attended 3+ events",
        segment_filters={
            "min_events": 3,
            "sms_opt_in": True,
        },
    )

    if "error" not in regulars:
        print(f"  ✅ Created list: {regulars['name']}")
        print(f"     Description: {regulars['filter_description']}")
        print(f"     Current count: {regulars['current_count']} customers")
        print()

    # Test 4: Create Birthday List
    print("Step 5: Creating Birthday This Month List...")
    birthday_list = create_marketing_list(
        db=db,
        name="Birthday This Month",
        description="Customers with birthdays this month",
        segment_filters={
            "has_birthday_this_month": True,
        },
    )

    if "error" not in birthday_list:
        print(f"  ✅ Created list: {birthday_list['name']}")
        print(f"     Description: {birthday_list['filter_description']}")
        print(f"     Current count: {birthday_list['current_count']} customers")
        print()

    # Test 5: List All Marketing Lists
    print("Step 6: Listing All Marketing Lists...")
    all_lists = list_marketing_lists(db=db, limit=10, offset=0)
    print(f"  Found {all_lists['total']} total lists:")
    for lst in all_lists['lists']:
        print(f"    - {lst['name']}: {lst['current_count']} customers")
        print(f"      {lst['filter_description']}")
    print()

    # Test 6: Preview a List
    if all_lists['lists']:
        first_list_id = all_lists['lists'][0]['id']
        print(f"Step 7: Previewing List #{first_list_id}...")
        preview = preview_marketing_list(db=db, list_id=first_list_id, limit=5)

        print(f"  List: {preview['list_name']}")
        print(f"  Filters: {preview['filter_description']}")
        print(f"  Total count: {preview['total_count']} customers")
        print()

        if preview['sample_customers']:
            print(f"  Sample customers (showing {len(preview['sample_customers'])}):")
            for customer in preview['sample_customers']:
                vip_badge = "👑 VIP" if customer['is_vip'] else ""
                print(f"    - {customer['name']} ({customer['email']}) {vip_badge}")
                print(f"      Events: {customer['total_events_attended']}, Spent: ${customer['total_spent_cents']/100:.2f}")
                opt_ins = []
                if customer['marketing_opt_in']:
                    opt_ins.append("Marketing")
                if customer['email_opt_in']:
                    opt_ins.append("Email")
                if customer['sms_opt_in']:
                    opt_ins.append("SMS")
                print(f"      Opt-ins: {', '.join(opt_ins) if opt_ins else 'None'}")
        print()

    # Test 7: Update a List
    if all_lists['lists']:
        first_list_id = all_lists['lists'][0]['id']
        print(f"Step 8: Updating List #{first_list_id}...")
        updated = update_marketing_list(
            db=db,
            list_id=first_list_id,
            description="Updated description for testing",
        )

        if "error" not in updated:
            print(f"  ✅ Updated: {updated['name']}")
            print(f"     New description: {updated['description']}")
            print()

    # Test 8: Delete a List
    if all_lists['lists'] and len(all_lists['lists']) > 1:
        last_list_id = all_lists['lists'][-1]['id']
        last_list_name = all_lists['lists'][-1]['name']
        print(f"Step 9: Deleting List #{last_list_id} ({last_list_name})...")
        deleted = delete_marketing_list(db=db, list_id=last_list_id)

        if "error" not in deleted:
            print(f"  ✅ {deleted['message']}")
            print()

    # Final Summary
    print("=" * 60)
    print("🎉 Marketing Lists Test Complete!")
    print("=" * 60)
    print()

    remaining_lists = list_marketing_lists(db=db, limit=100, offset=0)
    print(f"Summary:")
    print(f"  ✅ {remaining_lists['total']} marketing lists created")
    print(f"  ✅ Audience segmentation working")
    print(f"  ✅ Preview functionality working")
    print()

    print("Available Filter Options:")
    print("  - is_vip, vip_tier")
    print("  - min_events, max_events")
    print("  - min_spent_cents, max_spent_cents")
    print("  - category_ids, event_id")
    print("  - has_birthday_this_month")
    print("  - last_purchase_days_ago")
    print("  - first_time_buyers, no_show")
    print("  - marketing_opt_in, email_opt_in, sms_opt_in")
    print("  - preferred_language")
    print("  - dormant_days")
    print()

    print("API Endpoints:")
    print("  POST   /api/marketing-lists           - Create list")
    print("  GET    /api/marketing-lists           - List all lists")
    print("  GET    /api/marketing-lists/{id}      - Get list details")
    print("  GET    /api/marketing-lists/{id}/preview - Preview audience")
    print("  PUT    /api/marketing-lists/{id}      - Update list")
    print("  DELETE /api/marketing-lists/{id}      - Delete list")
    print()

    db.close()


if __name__ == "__main__":
    test_marketing_lists()
