"use client";

import { motion } from "framer-motion";
import { Loader2, CreditCard, Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";

interface CheckoutButtonProps {
  total: number; // in cents
  isLoading: boolean;
  onClick: () => void;
  disabled?: boolean;
}

export function CheckoutButton({
  total,
  isLoading,
  onClick,
  disabled,
}: CheckoutButtonProps) {
  const isFree = total === 0;

  return (
    <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
      <Button
        size="lg"
        className="w-full h-14 text-lg"
        onClick={onClick}
        disabled={disabled || isLoading}
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Processing...
          </>
        ) : isFree ? (
          <>
            <Ticket className="mr-2 h-5 w-5" />
            Get Free Tickets
          </>
        ) : (
          <>
            <CreditCard className="mr-2 h-5 w-5" />
            Pay {formatCurrency(total / 100)}
          </>
        )}
      </Button>
    </motion.div>
  );
}
