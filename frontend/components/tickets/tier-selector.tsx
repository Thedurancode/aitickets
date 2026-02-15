"use client";

import { motion } from "framer-motion";
import { Check, Ticket, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatCurrency } from "@/lib/utils";
import type { TicketTier } from "@/types/api";

interface TierSelectorProps {
  tiers: TicketTier[];
  selectedTierId: number | null;
  onSelectTier: (tier: TicketTier) => void;
}

export function TierSelector({
  tiers,
  selectedTierId,
  onSelectTier,
}: TierSelectorProps) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-lg">Select Tickets</h3>
      <div className="space-y-3">
        {tiers.map((tier, index) => (
          <TierCard
            key={tier.id}
            tier={tier}
            isSelected={selectedTierId === tier.id}
            onSelect={() => onSelectTier(tier)}
            index={index}
          />
        ))}
      </div>
    </div>
  );
}

interface TierCardProps {
  tier: TicketTier;
  isSelected: boolean;
  onSelect: () => void;
  index: number;
}

function TierCard({ tier, isSelected, onSelect, index }: TierCardProps) {
  const isSoldOut = tier.status === "SOLD_OUT" || tier.tickets_remaining === 0;
  const isLowStock = tier.tickets_remaining <= 10 && tier.tickets_remaining > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <motion.button
        whileHover={!isSoldOut ? { scale: 1.02 } : {}}
        whileTap={!isSoldOut ? { scale: 0.98 } : {}}
        onClick={onSelect}
        disabled={isSoldOut}
        className="w-full text-left"
      >
        <Card
          className={cn(
            "relative overflow-hidden transition-all bg-card/50 border-white/5",
            isSelected && "border-primary/50 glow-sm",
            isSoldOut && "opacity-50 cursor-not-allowed",
            !isSoldOut && !isSelected && "hover:border-white/10"
          )}
        >
          {/* Selection gradient */}
          {isSelected && (
            <motion.div
              layoutId="tier-selection"
              className="absolute inset-0 bg-gradient-to-r from-primary/10 to-transparent pointer-events-none"
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          )}

          <CardContent className="p-4 flex items-center justify-between gap-4 relative">
            <div className="flex items-center gap-4">
              <div
                className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center transition-colors",
                  isSelected
                    ? "bg-primary text-primary-foreground"
                    : "bg-white/5"
                )}
              >
                {isSelected ? (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 500 }}
                  >
                    <Check className="h-5 w-5" />
                  </motion.div>
                ) : (
                  <Ticket className="h-5 w-5 text-muted-foreground" />
                )}
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">{tier.name}</span>
                  {isSoldOut && (
                    <Badge variant="destructive" className="text-xs">
                      Sold Out
                    </Badge>
                  )}
                  {isLowStock && !isSoldOut && (
                    <Badge className="text-xs bg-amber-500/20 text-amber-400 border-amber-500/30">
                      <Sparkles className="h-3 w-3 mr-1" />
                      {tier.tickets_remaining} left
                    </Badge>
                  )}
                </div>
                {tier.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {tier.description}
                  </p>
                )}
              </div>
            </div>

            <div className="text-right">
              <div className="font-bold text-xl text-foreground">
                {tier.price === 0 ? (
                  <span className="text-emerald-400">Free</span>
                ) : (
                  formatCurrency(tier.price / 100)
                )}
              </div>
              {!isSoldOut && (
                <p className="text-xs text-muted-foreground">
                  {tier.tickets_remaining} available
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.button>
    </motion.div>
  );
}

export function TierSelectorSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-7 rounded shimmer w-32" />
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i} className="bg-card/50 border-white/5">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl shimmer" />
                  <div className="space-y-2">
                    <div className="h-5 rounded shimmer w-32" />
                    <div className="h-4 rounded shimmer w-48" />
                  </div>
                </div>
                <div className="h-7 rounded shimmer w-20" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
