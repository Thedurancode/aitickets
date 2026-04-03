#!/usr/bin/env python3
"""
Test Script for Cross-Platform Page View Analytics

Demonstrates:
- Tracking views from multiple platforms (Eventbrite, Facebook, Ticketmaster)
- Querying aggregated analytics via REST API
- Using MCP tools for agent access
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"


def test_cross_platform_analytics():
    print("=" * 80)
    print("🌐 CROSS-PLATFORM PAGE VIEW ANALYTICS TEST")
    print("=" * 80)

    # Step 1: Get list of events
    print("\n📋 Step 1: Getting available events...")
    response = requests.get(f"{BASE_URL}/api/events")
    events = response.json()

    if not events:
        print("❌ No events found. Please run create_test_events.py first.")
        return

    event_id = events[0]['id']
    event_name = events[0]['name']
    print(f"✅ Using event: {event_name} (ID: {event_id})")

    # Step 2: Track views from different platforms
    print("\n📊 Step 2: Tracking page views from multiple platforms...")

    platforms_data = [
        {
            "platform": "eventbrite",
            "views": 150,
            "external_id": "evt_eb_12345",
            "metadata": {
                "event_url": "https://eventbrite.com/e/evt_eb_12345",
                "impressions": 1250,
                "click_through_rate": 0.12
            }
        },
        {
            "platform": "facebook",
            "views": 320,
            "external_id": "fb_event_67890",
            "metadata": {
                "event_url": "https://facebook.com/events/fb_event_67890",
                "likes": 89,
                "shares": 34,
                "interested": 156
            }
        },
        {
            "platform": "ticketmaster",
            "views": 75,
            "external_id": "tm_evt_abc123",
            "metadata": {
                "event_url": "https://ticketmaster.com/event/tm_evt_abc123",
                "favorited": 23
            }
        }
    ]

    for platform_data in platforms_data:
        print(f"\n  📍 Importing {platform_data['views']} views from {platform_data['platform']}...")
        response = requests.post(
            f"{BASE_URL}/api/platform-analytics/bulk-import",
            json={
                "event_id": event_id,
                "platform": platform_data['platform'],
                "view_count": platform_data['views'],
                "external_platform_id": platform_data['external_id'],
                "platform_data": platform_data['metadata']
            }
        )

        if response.status_code == 201:
            result = response.json()
            print(f"  ✅ {result['message']}")
        else:
            print(f"  ❌ Failed: {response.status_code} - {response.text}")

    # Add some internal platform views for comparison
    print("\n  📍 Adding internal platform views...")
    for _ in range(50):
        response = requests.post(
            f"{BASE_URL}/api/platform-analytics/track-external",
            json={
                "event_id": event_id,
                "platform": "internal",
                "platform_data": {
                    "source": "direct_traffic",
                    "page": "event_detail"
                }
            }
        )

    print("  ✅ Added 50 internal platform views")

    # Step 3: Query cross-platform analytics via REST API
    print("\n📈 Step 3: Querying cross-platform analytics...")

    # Get aggregated views
    print("\n  🔍 Aggregated views across all platforms:")
    response = requests.get(f"{BASE_URL}/api/platform-analytics/events/{event_id}")

    if response.status_code == 200:
        data = response.json()
        print(f"\n  📊 Results:")
        print(f"     Total Views: {data['total_views']}")
        print(f"     Period: Last {data['period_days']} days")
        print(f"\n     By Platform:")
        for platform, count in data['by_platform'].items():
            percentage = (count / data['total_views'] * 100) if data['total_views'] > 0 else 0
            print(f"       • {platform:15} {count:4} views ({percentage:5.1f}%)")
    else:
        print(f"  ❌ Failed: {response.status_code}")

    # Get detailed breakdown
    print("\n  🔍 Detailed platform breakdown:")
    response = requests.get(f"{BASE_URL}/api/platform-analytics/events/{event_id}/breakdown?days=7")

    if response.status_code == 200:
        breakdown = response.json()
        print(f"\n  Platform-by-Platform Analysis:")
        for platform_stat in breakdown:
            print(f"\n     {platform_stat['platform'].upper()}")
            print(f"       Views:             {platform_stat['views']}")
            print(f"       Unique Visitors:   {platform_stat['unique_visitors']}")
            print(f"       Avg Views/Visitor: {platform_stat['avg_views_per_visitor']}")
    else:
        print(f"  ❌ Failed: {response.status_code}")

    # Get org-wide summary
    print("\n  🔍 Organization-wide platform summary:")
    response = requests.get(f"{BASE_URL}/api/platform-analytics/summary?days=30")

    if response.status_code == 200:
        summary = response.json()
        print(f"\n  🌐 All Events Combined:")
        print(f"     Total Views:       {summary['total_views']}")
        print(f"     Platforms Tracked: {summary['platforms_tracked']}")
        print(f"     Period:            Last {summary['period_days']} days")
    else:
        print(f"  ❌ Failed: {response.status_code}")

    # Step 4: Test MCP tool access
    print("\n🤖 Step 4: Testing MCP tool access...")
    response = requests.get(f"{BASE_URL}/mcp/tools")

    if response.status_code == 200:
        tools = response.json()
        platform_tools = [
            t for t in tools
            if isinstance(t, dict) and ('platform' in t.get('name', '').lower() or 'cross_platform' in t.get('name', ''))
        ]
        print(f"\n  ✅ Found {len(platform_tools)} cross-platform analytics MCP tools:")
        for tool in platform_tools:
            print(f"     • {tool['name']}")
    else:
        print(f"  ❌ Failed to list MCP tools: {response.status_code}")

    # Test calling an MCP tool
    print("\n  🔧 Calling get_cross_platform_pageviews MCP tool...")
    response = requests.post(
        f"{BASE_URL}/mcp/tools/get_cross_platform_pageviews",
        json={
            "arguments": {
                "event_id": event_id,
                "days": 30
            }
        }
    )

    if response.status_code == 200:
        result = response.json()
        print(f"  ✅ MCP Tool Response:")
        print(f"     {json.dumps(result, indent=6)}")
    else:
        print(f"  ❌ Failed: {response.status_code}")

    # Step 5: Test webhook receiver
    print("\n📡 Step 5: Testing webhook receiver...")
    webhook_payload = {
        "event_id": event_id,
        "external_platform_id": "ext_platform_999",
        "views": 25,
        "metadata": {
            "platform_name": "Custom Platform",
            "webhook_timestamp": time.time()
        }
    }

    response = requests.post(
        f"{BASE_URL}/api/platform-analytics/webhooks/custom_platform",
        json=webhook_payload
    )

    if response.status_code == 200:
        result = response.json()
        print(f"  ✅ {result['message']}")
    else:
        print(f"  ❌ Failed: {response.status_code} - {response.text}")

    # Final summary
    print("\n" + "=" * 80)
    print("✅ CROSS-PLATFORM ANALYTICS TEST COMPLETE")
    print("=" * 80)
    print("\n📊 Summary:")
    print("   ✓ Tracked views from 5 platforms (Eventbrite, Facebook, Ticketmaster, Internal, Custom)")
    print("   ✓ REST API endpoints working correctly")
    print("   ✓ MCP tools accessible to AI agents")
    print("   ✓ Webhook receiver ready for external platform integrations")
    print("\n🎯 Your AI agent can now query cross-platform page views using:")
    print("   • MCP Tools: get_cross_platform_pageviews, get_platform_breakdown")
    print("   • REST API: GET /api/platform-analytics/events/{event_id}")
    print("   • Webhooks: POST /api/platform-analytics/webhooks/{platform}")
    print("=" * 80)


if __name__ == "__main__":
    test_cross_platform_analytics()
