"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

// Stripe minimum is $0.50 USD (50 cents)
const STRIPE_MINIMUM_CENTS = 50;

interface PriceSummaryProps {
  tierName: string;
  unitPrice: number; // in cents
  quantity: number;
  discount: number; // in cents
}

export function PriceSummary({
  tierName,
  unitPrice,
  quantity,
  discount,
}: PriceSummaryProps) {
  const subtotal = unitPrice * quantity;
  const rawTotal = Math.max(0, subtotal - discount);
  // If total is below Stripe minimum, make it free
  const total = rawTotal > 0 && rawTotal < STRIPE_MINIMUM_CENTS ? 0 : rawTotal;
  const isBelowMinimum = rawTotal > 0 && rawTotal < STRIPE_MINIMUM_CENTS;

  return (
    <div className="space-y-3 py-4 border-t border-white/5">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">
          {tierName} x {quantity}
        </span>
        <AnimatedPrice amount={subtotal} />
      </div>

      <AnimatePresence>
        {discount > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex justify-between text-sm text-emerald-400"
          >
            <span>Discount</span>
            <span>-{formatCurrency(discount / 100)}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isBelowMinimum && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 rounded-lg px-3 py-2"
          >
            <AlertCircle className="h-3 w-3" />
            <span>Amount below minimum - tickets are free!</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex justify-between font-semibold text-lg pt-2 border-t border-white/5">
        <span>Total</span>
        <AnimatedPrice amount={total} className={total === 0 ? "text-emerald-400" : "text-primary"} />
      </div>
    </div>
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
