"""Test script for Apple Wallet .pkpass generation."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_wallet.db")

import json
import zipfile
from io import BytesIO

# Test 1: generate_wallet_pass produces a valid ZIP
print("=" * 50)
print("Test 1: generate_wallet_pass returns a valid .pkpass (ZIP)")

from app.services.wallet_pass import generate_wallet_pass, is_wallet_configured

pass_bytes = generate_wallet_pass(
    event_name="Jazz Night",
    event_date="2026-03-15",
    event_time="20:00",
    venue_name="The Blue Note",
    venue_address="123 Jazz Ave",
    attendee_name="John Smith",
    tier_name="VIP",
    ticket_id=42,
    qr_token="abc123token",
)

assert isinstance(pass_bytes, bytes), "Should return bytes"
assert len(pass_bytes) > 0, "Should not be empty"

# Verify it's a valid ZIP
zf = zipfile.ZipFile(BytesIO(pass_bytes))
names = zf.namelist()
print(f"  ZIP contains: {names}")

assert "pass.json" in names, "Missing pass.json"
assert "manifest.json" in names, "Missing manifest.json"
assert "icon.png" in names, "Missing icon.png"
assert "icon@2x.png" in names, "Missing icon@2x.png"
assert "icon@3x.png" in names, "Missing icon@3x.png"
assert "logo.png" in names, "Missing logo.png"
assert "logo@2x.png" in names, "Missing logo@2x.png"
print("PASS: ZIP contains all required files")

# Test 2: pass.json has correct content
print("\n" + "=" * 50)
print("Test 2: pass.json contains correct event data")

pass_data = json.loads(zf.read("pass.json"))

assert pass_data["formatVersion"] == 1, "formatVersion should be 1"
assert pass_data["description"] == "Ticket for Jazz Night"
assert pass_data["serialNumber"] == "ticket-42"

event_ticket = pass_data["eventTicket"]

# Primary field = event name
primary = event_ticket["primaryFields"][0]
assert primary["value"] == "Jazz Night", f"Expected 'Jazz Night', got '{primary['value']}'"

# Secondary fields = date and time
secondary = event_ticket["secondaryFields"]
assert secondary[0]["value"] == "2026-03-15"
assert secondary[1]["value"] == "20:00"

# Auxiliary fields = venue and tier
aux = event_ticket["auxiliaryFields"]
assert aux[0]["value"] == "The Blue Note"
assert aux[1]["value"] == "VIP"

# Back fields = attendee, ticket id, address
back = event_ticket["backFields"]
assert back[0]["value"] == "John Smith"
assert back[1]["value"] == "#42"
assert back[2]["value"] == "123 Jazz Ave"

print("PASS: pass.json has correct event, venue, attendee, tier data")

# Test 3: QR barcode URL
print("\n" + "=" * 50)
print("Test 3: QR barcode contains validation URL")

barcode = pass_data["barcode"]
assert "abc123token" in barcode["message"], f"QR should contain token, got: {barcode['message']}"
assert barcode["format"] == "PKBarcodeFormatQR"

barcodes = pass_data["barcodes"]
assert len(barcodes) == 1
assert "abc123token" in barcodes[0]["message"]
print("PASS: QR barcode URL contains ticket token")

# Test 4: manifest.json has SHA1 hashes for all files
print("\n" + "=" * 50)
print("Test 4: manifest.json contains SHA1 hashes")

import hashlib
manifest = json.loads(zf.read("manifest.json"))

for filename in ["pass.json", "icon.png", "icon@2x.png", "icon@3x.png", "logo.png", "logo@2x.png"]:
    assert filename in manifest, f"manifest.json missing entry for {filename}"
    # Verify hash is correct
    file_data = zf.read(filename)
    expected_hash = hashlib.sha1(file_data).hexdigest()
    assert manifest[filename] == expected_hash, f"Hash mismatch for {filename}"

print("PASS: manifest.json has valid SHA1 hashes for all files")

# Test 5: doors_open_time optional field
print("\n" + "=" * 50)
print("Test 5: doors_open_time adds auxiliary field when provided")

pass_with_doors = generate_wallet_pass(
    event_name="Concert",
    event_date="2026-04-01",
    event_time="21:00",
    venue_name="Arena",
    venue_address="456 Main St",
    attendee_name="Jane Doe",
    tier_name="General Admission",
    ticket_id=99,
    qr_token="doors-test-token",
    doors_open_time="19:30",
)

zf2 = zipfile.ZipFile(BytesIO(pass_with_doors))
pass_data2 = json.loads(zf2.read("pass.json"))
aux2 = pass_data2["eventTicket"]["auxiliaryFields"]
doors_field = [f for f in aux2 if f["key"] == "doors"]
assert len(doors_field) == 1, "Should have doors field"
assert doors_field[0]["value"] == "19:30"
print("PASS: doors_open_time appears in auxiliary fields")

# Verify it's NOT present when omitted
aux_no_doors = event_ticket["auxiliaryFields"]
doors_field_absent = [f for f in aux_no_doors if f["key"] == "doors"]
assert len(doors_field_absent) == 0, "Should NOT have doors field when not provided"
print("PASS: doors_open_time omitted when not provided")

# Test 6: is_wallet_configured returns False without certs
print("\n" + "=" * 50)
print("Test 6: is_wallet_configured() returns False without certs")

configured = is_wallet_configured()
assert configured is False, f"Expected False without certs, got {configured}"
print("PASS: is_wallet_configured() is False (no certs set)")

# Test 7: Unsigned pass has no signature file (dev mode)
print("\n" + "=" * 50)
print("Test 7: Unsigned pass has no signature file")

assert "signature" not in names, "Unsigned pass should not contain 'signature' file"
print("PASS: No signature file in unsigned (dev) pass")

# Test 8: relevantDate formatting
print("\n" + "=" * 50)
print("Test 8: relevantDate ISO format")

assert "relevantDate" in pass_data
assert pass_data["relevantDate"].startswith("2026-03-15T20:00")
print(f"  relevantDate: {pass_data['relevantDate']}")
print("PASS: relevantDate is ISO-formatted")

# Test 9: API endpoint (full integration test)
print("\n" + "=" * 50)
print("Test 9: GET /api/tickets/{id}/wallet endpoint")

from app.database import init_db, SessionLocal
from app.models import Venue, Event, TicketTier, EventGoer, Ticket, TicketStatus
import uuid

init_db()
db = SessionLocal()

venue = Venue(name="Test Venue", address="789 Test Blvd")
db.add(venue)
db.commit()
db.refresh(venue)

event = Event(
    venue_id=venue.id,
    name="Wallet Test Event",
    event_date="2026-05-01",
    event_time="19:00",
)
db.add(event)
db.commit()
db.refresh(event)

tier = TicketTier(
    event_id=event.id,
    name="Standard",
    price=2500,
    quantity_available=100,
)
db.add(tier)
db.commit()
db.refresh(tier)

customer = EventGoer(name="Test User", email=f"wallet-test-{uuid.uuid4().hex[:8]}@example.com")
db.add(customer)
db.commit()
db.refresh(customer)

qr_token = str(uuid.uuid4())
ticket = Ticket(
    ticket_tier_id=tier.id,
    event_goer_id=customer.id,
    status=TicketStatus.PAID,
    qr_code_token=qr_token,
)
db.add(ticket)
db.commit()
db.refresh(ticket)
ticket_id = ticket.id
tier_id = tier.id
customer_id = customer.id
db.close()

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 9a: Valid ticket returns .pkpass
response = client.get(f"/api/tickets/{ticket_id}/wallet")
assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
assert response.headers["content-type"] == "application/vnd.apple.pkpass"
assert f"ticket-{ticket_id}.pkpass" in response.headers["content-disposition"]

# Verify the response is a valid ZIP with pass.json
resp_zf = zipfile.ZipFile(BytesIO(response.content))
resp_pass = json.loads(resp_zf.read("pass.json"))
assert resp_pass["eventTicket"]["primaryFields"][0]["value"] == "Wallet Test Event"
print("PASS: GET /api/tickets/{id}/wallet returns valid .pkpass")

# 9b: Non-existent ticket returns 404
response_404 = client.get("/api/tickets/99999/wallet")
assert response_404.status_code == 404, f"Expected 404, got {response_404.status_code}"
print("PASS: Non-existent ticket returns 404")

# 9c: Pending ticket returns 400
db2 = SessionLocal()
pending_ticket = Ticket(
    ticket_tier_id=tier_id,
    event_goer_id=customer_id,
    status=TicketStatus.PENDING,
    qr_code_token=str(uuid.uuid4()),
)
db2.add(pending_ticket)
db2.commit()
db2.refresh(pending_ticket)
pending_ticket_id = pending_ticket.id
db2.close()

response_400 = client.get(f"/api/tickets/{pending_ticket_id}/wallet")
assert response_400.status_code == 400, f"Expected 400 for pending ticket, got {response_400.status_code}"
print("PASS: Pending ticket returns 400")

# 9d: Checked-in ticket still works
db3 = SessionLocal()
checkedin_ticket = Ticket(
    ticket_tier_id=tier_id,
    event_goer_id=customer_id,
    status=TicketStatus.CHECKED_IN,
    qr_code_token=str(uuid.uuid4()),
)
db3.add(checkedin_ticket)
db3.commit()
db3.refresh(checkedin_ticket)
checkedin_ticket_id = checkedin_ticket.id
db3.close()

response_checkedin = client.get(f"/api/tickets/{checkedin_ticket_id}/wallet")
assert response_checkedin.status_code == 200, f"Expected 200 for checked_in ticket, got {response_checkedin.status_code}"
print("PASS: Checked-in ticket returns valid .pkpass")

# Cleanup
try:
    os.remove("test_wallet.db")
except OSError:
    pass

print("\n" + "=" * 50)
print("ALL 9 TESTS PASSED!")
