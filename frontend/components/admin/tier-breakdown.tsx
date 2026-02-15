"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AdminTierStats } from "@/types/api";

interface TierBreakdownProps {
  tiers: AdminTierStats[];
}

export function TierBreakdown({ tiers }: TierBreakdownProps) {
  return (
    <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-lg">Ticket Tiers</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {tiers.map((tier, i) => {
            const pct =
              tier.quantity_available > 0
                ? (tier.quantity_sold / tier.quantity_available) * 100
                : 0;
            const isSoldOut = tier.quantity_sold >= tier.quantity_available;

            return (
              <motion.div
                key={tier.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">
                      {tier.name}
                    </span>
                    <Badge
                      variant="outline"
                      className={
                        isSoldOut
                          ? "text-red-400 border-red-500/30"
                          : "text-green-400 border-green-500/30"
                      }
                    >
                      {isSoldOut ? "Sold Out" : "Active"}
                    </Badge>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {tier.price > 0
                      ? `$${(tier.price / 100).toFixed(2)}`
                      : "Free"}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(pct, 100)}%` }}
                      transition={{ duration: 0.8, delay: i * 0.1 }}
                      className={`h-full rounded-full ${
                        pct >= 100
                          ? "bg-red-500"
                          : pct >= 80
                            ? "bg-yellow-500"
                            : "bg-primary"
                      }`}
                    />
                  </div>
                  <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {tier.quantity_sold}/{tier.quantity_available}
                  </span>
                </div>

                <div className="text-xs text-muted-foreground">
                  Revenue: ${(tier.revenue_cents / 100).toFixed(2)}
                </div>
              </motion.div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
