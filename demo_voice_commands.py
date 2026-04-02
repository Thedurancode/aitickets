#!/usr/bin/env python3
"""
Voice Command Demo Script

Demonstrates MCP-powered voice commands working with the AI Tickets platform.
Run this to see actual examples of natural language queries being processed.
"""
import requests
import json
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:8000"
API_TOKEN = "your-jwt-token-here"  # Get this from /api/auth/login

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}


def voice_command(text: str) -> dict:
    """Send a voice command and get response."""
    print(f"\n🎤 Voice Input: \"{text}\"")
    print("─" * 80)

    response = requests.post(
        f"{BASE_URL}/api/voice/command",
        params={"text": text},
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Intent: {data['intent']}")
        print(f"🎯 Confidence: {data['confidence']*100:.0f}%")
        print(f"\n💬 Response:")
        print(f"   {data['natural_language_response']}")
        print(f"\n📊 Data:")
        print(json.dumps(data['result'], indent=2))
        return data
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return {}


def main():
    """Run voice command demonstrations."""

    print("=" * 80)
    print("🎙️  AI TICKETS VOICE COMMAND DEMO")
    print("=" * 80)

    # Example 1: Check ticket sales
    voice_command("How many tickets did I sell today?")

    # Example 2: Get revenue stats
    voice_command("What's my total revenue?")

    # Example 3: List events
    voice_command("Show me my upcoming events")

    # Example 4: Affiliate stats
    voice_command("How much commission have I earned from my affiliate link?")

    # Example 5: Loyalty program
    voice_command("What's my loyalty tier and how many points do I have?")

    # Example 6: Group buying
    voice_command("Show me my active group purchases")

    # Example 7: General stats
    voice_command("Give me an overview of my account")

    # Example 8: Code search (MCP powered)
    voice_command("Find the payment webhook handlers")

    print("\n" + "=" * 80)
    print("✨ Demo Complete!")
    print("=" * 80)


# ==================== EXAMPLE RESPONSES ====================

def show_example_responses():
    """Show what the actual responses look like."""

    print("\n" + "=" * 80)
    print("📋 EXAMPLE VOICE COMMAND RESPONSES")
    print("=" * 80)

    examples = [
        {
            "voice_input": "How many tickets sold today?",
            "natural_response": "You've sold 47 tickets worth $4,230.00 in the selected period.",
            "structured_data": {
                "type": "sales_report",
                "total_tickets": 47,
                "total_revenue": 423000,
                "revenue_formatted": "$4,230.00",
                "by_event": {
                    "AI Summit 2026": {"count": 30, "revenue": 297000},
                    "Tech Meetup": {"count": 17, "revenue": 126000}
                }
            }
        },
        {
            "voice_input": "What's my affiliate commission?",
            "natural_response": "Your affiliate code is TECH2026. You've earned $1,250.00 with $450.00 pending payout.",
            "structured_data": {
                "type": "affiliate_stats",
                "code": "TECH2026",
                "status": "active",
                "total_clicks": 523,
                "total_conversions": 34,
                "commission_earned": 125000,
                "commission_pending": 45000,
                "commission_paid": 80000
            }
        },
        {
            "voice_input": "Show my loyalty points",
            "natural_response": "You're in the GOLD tier with 4,350 points available.",
            "structured_data": {
                "type": "loyalty_info",
                "tier": "gold",
                "available_points": 4350,
                "lifetime_points": 8920,
                "next_tier": "platinum",
                "points_to_next_tier": 1080
            }
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n[Example {i}]")
        print(f"🎤 Voice: \"{example['voice_input']}\"")
        print(f"💬 Response: {example['natural_response']}")
        print(f"📊 Data: {json.dumps(example['structured_data'], indent=2)}")
        print("─" * 80)


# ==================== MCP-POWERED EXAMPLES ====================

def show_mcp_integration():
    """Show how MCP enhances voice commands."""

    print("\n" + "=" * 80)
    print("🔌 MCP-POWERED VOICE COMMANDS")
    print("=" * 80)

    mcp_examples = [
        {
            "voice": "Find all payment webhook handlers",
            "mcp_action": "smart_search(query='webhook payment handler')",
            "result": "Found 3 handlers in app/routers/stripe_webhooks.py:\n"
                     "  - handle_payment_success() - Line 100\n"
                     "  - handle_payment_failed() - Line 158\n"
                     "  - handle_refund() - Line 194"
        },
        {
            "voice": "Show me the structure of the affiliate router",
            "mcp_action": "smart_outline(file='app/routers/affiliates.py')",
            "result": "Outline of app/routers/affiliates.py:\n"
                     "  Classes: AffiliateApplication, AffiliateUpdate, AffiliateResponse\n"
                     "  Functions: apply_as_affiliate, get_affiliate_profile, update_affiliate_profile,\n"
                     "             get_referral_stats, track_referral_click, request_payout"
        },
        {
            "voice": "Did we already implement group buying?",
            "mcp_action": "search_memory(query='group buying implementation')",
            "result": "Yes! Group buying was implemented on April 2, 2026.\n"
                     "  File: app/routers/group_buying.py\n"
                     "  Features: Split payments, row-level locking, automatic ticket creation\n"
                     "  Status: Production ready with security fixes applied"
        },
        {
            "voice": "How does the loyalty tier system work?",
            "mcp_action": "smart_unfold(file='app/routers/loyalty.py', symbol='_check_tier_upgrade')",
            "result": "def _check_tier_upgrade(account: LoyaltyAccount) -> LoyaltyTier:\n"
                     "    points = account.lifetime_points\n"
                     "    if points >= 10000: return LoyaltyTier.PLATINUM\n"
                     "    elif points >= 3000: return LoyaltyTier.GOLD\n"
                     "    elif points >= 1000: return LoyaltyTier.SILVER\n"
                     "    else: return LoyaltyTier.BRONZE"
        }
    ]

    for i, example in enumerate(mcp_examples, 1):
        print(f"\n[MCP Example {i}]")
        print(f"🎤 Voice: \"{example['voice']}\"")
        print(f"🔧 MCP Call: {example['mcp_action']}")
        print(f"📄 Result:\n{example['result']}")
        print("─" * 80)


# ==================== INTERACTIVE DEMO ====================

def interactive_demo():
    """Run an interactive voice command session."""

    print("\n" + "=" * 80)
    print("🎙️  INTERACTIVE VOICE COMMAND SESSION")
    print("=" * 80)
    print("\nType your voice commands (or 'quit' to exit):\n")

    while True:
        command = input("🎤 You: ").strip()

        if command.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break

        if not command:
            continue

        # In production, this would call the actual API
        print(f"   [Processing: {command}...]")
        print(f"   💬 This would call: POST /api/voice/command?text={command}")
        print()


if __name__ == "__main__":
    print("\n🎯 Choose demo mode:")
    print("  1. Show example responses")
    print("  2. Show MCP integration")
    print("  3. Interactive demo (requires running server)")
    print("  4. All of the above")

    choice = input("\nYour choice (1-4): ").strip()

    if choice == "1":
        show_example_responses()
    elif choice == "2":
        show_mcp_integration()
    elif choice == "3":
        interactive_demo()
    elif choice == "4":
        show_example_responses()
        show_mcp_integration()
        print("\n[Skipping interactive demo - run separately with option 3]")
    else:
        print("\n✅ Running all examples...")
        show_example_responses()
        show_mcp_integration()

    print("\n" + "=" * 80)
    print("📚 NEXT STEPS:")
    print("=" * 80)
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Get your JWT token: POST /api/auth/login")
    print("3. Try voice commands: POST /api/voice/command?text=YOUR_COMMAND")
    print("4. Add Whisper API for real voice-to-text")
    print("5. Add text-to-speech for voice responses")
    print("=" * 80 + "\n")
