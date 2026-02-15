"use client";

import { EventCard, EventCardSkeleton } from "./event-card";
import { StaggerContainer } from "@/components/layout/page-transition";
import type { EventWithVenue } from "@/types/api";

interface EventGridProps {
  events: EventWithVenue[];
  isLoading?: boolean;
}

export function EventGrid({ events, isLoading }: EventGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <EventCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground text-lg">No events found</p>
        <p className="text-muted-foreground text-sm mt-2">
          Try adjusting your filters or check back later
        </p>
      </div>
    );
  }

  return (
    <StaggerContainer
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      staggerDelay={0.1}
    >
      {events.map((event) => (
        <EventCard key={event.id} event={event} />
      ))}
    </StaggerContainer>
  );
}
