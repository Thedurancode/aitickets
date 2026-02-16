import type { EventDetail, EventWithVenue } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchEvent(id: number): Promise<EventDetail | null> {
  try {
    const res = await fetch(`${API_BASE}/api/events/${id}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchEvents(): Promise<EventWithVenue[]> {
  try {
    const res = await fetch(`${API_BASE}/api/events`, {
      next: { revalidate: 600 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}
