"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { Calendar, Clock, MapPin, DoorOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatTime } from "@/lib/utils";
import { VideoEmbed } from "@/components/events/video-embed";
import type { EventDetail } from "@/types/api";

interface EventHeroProps {
  event: EventDetail;
}

export function EventHero({ event }: EventHeroProps) {
  const eventDateTime = `${event.event_date}T${event.event_time}`;
  const doorsTime = event.doors_open_time
    ? `${event.event_date}T${event.doors_open_time}`
    : null;

  return (
    <div className="relative">
      {/* Hero Image */}
      <div className="relative aspect-[4/3] sm:aspect-[16/9] md:aspect-[2/1] overflow-hidden rounded-2xl">
        {event.image_url ? (
          <motion.div
            layoutId={`event-image-${event.id}`}
            className="absolute inset-0"
          >
            <Image
              src={event.image_url}
              alt={event.name}
              fill
              className="object-cover"
              priority
              sizes="100vw"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent" />
            <div className="absolute inset-0 bg-gradient-to-r from-background/80 to-transparent" />
          </motion.div>
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/5 to-background flex items-center justify-center">
            <div className="p-8 rounded-full bg-primary/10">
              <Calendar className="h-24 w-24 text-primary/30" />
            </div>
          </div>
        )}

        {/* Categories overlay */}
        <div className="absolute top-4 left-4 flex gap-2 flex-wrap">
          {event.categories.map((category) => (
            <Badge
              key={category.id}
              className="backdrop-blur-md bg-black/40 border-white/10 text-white"
            >
              {category.name}
            </Badge>
          ))}
        </div>
      </div>

      {/* Event Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-4 sm:mt-6 lg:mt-8 space-y-4 sm:space-y-6"
      >
        <motion.h1
          layoutId={`event-title-${event.id}`}
          className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-foreground"
        >
          {event.name}
        </motion.h1>

        <div className="flex flex-wrap gap-2 sm:gap-4">
          <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl bg-card/50 border border-white/5 text-sm sm:text-base">
            <Calendar className="h-4 w-4 sm:h-5 sm:w-5 text-primary flex-shrink-0" />
            <span className="text-foreground">{formatDate(eventDateTime)}</span>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl bg-card/50 border border-white/5 text-sm sm:text-base">
            <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-primary flex-shrink-0" />
            <span className="text-foreground">{formatTime(eventDateTime)}</span>
          </div>
          {doorsTime && (
            <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl bg-card/50 border border-white/5 text-sm sm:text-base">
              <DoorOpen className="h-4 w-4 sm:h-5 sm:w-5 text-primary flex-shrink-0" />
              <span className="text-foreground">Doors: {formatTime(doorsTime)}</span>
            </div>
          )}
        </div>

        <div className="flex items-start gap-2 sm:gap-3 p-3 sm:p-4 rounded-xl bg-card/50 border border-white/5">
          <MapPin className="h-4 w-4 sm:h-5 sm:w-5 text-primary flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="font-medium text-foreground text-sm sm:text-base">{event.venue.name}</p>
            <p className="text-xs sm:text-sm text-muted-foreground truncate">{event.venue.address}</p>
          </div>
        </div>

        {event.description && (
          <div className="pt-4 sm:pt-6 border-t border-white/5">
            <h2 className="font-semibold mb-2 sm:mb-3 text-base sm:text-lg">About this event</h2>
            <p className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
              {event.description}
            </p>
          </div>
        )}

        {event.promo_video_url && (
          <div className="pt-4 sm:pt-6 border-t border-white/5">
            <h2 className="font-semibold mb-3 text-lg">Event Preview</h2>
            <VideoEmbed url={event.promo_video_url} title={event.name} />
          </div>
        )}
      </motion.div>
    </div>
  );
}

export function EventHeroSkeleton() {
  return (
    <div>
      <div className="relative aspect-[4/3] sm:aspect-[16/9] md:aspect-[2/1] rounded-2xl shimmer" />
      <div className="mt-4 sm:mt-6 lg:mt-8 space-y-4 sm:space-y-6">
        <div className="h-8 sm:h-12 rounded shimmer w-3/4" />
        <div className="flex flex-wrap gap-2 sm:gap-4">
          <div className="h-10 sm:h-12 rounded-xl shimmer w-36 sm:w-40" />
          <div className="h-10 sm:h-12 rounded-xl shimmer w-28 sm:w-32" />
        </div>
        <div className="h-16 sm:h-20 rounded-xl shimmer" />
        <div className="pt-4 sm:pt-6 border-t border-white/5 space-y-3">
          <div className="h-6 rounded shimmer w-40" />
          <div className="h-24 rounded shimmer" />
        </div>
      </div>
    </div>
  );
}
