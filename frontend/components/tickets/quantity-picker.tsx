"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface QuantityPickerProps {
  quantity: number;
  maxQuantity: number;
  onIncrement: () => void;
  onDecrement: () => void;
  onChange: (quantity: number) => void;
}

export function QuantityPicker({
  quantity,
  maxQuantity,
  onIncrement,
  onDecrement,
}: QuantityPickerProps) {
  const canDecrement = quantity > 1;
  const canIncrement = quantity < maxQuantity;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Quantity</label>
      <div className="flex items-center gap-3">
        <motion.div whileTap={{ scale: 0.9 }}>
          <Button
            variant="outline"
            size="icon"
            onClick={onDecrement}
            disabled={!canDecrement}
            className="h-10 w-10"
          >
            <Minus className="h-4 w-4" />
          </Button>
        </motion.div>

        <div className="w-12 text-center">
          <AnimatePresence mode="popLayout">
            <motion.span
              key={quantity}
              initial={{ y: -10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 10, opacity: 0 }}
              className="text-xl font-semibold inline-block"
            >
              {quantity}
            </motion.span>
          </AnimatePresence>
        </div>

        <motion.div whileTap={{ scale: 0.9 }}>
          <Button
            variant="outline"
            size="icon"
            onClick={onIncrement}
            disabled={!canIncrement}
            className="h-10 w-10"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </motion.div>

        <span className="text-sm text-muted-foreground">
          (max {maxQuantity})
        </span>
      </div>
    </div>
  );
}

// Quick select buttons for common quantities
interface QuickQuantitySelectProps {
  quantity: number;
  maxQuantity: number;
  onChange: (quantity: number) => void;
}

export function QuickQuantitySelect({
  quantity,
  maxQuantity,
  onChange,
}: QuickQuantitySelectProps) {
  const options = [1, 2, 4, 6].filter((n) => n <= maxQuantity);

  return (
    <div className="flex gap-2">
      {options.map((num) => (
        <motion.button
          key={num}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => onChange(num)}
          className={cn(
            "h-10 w-10 rounded-full text-sm font-medium transition-colors",
            quantity === num
              ? "bg-primary text-primary-foreground"
              : "bg-muted hover:bg-muted/80"
          )}
        >
          {num}
        </motion.button>
      ))}
    </div>
  );
}
