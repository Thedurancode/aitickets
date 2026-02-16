import type { Metadata } from "next";
import { fetchEvent } from "@/lib/api-server";
import { SITE_URL } from "@/lib/constants";
import { EventJsonLd } from "@/components/seo/event-json-ld";
import { BreadcrumbJsonLd } from "@/components/seo/breadcrumb-json-ld";
import EventDetailContent from "./event-detail-content";

type Props = {
  params: { id: string };
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const event = await fetchEvent(Number(params.id));

  if (!event) {
    return { title: "Event Not Found" };
  }

  const title = event.name;
  const description =
    event.description?.slice(0, 160) ||
    `Get tickets for ${event.name} at ${event.venue.name}`;
  const url = `${SITE_URL}/events/${event.id}`;

  return {
    title,
    description,
    openGraph: {
      title: event.name,
      description,
      url,
      type: "website",
      ...(event.image_url && {
        images: [
          {
            url: event.image_url,
            width: 1200,
            height: 630,
            alt: event.name,
          },
        ],
      }),
    },
    twitter: {
      card: event.image_url ? "summary_large_image" : "summary",
      title: event.name,
      description,
      ...(event.image_url && { images: [event.image_url] }),
    },
    alternates: {
      canonical: url,
    },
  };
}

export default async function EventDetailPage({ params }: Props) {
  const event = await fetchEvent(Number(params.id));

  return (
    <>
      {event && (
        <>
          <EventJsonLd event={event} />
          <BreadcrumbJsonLd
            items={[
              { name: "Home", href: "/" },
              { name: "Events", href: "/events" },
              { name: event.name },
            ]}
          />
        </>
      )}
      <EventDetailContent />
    </>
  );
}
