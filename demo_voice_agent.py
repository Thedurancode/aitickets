#!/usr/bin/env python3
"""
Demo Script: Enhanced Voice Agent Capabilities

Shows the powerful natural language understanding and context awareness
of the enhanced voice agent system.
"""

import requests
import json
import time
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

# Test session ID for continuity
SESSION_ID = f"demo_session_{datetime.now().timestamp()}"


def send_voice_command(text, emotion=None):
    """Send a voice command to the enhanced agent."""
    print(f"\n🎤 You: '{text}'")
    if emotion:
        print(f"   (Detected emotion: {emotion})")

    response = requests.post(
        f"{BASE_URL}/api/voice-agent/command",
        json={
            "text": text,
            "session_id": SESSION_ID,
            "audio_emotion": emotion
        }
    )

    if response.status_code == 200:
        data = response.json()
        print(f"\n🤖 Agent: {data['text']}")
        print(f"   Tone: {data['emotional_tone']}")

        if data.get('suggestions'):
            print(f"\n   📝 Suggestions:")
            for i, suggestion in enumerate(data['suggestions'][:3], 1):
                print(f"      {i}. {suggestion}")

        if data.get('proactive_insights'):
            print(f"\n   💡 Proactive Insights:")
            for insight in data['proactive_insights']:
                print(f"      - {insight['message']} (urgency: {insight['urgency']})")

        if data.get('alerts'):
            print(f"\n   ⚠️ Alerts:")
            for alert in data['alerts']:
                print(f"      - {alert['message']}")

        return data
    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   {response.text}")
        return None


def demo_conversation():
    """Demonstrate multi-turn conversation with context awareness."""

    print("=" * 60)
    print("ENHANCED VOICE AGENT DEMO")
    print("Showing Natural Language Understanding & Context Awareness")
    print("=" * 60)

    # Conversation 1: Casual greeting and sales check
    print("\n\n📍 Conversation 1: Natural Dialogue")
    print("-" * 40)

    send_voice_command("Hey! How's everything going with my events?", emotion="casual")
    time.sleep(2)

    send_voice_command("Show me today's sales", emotion="curious")
    time.sleep(2)

    send_voice_command("What about revenue?")  # Context-aware follow-up
    time.sleep(2)

    # Conversation 2: Urgent situation handling
    print("\n\n📍 Conversation 2: Urgent Situation")
    print("-" * 40)

    send_voice_command("I need help NOW! My event is in 3 days and tickets aren't selling!", emotion="urgent")
    time.sleep(2)

    send_voice_command("Yes, boost the marketing immediately!", emotion="urgent")
    time.sleep(2)

    # Conversation 3: Confused user support
    print("\n\n📍 Conversation 3: Empathetic Support")
    print("-" * 40)

    send_voice_command("I don't understand why my ads aren't working?", emotion="confused")
    time.sleep(2)

    send_voice_command("Can you help me fix them?", emotion="frustrated")
    time.sleep(2)

    # Conversation 4: Celebration moment
    print("\n\n📍 Conversation 4: Celebrating Success")
    print("-" * 40)

    send_voice_command("Did we hit 1000 tickets sold yet?!", emotion="excited")
    time.sleep(2)

    send_voice_command("That's amazing! Thank you for your help!", emotion="excited")
    time.sleep(2)

    # Conversation 5: Complex multi-step task
    print("\n\n📍 Conversation 5: Multi-Step Task")
    print("-" * 40)

    send_voice_command("I want to create a new summer concert event")
    time.sleep(2)

    send_voice_command("The name is Summer Vibes Festival")
    time.sleep(2)

    send_voice_command("June 15th at Madison Square Garden")
    time.sleep(2)

    send_voice_command("Set tickets from $50 to $150")
    time.sleep(2)

    # Conversation 6: Learning from context
    print("\n\n📍 Conversation 6: Context Memory")
    print("-" * 40)

    send_voice_command("How's that event doing?")  # Refers to previously discussed event
    time.sleep(2)

    send_voice_command("Compare it to last week")  # Contextual comparison
    time.sleep(2)


def demo_proactive_features():
    """Demonstrate proactive monitoring and suggestions."""

    print("\n\n" + "=" * 60)
    print("PROACTIVE INTELLIGENCE DEMO")
    print("=" * 60)

    # Check for alerts
    print("\n\n📍 Proactive Monitoring")
    print("-" * 40)

    response = send_voice_command("Any alerts I should know about?")

    if response and response.get('alerts'):
        print("\n🚨 System detected these issues proactively:")
        for alert in response['alerts']:
            print(f"   - {alert['message']}")
            if alert.get('action'):
                print(f"     Suggested action: {alert['action']}")


def demo_voice_analytics():
    """Show voice interaction analytics."""

    print("\n\n" + "=" * 60)
    print("VOICE ANALYTICS")
    print("=" * 60)

    response = requests.get(
        f"{BASE_URL}/api/voice-agent/analytics",
        params={"days": 7}
    )

    if response.status_code == 200:
        analytics = response.json()
        print(f"\n📊 Last 7 Days Analytics:")
        print(f"   Total interactions: {analytics['total_interactions']}")
        print(f"   Unique users: {analytics['unique_users']}")
        print(f"   Average session: {analytics['average_session_length']}")
        print(f"   Satisfaction score: {analytics['satisfaction_score']}/5.0")

        print(f"\n   Top Commands:")
        for intent in analytics['top_intents'][:3]:
            print(f"      - {intent['intent']}: {intent['percentage']}%")

        print(f"\n   Emotional Distribution:")
        for emotion, percent in analytics['emotional_distribution'].items():
            print(f"      - {emotion}: {percent}%")


if __name__ == "__main__":
    print("\n🚀 Starting Enhanced Voice Agent Demo\n")

    # Run conversation demos
    demo_conversation()

    # Show proactive features
    demo_proactive_features()

    # Display analytics
    demo_voice_analytics()

    print("\n\n✅ Demo Complete!")
    print("\nThe enhanced voice agent provides:")
    print("  ✓ Natural language understanding")
    print("  ✓ Multi-turn conversations with context")
    print("  ✓ Emotional intelligence and tone adaptation")
    print("  ✓ Proactive insights and alerts")
    print("  ✓ Smart follow-up suggestions")
    print("  ✓ Voice analytics and learning")
    print("\n🎯 This creates a truly intelligent, conversational experience!")