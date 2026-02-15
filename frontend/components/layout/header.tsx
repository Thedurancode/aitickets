"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Ticket, ShoppingCart } from "lucide-react";
import { useCheckoutStore } from "@/stores/checkout-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function Header() {
  const { selectedTier, quantity } = useCheckoutStore();
  const hasItemsInCart = selectedTier !== null;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-background/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/events" className="flex items-center gap-2 group">
          <motion.div
            whileHover={{ rotate: 15, scale: 1.1 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors"
          >
            <Ticket className="h-5 w-5 text-primary" />
          </motion.div>
          <span className="font-bold text-xl text-foreground">Tickets</span>
        </Link>

        <nav className="flex items-center gap-2">
          <Link href="/events">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              Events
            </Button>
          </Link>

          <Link href="/tickets">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
              My Tickets
            </Button>
          </Link>

          <Link href="/checkout" className="relative">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                variant={hasItemsInCart ? "default" : "outline"}
                size="sm"
                className={hasItemsInCart ? "glow-sm" : ""}
              >
                <ShoppingCart className="h-4 w-4 mr-2" />
                Cart
                {hasItemsInCart && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute -top-2 -right-2"
                  >
                    <Badge className="h-5 w-5 p-0 flex items-center justify-center text-xs bg-primary text-primary-foreground">
                      {quantity}
                    </Badge>
                  </motion.div>
                )}
              </Button>
            </motion.div>
          </Link>
        </nav>
      </div>
    </header>
  );
}
