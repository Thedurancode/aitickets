"use client";

import { Suspense, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useEvent, usePurchaseMutation } from "@/lib/queries";
import { api } from "@/lib/api";
import { useCheckoutStore } from "@/stores/checkout-store";
import { usePageView } from "@/hooks/use-pageview";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EventHero, EventHeroSkeleton } from "@/components/events/event-hero";
import {
  TierSelector,
  TierSelectorSkeleton,
} from "@/components/tickets/tier-selector";
import { QuantityPicker } from "@/components/tickets/quantity-picker";
import { PromoInput } from "@/components/tickets/promo-input";
import { PurchaseForm, type PurchaseFormData } from "@/components/tickets/purchase-form";
import { PriceSummary } from "@/components/tickets/price-summary";

export default function EventDetailContent() {
  return (
    <Suspense>
      <EventDetailPageInner />
    </Suspense>
  );
}

function EventDetailPageInner() {
  const params = useParams();
  const router = useRouter();
  const eventId = Number(params.id);

  usePageView({ eventId, page: "detail" });
  const { data: event, isLoading: eventLoading, error } = useEvent(eventId, {
    refetchInterval: 15000,
  });
  const purchaseMutation = usePurchaseMutation(eventId);

  const {
    setEvent,
    selectedTier,
    selectTier,
    quantity,
    incrementQuantity,
    decrementQuantity,
    setQuantity,
    promoValidation,
    setPromoValidation,
    buyerInfo,
    setBuyerInfo,
    getDiscount,
  } = useCheckoutStore();

  // Set event in store when loaded
  useEffect(() => {
    if (event) {
      setEvent(event);
    }
  }, [event, setEvent]);

  const handlePromoValidate = async (code: string) => {
    if (!selectedTier) {
      throw new Error("Please select a ticket tier first");
    }
    return api.promo.validate(code, selectedTier.id);
  };

  const handlePurchase = async (formData: PurchaseFormData) => {
    if (!selectedTier) return;

    // Save buyer info
    setBuyerInfo(formData);

    try {
      const result = await purchaseMutation.mutateAsync({
        ticket_tier_id: selectedTier.id,
        email: formData.email,
        name: formData.name,
        phone: formData.phone || undefined,
        quantity,
        promo_code: promoValidation?.code || undefined,
      });

      if (result.checkout_url) {
        // Redirect to Stripe checkout
        window.location.href = result.checkout_url;
      } else if (result.tickets) {
        // Free tickets - redirect to success
        router.push(`/success?tickets=${result.tickets.map(t => t.id).join(",")}`);
      }
    } catch (err) {
      console.error("Purchase failed:", err);
    }
  };

  if (error) {
    return (
      <div className="container py-12 text-center">
        <h1 className="text-2xl font-bold mb-4">Event Not Found</h1>
        <p className="text-muted-foreground mb-6">
          The event you're looking for doesn't exist or has been removed.
        </p>
        <Link href="/events">
          <Button>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Events
          </Button>
        </Link>
      </div>
    );
  }

  const maxQuantity = selectedTier
    ? Math.min(selectedTier.tickets_remaining, 10)
    : 10;

  return (
    <div className="container py-8">
      {/* Back button */}
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        className="mb-6"
      >
        <Link href="/events">
          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Events
          </Button>
        </Link>
      </motion.div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main content */}
        <div className="lg:col-span-2">
          {eventLoading ? <EventHeroSkeleton /> : event && <EventHero event={event} />}
        </div>

        {/* Ticket purchase panel */}
        <div className="lg:col-span-1">
          <div className="lg:sticky lg:top-24">
            <Card className="bg-card/50 border-white/5 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Get Tickets</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {eventLoading ? (
                  <TierSelectorSkeleton />
                ) : event ? (
                  <>
                    <TierSelector
                      tiers={event.ticket_tiers}
                      selectedTierId={selectedTier?.id ?? null}
                      onSelectTier={selectTier}
                    />

                    {selectedTier && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="space-y-6"
                      >
                        <QuantityPicker
                          quantity={quantity}
                          maxQuantity={maxQuantity}
                          onIncrement={incrementQuantity}
                          onDecrement={decrementQuantity}
                          onChange={setQuantity}
                        />

                        <PromoInput
                          ticketTierId={selectedTier.id}
                          onValidate={handlePromoValidate}
                          onApply={setPromoValidation}
                          appliedPromo={promoValidation}
                        />

                        <PriceSummary
                          tierName={selectedTier.name}
                          unitPrice={selectedTier.price}
                          quantity={quantity}
                          discount={getDiscount()}
                        />

                        <PurchaseForm
                          onSubmit={handlePurchase}
                          isSubmitting={purchaseMutation.isPending}
                          defaultValues={buyerInfo}
                        />

                        {purchaseMutation.isError && (
                          <p className="text-sm text-destructive text-center">
                            {(purchaseMutation.error as Error)?.message ||
                              "Failed to create checkout session. Please try again."}
                          </p>
                        )}
                      </motion.div>
                    )}

                    {event.ticket_tiers.length === 0 && (
                      <p className="text-center text-muted-foreground py-4">
                        No tickets available for this event.
                      </p>
                    )}
                  </>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
