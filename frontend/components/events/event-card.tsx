"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { Calendar, MapPin, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatTime } from "@/lib/utils";
import type { EventWithVenue } from "@/types/api";
import { staggerItemVariants } from "@/components/layout/page-transition";

interface EventCardProps {
  event: EventWithVenue;
}

export function EventCard({ event }: EventCardProps) {
  const eventDateTime = `${event.event_date}T${event.event_time}`;

  return (
    <motion.div variants={staggerItemVariants}>
      <Link href={`/events/${event.id}`}>
        <motion.div
          whileHover={{ y: -8, scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
        >
          <Card className="overflow-hidden h-full bg-card/50 border-white/5 card-glow cursor-pointer gradient-border">
            <div className="relative aspect-[4/3] overflow-hidden">
              {event.image_url ? (
                <motion.div
                  layoutId={`event-image-${event.id}`}
                  className="absolute inset-0"
                >
                  <Image
                    src={event.image_url}
                    alt={event.name}
                    fill
                    className="object-cover transition-transform duration-500 hover:scale-110"
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                </motion.div>
              ) : (
                <div className="absolute inset-0 bg-gradient-to-br from-primary/30 via-primary/10 to-transparent flex items-center justify-center">
                  <div className="p-4 rounded-full bg-primary/10">
                    <Calendar className="h-12 w-12 text-primary/50" />
                  </div>
                </div>
              )}

              {/* Category badges */}
              {event.categories.length > 0 && (
                <div className="absolute top-3 left-3 flex gap-2 flex-wrap">
                  {event.categories.slice(0, 2).map((category) => (
                    <Badge
                      key={category.id}
                      className="backdrop-blur-md bg-black/40 border-white/10 text-white"
                    >
                      {category.name}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Date overlay */}
              <div className="absolute bottom-3 left-3">
                <div className="backdrop-blur-md bg-black/40 rounded-lg px-3 py-2 border border-white/10">
                  <div className="text-xs text-white/70">{formatDate(eventDateTime).split(',')[0]}</div>
                  <div className="text-lg font-bold text-white">{new Date(eventDateTime).getDate()}</div>
                </div>
              </div>
            </div>

            <CardContent className="p-5 space-y-3">
              <motion.h3
                layoutId={`event-title-${event.id}`}
                className="font-semibold text-lg line-clamp-2 text-foreground"
              >
                {event.name}
              </motion.h3>

              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-primary/70" />
                  <span>{formatTime(eventDateTime)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-primary/70" />
                  <span className="truncate">{event.venue.name}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </Link>
    </motion.div>
  );
}

// Loading skeleton
export function EventCardSkeleton() {
  return (
    <Card className="overflow-hidden bg-card/50 border-white/5">
      <div className="relative aspect-[4/3] shimmer" />
      <CardContent className="p-5 space-y-3">
        <div className="h-6 rounded shimmer w-3/4" />
        <div className="space-y-2">
          <div className="h-4 rounded shimmer w-1/2" />
          <div className="h-4 rounded shimmer w-2/3" />
        </div>
      </CardContent>
    </Card>
  );
}
