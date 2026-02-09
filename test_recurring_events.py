"""Test script for recurring events feature."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_recurring.db")

import sys
import asyncio
from datetime import datetime, date, timedelta

# Test 1: Migration and model
print("=" * 50)
print("Test 1: Migration and series_id column")
from app.database import init_db, SessionLocal, engine
from app.models import Event, Venue, TicketTier, EventCategory
from sqlalchemy import inspect as sa_inspect

init_db()
inspector = sa_inspect(engine)
columns = [c["name"] for c in inspector.get_columns("events")]
assert "series_id" in columns, f"series_id not in columns: {columns}"
print("PASS: series_id column exists in events table")

# Test 2: Create venue for testing
print("\n" + "=" * 50)
print("Test 2: Create test venue")
db = SessionLocal()
venue = Venue(name="Test Taco Spot", address="123 Taco St")
db.add(venue)
db.commit()
db.refresh(venue)
print(f"PASS: Created venue id={venue.id}")
db.close()

# Test 3: Test the MCP handler - weekly
print("\n" + "=" * 50)
print("Test 3: create_recurring_event MCP tool (weekly, 4 months)")
from mcp_server.server import _execute_tool

async def run_weekly():
    db2 = SessionLocal()
    result = await _execute_tool("create_recurring_event", {
        "venue_id": venue.id,
        "name": "Taco Tuesday",
        "event_time": "19:00",
        "day_of_week": "tuesday",
        "frequency": "weekly",
        "duration_months": 4,
        "tier_name": "Free Admission",
        "tier_price": 0,
        "tier_quantity": 100,
    }, db2)
    db2.close()
    return result

result = asyncio.run(run_weekly())

if "error" in result:
    print(f"FAIL: {result['error']}")
    sys.exit(1)

print(f"  events_created: {result['events_created']}")
print(f"  series_id: {result['series_id']}")
print(f"  first_date: {result['first_date']}")
print(f"  last_date: {result['last_date']}")

# Verify count (~17 for 4 months of Tuesdays)
assert result["events_created"] >= 15, f"Expected >= 15 events, got {result['events_created']}"
assert result["events_created"] <= 18, f"Expected <= 18 events, got {result['events_created']}"
print(f"PASS: Created {result['events_created']} weekly events")

# Verify all events are Tuesdays
for evt in result["events"]:
    d = datetime.strptime(evt["event_date"], "%Y-%m-%d").date()
    assert d.weekday() == 1, f"Expected Tuesday (1), got weekday {d.weekday()} for {evt['event_date']}"
print("PASS: All events are on Tuesdays")

# Verify all events share same series_id
for evt in result["events"]:
    assert evt["series_id"] == result["series_id"], "series_id mismatch"
print("PASS: All events share same series_id")

# Verify each event has a ticket tier
db3 = SessionLocal()
for event_id in result["event_ids"]:
    tiers = db3.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    assert len(tiers) == 1, f"Expected 1 tier for event {event_id}, got {len(tiers)}"
    assert tiers[0].name == "Free Admission"
    assert tiers[0].price == 0
    assert tiers[0].quantity_available == 100
db3.close()
print("PASS: Each event has 1 'Free Admission' tier with 100 tickets at $0")

# Test 4: Biweekly frequency
print("\n" + "=" * 50)
print("Test 4: create_recurring_event (biweekly, 3 months)")

async def run_biweekly():
    db4 = SessionLocal()
    result = await _execute_tool("create_recurring_event", {
        "venue_id": venue.id,
        "name": "Biweekly Bingo",
        "event_time": "20:00",
        "day_of_week": "friday",
        "frequency": "biweekly",
        "duration_months": 3,
        "tier_name": "VIP",
        "tier_price": 2500,
        "tier_quantity": 50,
    }, db4)
    db4.close()
    return result

result_bw = asyncio.run(run_biweekly())
assert "error" not in result_bw, f"Error: {result_bw.get('error')}"
assert result_bw["events_created"] >= 5, f"Expected >= 5 biweekly events, got {result_bw['events_created']}"
assert result_bw["events_created"] <= 7, f"Expected <= 7 biweekly events, got {result_bw['events_created']}"
print(f"PASS: Created {result_bw['events_created']} biweekly events")

# Verify all events are Fridays
for evt in result_bw["events"]:
    d = datetime.strptime(evt["event_date"], "%Y-%m-%d").date()
    assert d.weekday() == 4, f"Expected Friday (4), got weekday {d.weekday()} for {evt['event_date']}"
print("PASS: All biweekly events are on Fridays")

# Test 5: Monthly frequency
print("\n" + "=" * 50)
print("Test 5: create_recurring_event (monthly, 6 months)")

async def run_monthly():
    db5 = SessionLocal()
    result = await _execute_tool("create_recurring_event", {
        "venue_id": venue.id,
        "name": "Monthly Mixer",
        "event_time": "18:00",
        "day_of_week": "saturday",
        "frequency": "monthly",
        "duration_months": 6,
    }, db5)
    db5.close()
    return result

result_mo = asyncio.run(run_monthly())
assert "error" not in result_mo, f"Error: {result_mo.get('error')}"
assert result_mo["events_created"] >= 5, f"Expected >= 5 monthly events, got {result_mo['events_created']}"
assert result_mo["events_created"] <= 7, f"Expected <= 7 monthly events, got {result_mo['events_created']}"
print(f"PASS: Created {result_mo['events_created']} monthly events")

# Verify all events are Saturdays
for evt in result_mo["events"]:
    d = datetime.strptime(evt["event_date"], "%Y-%m-%d").date()
    assert d.weekday() == 5, f"Expected Saturday (5), got weekday {d.weekday()} for {evt['event_date']}"
print("PASS: All monthly events are on Saturdays")

# Test 6: Error cases
print("\n" + "=" * 50)
print("Test 6: Error handling")

async def run_errors():
    db6 = SessionLocal()
    # Bad venue
    r1 = await _execute_tool("create_recurring_event", {
        "venue_id": 99999,
        "name": "Bad Event",
        "event_time": "19:00",
        "day_of_week": "monday",
    }, db6)
    assert "error" in r1, "Should error for bad venue"
    print("  PASS: Bad venue returns error")

    # Bad day
    r2 = await _execute_tool("create_recurring_event", {
        "venue_id": venue.id,
        "name": "Bad Day",
        "event_time": "19:00",
        "day_of_week": "funday",
    }, db6)
    assert "error" in r2, "Should error for bad day_of_week"
    print("  PASS: Bad day_of_week returns error")

    db6.close()

asyncio.run(run_errors())
print("PASS: Error handling works")

# Test 7: Voice speech response
print("\n" + "=" * 50)
print("Test 7: Speech response generation")
from app.routers.mcp import _generate_speech_response
speech = _generate_speech_response("create_recurring_event", {
    "events_created": 17,
    "event_name": "Taco Tuesday",
    "day_of_week": "tuesday",
    "first_date": "2026-02-10",
    "last_date": "2026-06-02",
    "tier_quantity": 100,
    "tier_price_cents": 0,
})
print(f"  Speech: {speech}")
assert "17" in speech, "Should mention event count"
assert "Taco Tuesday" in speech, "Should mention event name"
assert "Tuesday" in speech, "Should mention day"
assert "free" in speech.lower(), "Should mention free"
print("PASS: Speech response is correct")

# Test 7b: Time formatting in speech (standard time, not military)
print("\nTest 7b: Time formatting (12-hour)")
from app.routers.mcp import _format_time
assert _format_time("19:00") == "7 PM", f"Expected '7 PM', got '{_format_time('19:00')}'"
assert _format_time("09:30") == "9:30 AM", f"Expected '9:30 AM', got '{_format_time('09:30')}'"
assert _format_time("00:00") == "12 AM", f"Expected '12 AM', got '{_format_time('00:00')}'"
assert _format_time("12:00") == "12 PM", f"Expected '12 PM', got '{_format_time('12:00')}'"
assert _format_time("13:45") == "1:45 PM", f"Expected '1:45 PM', got '{_format_time('13:45')}'"
print("PASS: _format_time converts to 12-hour correctly")

speech2 = _generate_speech_response("create_event", {
    "name": "Jazz Night",
    "event_date": "2026-03-15",
    "event_time": "20:00",
})
print(f"  create_event speech: {speech2}")
assert "8 PM" in speech2, f"Should say '8 PM', got: {speech2}"
print("PASS: create_event speech uses 12-hour time")

# Test 8: Default parameters (no frequency, duration, tier specified)
print("\n" + "=" * 50)
print("Test 8: Default parameters")

async def run_defaults():
    db7 = SessionLocal()
    result = await _execute_tool("create_recurring_event", {
        "venue_id": venue.id,
        "name": "Default Event",
        "event_time": "21:00",
        "day_of_week": "wednesday",
    }, db7)
    db7.close()
    return result

result_def = asyncio.run(run_defaults())
assert "error" not in result_def, f"Error: {result_def.get('error')}"
assert result_def["frequency"] == "weekly", f"Default frequency should be weekly, got {result_def['frequency']}"
assert result_def["tier_name"] == "General Admission", f"Default tier should be General Admission, got {result_def['tier_name']}"
assert result_def["tier_price_cents"] == 0, f"Default price should be 0, got {result_def['tier_price_cents']}"
assert result_def["tier_quantity"] == 100, f"Default quantity should be 100, got {result_def['tier_quantity']}"
print(f"PASS: Defaults work (weekly, 3 months, General Admission, free, 100 qty)")
print(f"  Created {result_def['events_created']} events from {result_def['first_date']} to {result_def['last_date']}")

# Cleanup
import os
try:
    os.remove("test_recurring.db")
except OSError:
    pass

print("\n" + "=" * 50)
print(f"ALL 8 TESTS PASSED!")
