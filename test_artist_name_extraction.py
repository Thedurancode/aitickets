#!/usr/bin/env python
"""
Test artist name extraction from event names.
"""

from app.services.event_research_agent import extract_artist_name


def test_artist_name_extraction():
    """Test various event name formats."""
    test_cases = [
        ("Bad Bunny - Most Wanted Tour", "Bad Bunny"),
        ("Bad Bunny Summer Fest", "Bad Bunny"),
        ("Drake Live at Madison Square Garden", "Drake"),
        ("Taylor Swift Eras Tour", "Taylor Swift"),
        ("Bad Bunny Festival 2024", "Bad Bunny"),
        ("Beyoncé Renaissance World Tour", "Beyoncé Renaissance"),
        ("The Weeknd After Hours Tour", "The Weeknd After Hours"),
        ("Post Malone @ Barclays Center", "Post Malone"),
        ("Dua Lipa Future Nostalgia Tour", "Dua Lipa Future Nostalgia"),
        ("Bad Bunny", "Bad Bunny"),  # Just the name
        ("Bruno Mars Live", "Bruno Mars"),
        ("Ed Sheeran Mathematics Tour", "Ed Sheeran Mathematics"),
        ("Bad Bunny Concert", "Bad Bunny"),
        ("Kendrick Lamar - The Big Steppers Tour", "Kendrick Lamar"),
    ]

    print("\n" + "="*60)
    print("ARTIST NAME EXTRACTION TEST")
    print("="*60 + "\n")

    passed = 0
    failed = 0

    for event_name, expected in test_cases:
        result = extract_artist_name(event_name)
        is_correct = result == expected
        status = "✅" if is_correct else "❌"

        if is_correct:
            passed += 1
        else:
            failed += 1

        print(f"{status} Event: '{event_name}'")
        print(f"   Expected: '{expected}'")
        print(f"   Got: '{result}'")
        if not is_correct:
            print(f"   ⚠️ MISMATCH!")
        print()

    print("-"*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("-"*60)

    # Special focus on Bad Bunny cases
    print("\n🎤 Bad Bunny Event Variations:")
    bad_bunny_events = [
        "Bad Bunny - Most Wanted Tour",
        "Bad Bunny Summer Fest",
        "Bad Bunny Festival 2024",
        "Bad Bunny Live at Prudential Center",
        "Bad Bunny Concert",
        "Bad Bunny",
    ]

    for event in bad_bunny_events:
        extracted = extract_artist_name(event)
        print(f"  '{event}' → '{extracted}'")

    print("\n" + "="*60)

    return failed == 0


if __name__ == "__main__":
    success = test_artist_name_extraction()
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed - review extraction logic")
    exit(0 if success else 1)