"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { Calendar, Clock, MapPin, Download, Wallet, Share2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDate, formatTime } from "@/lib/utils";
import type { Ticket } from "@/types/api";

interface TicketCardProps {
  ticket: Ticket;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  PAID: { label: "Confirmed", className: "bg-green-500/10 text-green-400 border-green-500/20" },
  CHECKED_IN: { label: "Checked In", className: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
};

export function TicketCard({ ticket }: TicketCardProps) {
  const event = ticket.event;
  const eventDateTime = `${event.event_date}T${event.event_time}`;
  const status = statusConfig[ticket.status] || { label: ticket.status, className: "" };

  const handleShare = async () => {
    if (navigator.share) {
      await navigator.share({
        title: `Ticket for ${event.name}`,
        text: `I'm going to ${event.name}!`,
      }).catch(() => {});
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="overflow-hidden bg-card/50 border-white/5 backdrop-blur-sm hover:border-white/10 transition-colors">
        <CardContent className="p-0">
          <div className="flex flex-col sm:flex-row">
            {/* Event Image */}
            <div className="relative w-full sm:w-48 h-40 sm:h-auto flex-shrink-0">
              {event.image_url ? (
                <Image
                  src={event.image_url}
                  alt={event.name}
                  fill
                  className="object-cover"
                  sizes="(max-width: 640px) 100vw, 192px"
                />
              ) : (
                <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                  <Calendar className="h-12 w-12 text-primary/30" />
                </div>
              )}
            </div>

            {/* Ticket Info */}
            <div className="flex-1 p-4 sm:p-5 space-y-3">
              <div className="flex items-start justify-between gap-2 sm:gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-base sm:text-lg text-foreground truncate">{event.name}</h3>
                  <p className="text-xs sm:text-sm text-muted-foreground">{ticket.ticket_tier.name}</p>
                </div>
                <Badge className={`${status.className} flex-shrink-0 text-xs`}>{status.label}</Badge>
              </div>

              <div className="flex flex-wrap gap-2 sm:gap-3 text-xs sm:text-sm text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5 text-primary flex-shrink-0" />
                  {formatDate(eventDateTime)}
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-primary flex-shrink-0" />
                  {formatTime(eventDateTime)}
                </div>
                <div className="flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-primary flex-shrink-0" />
                  <span className="truncate">{ticket.venue.name}</span>
                </div>
              </div>

              {/* QR Code + Actions */}
              <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-3 pt-2 border-t border-white/5">
                {ticket.qr_code_token && (
                  <div className="rounded-lg overflow-hidden bg-white p-1 w-16 h-16 flex-shrink-0">
                    <img
                      src={api.tickets.getQrUrl(ticket.id)}
                      alt="QR Code"
                      className="w-full h-full"
                    />
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <a href={api.tickets.getPdfUrl(ticket.id)} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm" className="gap-1.5 h-9">
                      <Download className="h-3.5 w-3.5" />
                      PDF
                    </Button>
                  </a>
                  <a href={api.tickets.getWalletUrl(ticket.id)} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm" className="gap-1.5 h-9">
                      <Wallet className="h-3.5 w-3.5" />
                      Wallet
                    </Button>
                  </a>
                  <Button variant="outline" size="sm" className="gap-1.5 h-9" onClick={handleShare}>
                    <Share2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function TicketCardSkeleton() {
  return (
    <Card className="overflow-hidden bg-card/50 border-white/5">
      <CardContent className="p-0">
        <div className="flex flex-col sm:flex-row">
          <div className="w-full sm:w-48 h-40 sm:h-auto shimmer" />
          <div className="flex-1 p-5 space-y-3">
            <div className="h-6 rounded shimmer w-3/4" />
            <div className="h-4 rounded shimmer w-1/2" />
            <div className="flex gap-3">
              <div className="h-4 rounded shimmer w-24" />
              <div className="h-4 rounded shimmer w-20" />
              <div className="h-4 rounded shimmer w-28" />
            </div>
            <div className="h-16 rounded shimmer w-16 mt-2" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
