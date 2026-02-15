"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Eye, EyeOff, Calendar, MapPin } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AdminDashboardData } from "@/types/api";

interface AdminHeaderProps {
  data: AdminDashboardData;
}

export function AdminHeader({ data }: AdminHeaderProps) {
  const { event } = data;

  const statusColor = {
    published: "bg-green-500/20 text-green-400 border-green-500/30",
    scheduled: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    cancelled: "bg-red-500/20 text-red-400 border-red-500/30",
  }[event.status] || "bg-muted text-muted-foreground";

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-8"
    >
      <Link
        href={`/events/${event.id}`}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to event
      </Link>

      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">
            {event.name}
          </h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              {event.event_date} at {event.event_time}
            </span>
            {event.venue && (
              <span className="flex items-center gap-1.5">
                <MapPin className="h-4 w-4" />
                {event.venue.name}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge className={statusColor}>
            {event.status.charAt(0).toUpperCase() + event.status.slice(1)}
          </Badge>
          <Badge variant="outline" className="gap-1.5">
            {event.is_visible ? (
              <>
                <Eye className="h-3 w-3" /> Visible
              </>
            ) : (
              <>
                <EyeOff className="h-3 w-3" /> Hidden
              </>
            )}
          </Badge>
        </div>
      </div>
    </motion.div>
  );
}
