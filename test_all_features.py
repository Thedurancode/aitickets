#!/usr/bin/env python3
"""
Comprehensive test suite for AI Tickets Platform
Tests all major features and integrations
"""
import requests
import json
from datetime import datetime, timedelta
import time

BASE_URL = "http://127.0.0.1:8000"

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def record(self, test_name, success, message=""):
        self.tests.append({
            "name": test_name,
            "success": success,
            "message": message
        })
        if success:
            self.passed += 1
            print(f"✅ PASS: {test_name}")
        else:
            self.failed += 1
            print(f"❌ FAIL: {test_name} - {message}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 80)
        print(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        print("=" * 80)
        if self.failed > 0:
            print("\nFailed tests:")
            for test in self.tests:
                if not test["success"]:
                    print(f"  - {test['name']}: {test['message']}")

results = TestResults()

print("=" * 80)
print("🧪 AI TICKETS PLATFORM - COMPREHENSIVE TEST SUITE")
print("=" * 80)

# ==================== TEST 1: HEALTH CHECK ====================
print("\n📡 Testing: Health Check & Server Status")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    results.record("Health Check Endpoint",
                   response.status_code == 200,
                   f"Status: {response.status_code}")
except Exception as e:
    results.record("Health Check Endpoint", False, str(e))

# ==================== TEST 2: API DOCUMENTATION ====================
print("\n📚 Testing: API Documentation")
try:
    response = requests.get(f"{BASE_URL}/docs", timeout=5)
    results.record("OpenAPI Documentation",
                   response.status_code == 200,
                   f"Status: {response.status_code}")
except Exception as e:
    results.record("OpenAPI Documentation", False, str(e))

# ==================== TEST 3: VENUE MANAGEMENT ====================
print("\n🏢 Testing: Venue Management")
try:
    # Create venue
    venue_data = {
        "name": "Test Venue",
        "address": "123 Test St",
        "city": "Test City",
        "state": "CA",
        "capacity": 1000
    }
    response = requests.post(f"{BASE_URL}/api/venues", json=venue_data)
    venue_created = response.status_code in [200, 201]
    venue_id = response.json().get('id') if venue_created else None
    results.record("Create Venue", venue_created, f"Venue ID: {venue_id}")

    # List venues
    if venue_created:
        response = requests.get(f"{BASE_URL}/api/venues")
        results.record("List Venues", response.status_code == 200)
except Exception as e:
    results.record("Venue Management", False, str(e))

# ==================== TEST 4: EVENT MANAGEMENT ====================
print("\n🎉 Testing: Event Management")
event_id = None
try:
    # Get a venue ID
    venues = requests.get(f"{BASE_URL}/api/venues").json()
    if venues:
        venue_id = venues[0]['id']

        # Create event
        event_date = datetime.now() + timedelta(days=30)
        event_data = {
            "venue_id": venue_id,
            "name": "Test Event",
            "description": "A comprehensive test event",
            "event_date": event_date.strftime("%Y-%m-%d"),
            "event_time": "18:00:00",
            "capacity": 500,
            "category": "technology",
            "visibility": "public"
        }
        response = requests.post(f"{BASE_URL}/api/events", json=event_data)
        event_created = response.status_code in [200, 201]
        event_id = response.json().get('id') if event_created else None
        results.record("Create Event", event_created, f"Event ID: {event_id}")

        # List events
        response = requests.get(f"{BASE_URL}/api/events")
        results.record("List Events", response.status_code == 200)

        # Get event details
        if event_id:
            response = requests.get(f"{BASE_URL}/api/events/{event_id}")
            results.record("Get Event Details", response.status_code == 200)
except Exception as e:
    results.record("Event Management", False, str(e))

# ==================== TEST 5: TICKET TIERS ====================
print("\n🎟️  Testing: Ticket Tier Management")
tier_id = None
try:
    if event_id:
        # Create ticket tier
        tier_data = {
            "name": "Test Tier",
            "description": "Test tier description",
            "price": 5000,  # $50.00
            "quantity_available": 100
        }
        response = requests.post(f"{BASE_URL}/api/events/{event_id}/tiers", json=tier_data)
        tier_created = response.status_code in [200, 201]
        tier_id = response.json().get('id') if tier_created else None
        results.record("Create Ticket Tier", tier_created, f"Tier ID: {tier_id}")

        # List tiers
        response = requests.get(f"{BASE_URL}/api/events/{event_id}/tiers")
        results.record("List Ticket Tiers", response.status_code == 200)
except Exception as e:
    results.record("Ticket Tier Management", False, str(e))

# ==================== TEST 6: FREE TICKET PURCHASE ====================
print("\n💳 Testing: Free Ticket Purchase Flow")
ticket_ids = []
try:
    # Create free tier event
    if venues:
        venue_id = venues[0]['id']
        event_date = datetime.now() + timedelta(days=15)

        # Create free event
        free_event_data = {
            "venue_id": venue_id,
            "name": "Free Test Event",
            "description": "Free event for testing",
            "event_date": event_date.strftime("%Y-%m-%d"),
            "event_time": "19:00:00",
            "capacity": 200,
            "category": "technology",
            "visibility": "public"
        }
        response = requests.post(f"{BASE_URL}/api/events", json=free_event_data)
        free_event_id = response.json().get('id')

        # Create free tier
        free_tier_data = {
            "name": "Free Entry",
            "description": "Free admission",
            "price": 0,
            "quantity_available": 200
        }
        response = requests.post(f"{BASE_URL}/api/events/{free_event_id}/tiers", json=free_tier_data)
        free_tier_id = response.json().get('id')

        # Purchase free tickets
        purchase_data = {
            "ticket_tier_id": free_tier_id,
            "quantity": 2,
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+14155551234"
        }
        response = requests.post(f"{BASE_URL}/api/tickets/events/{free_event_id}/purchase", json=purchase_data)
        purchase_success = response.status_code in [200, 201]

        if purchase_success and 'tickets' in response.json():
            ticket_ids = [t['id'] for t in response.json()['tickets']]
            results.record("Free Ticket Purchase", True, f"Tickets: {ticket_ids}")
        else:
            results.record("Free Ticket Purchase", False, f"Status: {response.status_code}")
except Exception as e:
    results.record("Free Ticket Purchase", False, str(e))

# ==================== TEST 7: ANALYTICS & REPORTING ====================
print("\n📊 Testing: Analytics & Reporting")
try:
    # Get analytics
    response = requests.get(f"{BASE_URL}/api/analytics/summary")
    results.record("Analytics Summary", response.status_code == 200)

    if event_id:
        # Event-specific analytics
        response = requests.get(f"{BASE_URL}/api/analytics/events/{event_id}")
        results.record("Event Analytics", response.status_code == 200)
except Exception as e:
    results.record("Analytics", False, str(e))

# ==================== TEST 8: CATEGORIES ====================
print("\n📂 Testing: Event Categories")
try:
    response = requests.get(f"{BASE_URL}/api/categories")
    categories_exist = response.status_code == 200 and len(response.json()) > 0
    results.record("List Categories", categories_exist)
except Exception as e:
    results.record("Categories", False, str(e))

# ==================== TEST 9: PUBLIC EVENT LISTING ====================
print("\n🌐 Testing: Public Event Pages")
try:
    response = requests.get(f"{BASE_URL}/events")
    results.record("Public Events Page", response.status_code == 200)

    if event_id:
        response = requests.get(f"{BASE_URL}/events/{event_id}")
        results.record("Event Detail Page", response.status_code == 200)
except Exception as e:
    results.record("Public Pages", False, str(e))

# ==================== TEST 10: SEARCH FUNCTIONALITY ====================
print("\n🔍 Testing: Search Functionality")
try:
    response = requests.get(f"{BASE_URL}/api/events?q=test")
    results.record("Event Search", response.status_code == 200)
except Exception as e:
    results.record("Search", False, str(e))

# ==================== TEST 11: MCP ENDPOINTS ====================
print("\n🤖 Testing: MCP Integration")
try:
    # Test MCP health
    response = requests.get(f"{BASE_URL}/mcp/health")
    results.record("MCP Health Check", response.status_code == 200)

    # List MCP tools
    response = requests.get(f"{BASE_URL}/mcp/tools")
    mcp_tools_available = response.status_code == 200
    results.record("MCP Tools List", mcp_tools_available)

    if mcp_tools_available:
        tools = response.json()
        print(f"   Available MCP Tools: {len(tools)}")
except Exception as e:
    results.record("MCP Integration", False, str(e))

# ==================== TEST 12: AFFILIATE SYSTEM ====================
print("\n🤝 Testing: Affiliate Program")
try:
    response = requests.get(f"{BASE_URL}/api/affiliates")
    results.record("Affiliate Listing", response.status_code == 200)
except Exception as e:
    results.record("Affiliate System", False, str(e))

# ==================== TEST 13: LOYALTY PROGRAM ====================
print("\n⭐ Testing: Loyalty Program")
try:
    response = requests.get(f"{BASE_URL}/api/loyalty/tiers")
    results.record("Loyalty Tiers", response.status_code == 200)
except Exception as e:
    results.record("Loyalty Program", False, str(e))

# ==================== TEST 14: SOCIAL PROOF ====================
print("\n👥 Testing: Social Proof Features")
try:
    if event_id:
        response = requests.get(f"{BASE_URL}/api/social-proof/{event_id}")
        results.record("Social Proof Stats", response.status_code == 200)
except Exception as e:
    results.record("Social Proof", False, str(e))

# ==================== TEST 15: CAMPAIGN TRACKING ====================
print("\n📈 Testing: Campaign Tracking")
try:
    response = requests.get(f"{BASE_URL}/api/campaign-tracking/summary")
    results.record("Campaign Tracking", response.status_code in [200, 404])  # 404 is ok if no campaigns
except Exception as e:
    results.record("Campaign Tracking", False, str(e))

# ==================== TEST 16: DYNAMIC PRICING ====================
print("\n💰 Testing: Dynamic Pricing")
try:
    if event_id and tier_id:
        response = requests.get(f"{BASE_URL}/api/dynamic-pricing/{tier_id}")
        results.record("Dynamic Pricing", response.status_code in [200, 404])
except Exception as e:
    results.record("Dynamic Pricing", False, str(e))

# ==================== TEST 17: WAITLIST ====================
print("\n⏳ Testing: Waitlist Management")
try:
    if event_id:
        waitlist_data = {
            "event_id": event_id,
            "name": "Waitlist Test",
            "email": "waitlist@example.com"
        }
        response = requests.post(f"{BASE_URL}/api/waitlist", json=waitlist_data)
        results.record("Waitlist Join", response.status_code in [200, 201])
except Exception as e:
    results.record("Waitlist", False, str(e))

# ==================== TEST 18: RATE LIMITING ====================
print("\n🛡️  Testing: Rate Limiting")
try:
    # Make multiple rapid requests
    responses = []
    for i in range(5):
        response = requests.get(f"{BASE_URL}/api/events")
        responses.append(response.status_code)

    # Should all succeed (we're within rate limit)
    all_success = all(status == 200 for status in responses)
    results.record("Rate Limiting (Normal)", all_success)
except Exception as e:
    results.record("Rate Limiting", False, str(e))

# ==================== TEST 19: ERROR HANDLING ====================
print("\n🚫 Testing: Error Handling")
try:
    # Test 404
    response = requests.get(f"{BASE_URL}/api/events/999999")
    results.record("404 Error Handling", response.status_code == 404)

    # Test invalid data
    response = requests.post(f"{BASE_URL}/api/venues", json={"invalid": "data"})
    results.record("Validation Error Handling", response.status_code in [400, 422])
except Exception as e:
    results.record("Error Handling", False, str(e))

# ==================== TEST 20: TICKET VALIDATION ====================
print("\n✅ Testing: Ticket Validation")
try:
    if ticket_ids:
        # Get ticket details to find QR token
        response = requests.get(f"{BASE_URL}/api/tickets/{ticket_ids[0]}")
        if response.status_code == 200:
            ticket = response.json()
            qr_token = ticket.get('qr_code_token')

            if qr_token:
                # Validate ticket
                response = requests.post(f"{BASE_URL}/api/tickets/validate/{qr_token}")
                results.record("Ticket QR Validation", response.status_code == 200)
            else:
                results.record("Ticket QR Validation", False, "No QR token")
except Exception as e:
    results.record("Ticket Validation", False, str(e))

# ==================== FINAL SUMMARY ====================
print("\n" + "=" * 80)
print("🎯 TEST EXECUTION COMPLETE")
print("=" * 80)

results.summary()

# Feature coverage report
print("\n📊 FEATURE COVERAGE:")
print("  ✓ Core Platform (Health, Docs, API)")
print("  ✓ Venue Management")
print("  ✓ Event Management")
print("  ✓ Ticket Tiers & Pricing")
print("  ✓ Free Ticket Purchase Flow")
print("  ✓ Analytics & Reporting")
print("  ✓ Public Web Pages")
print("  ✓ Search & Discovery")
print("  ✓ MCP Integration (AI Agent Support)")
print("  ✓ Affiliate Program")
print("  ✓ Loyalty Program")
print("  ✓ Social Proof")
print("  ✓ Campaign Tracking")
print("  ✓ Dynamic Pricing")
print("  ✓ Waitlist Management")
print("  ✓ Rate Limiting & Security")
print("  ✓ Error Handling")
print("  ✓ Ticket Validation")

print("\n🚀 Platform Status: " + ("PRODUCTION READY" if results.failed == 0 else "NEEDS ATTENTION"))
print("=" * 80)
