"use client";

import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, Search, Ticket, Loader2 } from "lucide-react";
import { useTicketsByEmail } from "@/lib/queries";
import { useCheckoutStore } from "@/stores/checkout-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { TicketCard, TicketCardSkeleton } from "@/components/tickets/ticket-card";
import { FadeIn } from "@/components/layout/page-transition";
import { usePageView } from "@/hooks/use-pageview";

const emailSchema = z.object({
  email: z.string().email("Please enter a valid email"),
});

type EmailFormData = z.infer<typeof emailSchema>;

export default function MyTicketsContent() {
  return (
    <Suspense>
      <MyTicketsPageInner />
    </Suspense>
  );
}

function MyTicketsPageInner() {
  usePageView({ page: "my-tickets" });
  const [lookupEmail, setLookupEmail] = useState("");
  const buyerEmail = useCheckoutStore((s) => s.buyerInfo.email);

  const { data: tickets, isLoading, error } = useTicketsByEmail(lookupEmail);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EmailFormData>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: buyerEmail || "" },
  });

  const onSubmit = (data: EmailFormData) => {
    setLookupEmail(data.email);
  };

  return (
    <div className="container px-4 sm:px-6 lg:px-8 py-6 md:py-12 max-w-3xl">
      <FadeIn>
        <div className="mb-6 sm:mb-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full bg-primary/10 border border-primary/20 mb-3 sm:mb-4"
          >
            <Ticket className="h-4 w-4 text-primary" />
            <span className="text-xs sm:text-sm text-primary">Your tickets</span>
          </motion.div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-2 sm:mb-3 text-foreground">
            My Tickets
          </h1>
          <p className="text-muted-foreground text-base sm:text-lg">
            Enter your email to find your tickets
          </p>
        </div>
      </FadeIn>

      <FadeIn delay={0.1}>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col sm:flex-row gap-3 mb-6 sm:mb-10">
          <div className="flex-1 relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              {...register("email")}
              type="email"
              placeholder="your@email.com"
              className="pl-10"
            />
            {errors.email && (
              <p className="text-sm text-red-400 mt-1">{errors.email.message}</p>
            )}
          </div>
          <Button type="submit" disabled={isLoading} className="gap-2">
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Find Tickets
          </Button>
        </form>
      </FadeIn>

      <AnimatePresence mode="wait">
        {isLoading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {[1, 2, 3].map((i) => (
              <TicketCardSkeleton key={i} />
            ))}
          </motion.div>
        )}

        {error && (
          <motion.div
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-12"
          >
            <p className="text-red-400">Something went wrong. Please try again.</p>
          </motion.div>
        )}

        {!isLoading && tickets && tickets.length === 0 && (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-center py-16"
          >
            <Ticket className="h-16 w-16 text-muted-foreground/30 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-foreground mb-2">No tickets found</h2>
            <p className="text-muted-foreground">
              We couldn&apos;t find any tickets for this email address.
            </p>
          </motion.div>
        )}

        {!isLoading && tickets && tickets.length > 0 && (
          <motion.div
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            <p className="text-sm text-muted-foreground mb-4">
              Found {tickets.length} ticket{tickets.length !== 1 ? "s" : ""}
            </p>
            {tickets.map((ticket, i) => (
              <motion.div
                key={ticket.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <TicketCard ticket={ticket} />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
