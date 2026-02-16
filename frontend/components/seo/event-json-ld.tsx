import type { EventDetail } from "@/types/api";
import { SITE_URL } from "@/lib/constants";

interface EventJsonLdProps {
  event: EventDetail;
}

export function EventJsonLd({ event }: EventJsonLdProps) {
  const startDateTime = `${event.event_date}T${event.event_time}`;

  const offers = event.ticket_tiers.map((tier) => ({
    "@type": "Offer" as const,
    name: tier.name,
    price: (tier.price / 100).toFixed(2),
    priceCurrency: "USD",
    availability:
      tier.tickets_remaining > 0
        ? "https://schema.org/InStock"
        : "https://schema.org/SoldOut",
    url: `${SITE_URL}/events/${event.id}`,
  }));

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Event",
    name: event.name,
    ...(event.description && { description: event.description }),
    startDate: startDateTime,
    ...(event.doors_open_time && {
      doorTime: `${event.event_date}T${event.doors_open_time}`,
    }),
    eventStatus: "https://schema.org/EventScheduled",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: {
      "@type": "Place",
      name: event.venue.name,
      address: {
        "@type": "PostalAddress",
        streetAddress: event.venue.address,
      },
    },
    ...(event.image_url && { image: [event.image_url] }),
    offers:
      offers.length === 1
        ? offers[0]
        : { "@type": "AggregateOffer", offers },
    url: `${SITE_URL}/events/${event.id}`,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
