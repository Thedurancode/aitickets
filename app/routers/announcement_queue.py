"""
In-memory announcement queue for voice agent notifications.
When a promoter updates an event via the admin page, announcements are
queued here and prepended to the voice agent's next response.
"""
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

# Global queue with auto-eviction at 50 entries
_announcements: deque = deque(maxlen=50)

EXPIRATION_MINUTES = 30


def queue_announcement(event_id: int, event_name: str, action: str):
    """Add an announcement to the queue."""
    _announcements.append({
        "event_id": event_id,
        "event_name": event_name,
        "action": action,
        "timestamp": datetime.utcnow(),
        "expires": datetime.utcnow() + timedelta(minutes=EXPIRATION_MINUTES),
    })


def get_pending_announcements(limit: int = 3) -> list[dict]:
    """Get pending announcements that haven't expired."""
    now = datetime.utcnow()

    # Evict expired items from front of queue
    while _announcements and _announcements[0]["expires"] < now:
        _announcements.popleft()

    return list(_announcements)[:limit]


def clear_announcements():
    """Clear all announcements (called after voice agent reads them)."""
    _announcements.clear()


def format_announcement_speech(announcements: list[dict]) -> Optional[str]:
    """Format announcements as natural speech for the voice agent."""
    if not announcements:
        return None

    if len(announcements) == 1:
        a = announcements[0]
        action_text = _action_to_speech(a["action"])
        minutes_ago = int((datetime.utcnow() - a["timestamp"]).total_seconds() / 60)
        time_text = "just now" if minutes_ago < 1 else f"{minutes_ago} minute{'s' if minutes_ago != 1 else ''} ago"
        return f"Heads up — the promoter {action_text} {a['event_name']} {time_text}."

    # Multiple updates — group by event
    event_names = list(set(a["event_name"] for a in announcements))
    if len(event_names) == 1:
        return f"Heads up — the promoter made {len(announcements)} updates to {event_names[0]}."

    return f"Heads up — the promoter updated {len(event_names)} events recently."


def _action_to_speech(action: str) -> str:
    """Convert action code to natural speech fragment."""
    return {
        "details_updated": "updated the details for",
        "image_uploaded": "uploaded a new image for",
        "visibility_changed": "changed the visibility of",
    }.get(action, "updated")
