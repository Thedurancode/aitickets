"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { MapPin, Calendar, Users, Loader2 } from "lucide-react";
import Link from "next/link";
import { FadeIn } from "@/components/layout/page-transition";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Venue {
  id: number;
  name: string;
  address?: string;
  phone?: string;
  description?: string;
  logo_url?: string;
  created_at: string;
}

export default function VenuesPage() {
  const { data: venues, isLoading } = useQuery<Venue[]>({
    queryKey: ["venues"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/venues`);
      if (!res.ok) throw new Error("Failed to fetch venues");
      return res.json();
    },
  });

  return (
    <div className="container px-4 sm:px-6 lg:px-8 py-6 md:py-12 max-w-5xl mx-auto">
      <FadeIn>
        <div className="mb-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-4"
          >
            <MapPin className="h-4 w-4 text-primary" />
            <span className="text-sm text-primary">Discover</span>
          </motion.div>
          <h1 className="text-4xl md:text-5xl font-bold mb-3 text-foreground">
            Venues
          </h1>
          <p className="text-muted-foreground text-lg">
            Explore venues hosting upcoming events
          </p>
        </div>
      </FadeIn>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : !venues || venues.length === 0 ? (
        <div className="text-center py-20">
          <MapPin className="h-16 w-16 text-muted-foreground/30 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-foreground mb-2">No venues yet</h2>
          <p className="text-muted-foreground">Check back soon for new venues.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {venues.map((venue, i) => (
            <motion.div
              key={venue.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <div className="rounded-xl border border-white/10 bg-card hover:border-primary/30 transition-all hover:shadow-lg overflow-hidden">
                {venue.logo_url ? (
                  <img
                    src={venue.logo_url}
                    alt={venue.name}
                    className="w-full h-40 object-cover"
                  />
                ) : (
                  <div className="w-full h-40 bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                    <MapPin className="h-12 w-12 text-primary/40" />
                  </div>
                )}
                <div className="p-5">
                  <h3 className="text-lg font-bold text-foreground mb-1">{venue.name}</h3>
                  {venue.address && (
                    <p className="text-sm text-muted-foreground flex items-center gap-1.5 mb-2">
                      <MapPin className="h-3.5 w-3.5 shrink-0" />
                      {venue.address}
                    </p>
                  )}
                  {venue.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">{venue.description}</p>
                  )}
                  <Link
                    href={`/events?venue=${venue.id}`}
                    className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mt-3"
                  >
                    <Calendar className="h-3.5 w-3.5" />
                    View Events
                  </Link>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
