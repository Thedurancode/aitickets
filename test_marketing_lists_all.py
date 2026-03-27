"""Test Marketing Lists with All Customers"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.marketing_lists import create_marketing_list, preview_marketing_list


def test_all_customers_list():
    """Test creating a list that matches all customers."""
    db = SessionLocal()

    print("🎯 Testing Marketing List with All Customers")
    print("=" * 60)
    print()

    # Create a list with minimal filters
    print("Creating 'All Opted-In Customers' list...")
    all_customers_list = create_marketing_list(
        db=db,
        name="All Email Opt-In Customers",
        description="All customers who opted in to email",
        segment_filters={"email_opt_in": True},
    )

    print(f"  ✅ Created: {all_customers_list['name']}")
    print(f"     Filters: {all_customers_list['filter_description']}")
    print(f"     Count: {all_customers_list['current_count']} customers")
    print()

    # Preview with sample customers
    if all_customers_list['current_count'] > 0:
        print("Previewing first 5 customers...")
        preview = preview_marketing_list(db=db, list_id=all_customers_list['id'], limit=5)

        for i, customer in enumerate(preview['sample_customers'], 1):
            print(f"  {i}. {customer['name']} ({customer['email']})")
            print(f"     Events attended: {customer['total_events_attended']}")
            print(f"     Total spent: ${customer['total_spent_cents']/100:.2f}")
            print(f"     VIP: {'Yes' if customer['is_vip'] else 'No'}")
            print()

    db.close()


if __name__ == "__main__":
    test_all_customers_list()
