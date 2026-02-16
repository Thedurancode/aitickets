import type { MetadataRoute } from "next";
import { fetchEvents } from "@/lib/api-server";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL || "https://ai-tickets.fly.dev";

  const staticPages: MetadataRoute.Sitemap = [
    {
      url: `${siteUrl}/events`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
  ];

  const allEvents = await fetchEvents();
  const events = allEvents.filter((e) => e.is_visible !== false);
  const eventPages: MetadataRoute.Sitemap = events.map((event) => ({
    url: `${siteUrl}/events/${event.id}`,
    lastModified: new Date(event.created_at),
    changeFrequency: "weekly" as const,
    priority: 0.8,
  }));

  return [...staticPages, ...eventPages];
}
