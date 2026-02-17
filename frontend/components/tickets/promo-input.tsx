"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Tag, Check, X, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency } from "@/lib/utils";
import type { PromoValidationResponse } from "@/types/api";

interface PromoInputProps {
  ticketTierId: number | null;
  onValidate: (code: string) => Promise<PromoValidationResponse>;
  onApply: (validation: PromoValidationResponse | null) => void;
  appliedPromo: PromoValidationResponse | null;
}

export function PromoInput({
  ticketTierId,
  onValidate,
  onApply,
  appliedPromo,
}: PromoInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [code, setCode] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApply = async () => {
    if (!code.trim() || !ticketTierId) return;

    setIsValidating(true);
    setError(null);

    try {
      const result = await onValidate(code.trim().toUpperCase());
      if (result.valid) {
        onApply(result);
        setCode("");
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError("Failed to validate promo code");
    } finally {
      setIsValidating(false);
    }
  };

  const handleRemove = () => {
    onApply(null);
    setCode("");
    setError(null);
  };

  if (appliedPromo?.valid) {
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800"
      >
        <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
          <Check className="h-4 w-4" />
          <span className="font-medium">{appliedPromo.code}</span>
          <span className="text-sm">
            (
            {appliedPromo.discount_type === "PERCENT"
              ? `${appliedPromo.discount_value}% off`
              : `${formatCurrency((appliedPromo.discount_value || 0) / 100)} off`}
            )
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRemove}
          className="h-8 text-green-700 dark:text-green-300 hover:text-green-900 hover:bg-green-100"
        >
          <X className="h-4 w-4" />
        </Button>
      </motion.div>
    );
  }

  return (
    <div className="space-y-2">
      <AnimatePresence>
        {!isOpen ? (
          <motion.button
            key="toggle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(true)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <Tag className="h-3.5 w-3.5" />
            Have a promo code?
          </motion.button>
        ) : (
          <motion.div
            key="input"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-2"
          >
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Tag className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Promo code"
                  value={code}
                  onChange={(e) => {
                    setCode(e.target.value.toUpperCase());
                    setError(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleApply();
                    }
                  }}
                  className={cn("pl-10", error && "border-destructive")}
                  disabled={!ticketTierId}
                  autoFocus
                />
              </div>
              <Button
                variant="outline"
                onClick={handleApply}
                disabled={!code.trim() || !ticketTierId || isValidating}
              >
                {isValidating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Apply"
                )}
              </Button>
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
