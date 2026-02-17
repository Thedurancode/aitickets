"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, ShoppingCart } from "lucide-react";
import Link from "next/link";
import { useCheckoutStore } from "@/stores/checkout-store";
import { usePurchaseMutation } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OrderSummary } from "@/components/checkout/order-summary";
import { PurchaseForm, type PurchaseFormData } from "@/components/tickets/purchase-form";
import { FadeIn } from "@/components/layout/page-transition";
import { usePageView } from "@/hooks/use-pageview";

export default function CheckoutContent() {
  return (
    <Suspense>
      <CheckoutPageInner />
    </Suspense>
  );
}

function CheckoutPageInner() {
  usePageView({ page: "checkout" });
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  const {
    event,
    selectedTier,
    quantity,
    promoValidation,
    buyerInfo,
    setBuyerInfo,
    getTotal,
    clearCheckout,
  } = useCheckoutStore();

  const purchaseMutation = usePurchaseMutation(event?.id || 0);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Don't render until mounted to avoid hydration mismatch
  if (!mounted) {
    return (
      <div className="container py-12 text-center">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  // Redirect if no items in cart
  if (!event || !selectedTier) {
    return (
      <div className="container py-12 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <ShoppingCart className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
          <h1 className="text-2xl font-bold mb-2">Your cart is empty</h1>
          <p className="text-muted-foreground mb-6">
            Browse events and select tickets to get started.
          </p>
          <Link href="/events">
            <Button>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Browse Events
            </Button>
          </Link>
        </motion.div>
      </div>
    );
  }

  const handleSubmit = async (formData: PurchaseFormData) => {
    if (!selectedTier || !event) return;

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
        // Redirect to Stripe
        window.location.href = result.checkout_url;
      } else if (result.tickets) {
        // Free tickets - clear cart and redirect to success
        const ticketIds = result.tickets.map((t) => t.id).join(",");
        clearCheckout();
        router.push(`/success?tickets=${ticketIds}`);
      }
    } catch (err) {
      console.error("Purchase failed:", err);
    }
  };

  const total = getTotal();

  return (
    <div className="container px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8 max-w-4xl mx-auto">
      {/* Back button */}
      <FadeIn>
        <Link href={`/events/${event.id}`}>
          <Button variant="ghost" size="sm" className="mb-4 sm:mb-6">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Event
          </Button>
        </Link>
      </FadeIn>

      <FadeIn delay={0.1}>
        <h1 className="text-2xl sm:text-3xl font-bold mb-6 sm:mb-8">Checkout</h1>
      </FadeIn>

      <div className="grid gap-6 md:grid-cols-2 md:gap-8">
        {/* Order Summary */}
        <FadeIn delay={0.2}>
          <OrderSummary
            event={event}
            tier={selectedTier}
            quantity={quantity}
            promoValidation={promoValidation}
          />
        </FadeIn>

        {/* Payment Form */}
        <FadeIn delay={0.3}>
          <Card>
            <CardHeader>
              <CardTitle>Your Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <PurchaseForm
                onSubmit={handleSubmit}
                isSubmitting={purchaseMutation.isPending}
                defaultValues={buyerInfo}
              />

              {purchaseMutation.isError && (
                <p className="text-sm text-destructive text-center">
                  {(purchaseMutation.error as Error)?.message ||
                    "Something went wrong. Please try again."}
                </p>
              )}
            </CardContent>
          </Card>
        </FadeIn>
      </div>
    </div>
  );
}
