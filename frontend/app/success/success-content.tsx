"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import confetti from "canvas-confetti";
import {
  CheckCircle,
  Calendar,
  Download,
  Wallet,
  Share2,
  Mail,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { Ticket } from "@/types/api";

function SuccessInner() {
  const searchParams = useSearchParams();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const ticketIds = searchParams.get("tickets");
  const sessionId = searchParams.get("session_id");

  // Fire confetti
  const fireConfetti = useCallback(() => {
    const count = 200;
    const defaults = {
      origin: { y: 0.7 },
      zIndex: 9999,
    };

    function fire(particleRatio: number, opts: confetti.Options) {
      confetti({
        ...defaults,
        ...opts,
        particleCount: Math.floor(count * particleRatio),
      });
    }

    fire(0.25, {
      spread: 26,
      startVelocity: 55,
    });
    fire(0.2, {
      spread: 60,
    });
    fire(0.35, {
      spread: 100,
      decay: 0.91,
      scalar: 0.8,
    });
    fire(0.1, {
      spread: 120,
      startVelocity: 25,
      decay: 0.92,
      scalar: 1.2,
    });
    fire(0.1, {
      spread: 120,
      startVelocity: 45,
    });
  }, []);

  useEffect(() => {
    fireConfetti();
  }, [fireConfetti]);

  useEffect(() => {
    async function fetchTickets() {
      if (!ticketIds) {
        setIsLoading(false);
        return;
      }

      try {
        const ids = ticketIds.split(",").map(Number).filter(Boolean);
        const ticketPromises = ids.map((id) => api.tickets.get(id));
        const fetchedTickets = await Promise.all(ticketPromises);
        setTickets(fetchedTickets);
      } catch (error) {
        console.error("Failed to fetch tickets:", error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchTickets();
  }, [ticketIds]);

  const generateCalendarUrl = (ticket: Ticket) => {
    const event = ticket.event;
    const startDate = new Date(`${event.event_date}T${event.event_time}`);
    const endDate = new Date(startDate.getTime() + 3 * 60 * 60 * 1000); // 3 hours

    const formatDateForCalendar = (date: Date) => {
      return date.toISOString().replace(/-|:|\.\d{3}/g, "");
    };

    const params = new URLSearchParams({
      action: "TEMPLATE",
      text: event.name,
      dates: `${formatDateForCalendar(startDate)}/${formatDateForCalendar(endDate)}`,
      location: ticket.venue.address,
      details: event.description || "",
    });

    return `https://calendar.google.com/calendar/render?${params.toString()}`;
  };

  const firstTicket = tickets[0];
  const event = firstTicket?.event;
  const venue = firstTicket?.venue;

  return (
    <div className="container py-12 max-w-2xl mx-auto text-center">
      {/* Success Animation */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 15 }}
        className="mb-8"
      >
        <div className="w-24 h-24 mx-auto bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring" }}
          >
            <CheckCircle className="h-12 w-12 text-green-600 dark:text-green-400" />
          </motion.div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <h1 className="text-3xl font-bold mb-2">You're all set!</h1>
        <p className="text-muted-foreground mb-8">
          Your tickets have been confirmed. Check your email for details.
        </p>
      </motion.div>

      {isLoading ? (
        <Card>
          <CardContent className="py-8">
            <div className="animate-pulse space-y-4">
              <div className="h-6 bg-muted rounded w-3/4 mx-auto" />
              <div className="h-4 bg-muted rounded w-1/2 mx-auto" />
            </div>
          </CardContent>
        </Card>
      ) : event && venue ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="mb-8">
            <CardContent className="py-6 space-y-4">
              <h2 className="text-xl font-semibold">{event.name}</h2>
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>
                  {formatDateTime(`${event.event_date}T${event.event_time}`)}
                </span>
              </div>
              <p className="text-muted-foreground">{venue.name}</p>
              <p className="text-sm text-muted-foreground">{venue.address}</p>

              <div className="pt-4 border-t">
                <p className="text-sm font-medium mb-2">
                  {tickets.length} ticket{tickets.length > 1 ? "s" : ""} for{" "}
                  {firstTicket.event_goer.name}
                </p>
                <p className="text-sm text-muted-foreground">
                  Confirmation sent to {firstTicket.event_goer.email}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Action buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="grid grid-cols-2 gap-4 mb-8"
          >
            <a
              href={generateCalendarUrl(firstTicket)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" className="w-full">
                <Calendar className="mr-2 h-4 w-4" />
                Add to Calendar
              </Button>
            </a>

            <a
              href={api.tickets.getPdfUrl(firstTicket.id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" className="w-full">
                <Download className="mr-2 h-4 w-4" />
                Download PDF
              </Button>
            </a>

            <a
              href={api.tickets.getWalletUrl(firstTicket.id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" className="w-full">
                <Wallet className="mr-2 h-4 w-4" />
                Apple Wallet
              </Button>
            </a>

            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                if (navigator.share) {
                  navigator.share({
                    title: event.name,
                    text: `I'm going to ${event.name}!`,
                    url: window.location.origin + `/events/${event.id}`,
                  });
                }
              }}
            >
              <Share2 className="mr-2 h-4 w-4" />
              Share
            </Button>
          </motion.div>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="mb-8">
            <CardContent className="py-6">
              <Mail className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                Your tickets have been sent to your email address.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      )}

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
      >
        <Link href="/events">
          <Button size="lg">Browse More Events</Button>
        </Link>
      </motion.div>
    </div>
  );
}

export default function SuccessContent() {
  return (
    <Suspense
      fallback={
        <div className="container py-12 text-center">
          <div className="animate-pulse">Loading...</div>
        </div>
      }
    >
      <SuccessInner />
    </Suspense>
  );
}
