"use client";

import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import { Calendar, MapPin, Ticket, Tag } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatDate, formatTime } from "@/lib/utils";
import type { EventDetail, TicketTier, PromoValidationResponse } from "@/types/api";

interface OrderSummaryProps {
  event: EventDetail;
  tier: TicketTier;
  quantity: number;
  promoValidation: PromoValidationResponse | null;
}

export function OrderSummary({
  event,
  tier,
  quantity,
  promoValidation,
}: OrderSummaryProps) {
  const subtotal = tier.price * quantity;
  const discount = promoValidation?.valid
    ? promoValidation.discount_amount_cents * quantity
    : 0;
  const total = Math.max(0, subtotal - discount);
  const eventDateTime = `${event.event_date}T${event.event_time}`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Ticket className="h-5 w-5" />
          Order Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Event Info */}
        <div className="flex gap-4">
          {event.image_url && (
            <div className="relative w-20 h-20 rounded-lg overflow-hidden flex-shrink-0">
              <Image
                src={event.image_url}
                alt={event.name}
                fill
                className="object-cover"
              />
            </div>
          )}
          <div className="min-w-0">
            <h3 className="font-semibold line-clamp-2">{event.name}</h3>
            <div className="text-sm text-muted-foreground space-y-1 mt-1">
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>
                  {formatDate(eventDateTime)} at {formatTime(eventDateTime)}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                <span className="truncate">{event.venue.name}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Line Items */}
        <div className="space-y-3 py-4 border-y">
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex justify-between"
          >
            <div>
              <p className="font-medium">{tier.name}</p>
              <p className="text-sm text-muted-foreground">
                {formatCurrency(tier.price / 100)} x {quantity}
              </p>
            </div>
            <AnimatedPrice amount={subtotal} />
          </motion.div>

          <AnimatePresence>
            {discount > 0 && promoValidation && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="flex justify-between text-green-600 dark:text-green-400"
              >
                <div className="flex items-center gap-2">
                  <Tag className="h-4 w-4" />
                  <span>{promoValidation.code}</span>
                </div>
                <span>-{formatCurrency(discount / 100)}</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Total */}
        <div className="flex justify-between items-center">
          <span className="text-lg font-semibold">Total</span>
          <AnimatedPrice
            amount={total}
            className="text-xl font-bold text-primary"
          />
        </div>
      </CardContent>
    </Card>
  );
}

function AnimatedPrice({
  amount,
  className = "",
}: {
  amount: number;
  className?: string;
}) {
  return (
    <AnimatePresence mode="popLayout">
      <motion.span
        key={amount}
        initial={{ y: -10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 10, opacity: 0 }}
        className={className}
      >
        {amount === 0 ? "Free" : formatCurrency(amount / 100)}
      </motion.span>
    </AnimatePresence>
  );
}
