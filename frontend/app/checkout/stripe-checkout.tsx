"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  CreditCard,
  Lock,
  CheckCircle2,
  Mail,
  Phone,
  User,
  Calendar,
  MapPin,
  Ticket,
  Shield,
  ChevronRight
} from "lucide-react";
import Link from "next/link";
import { useCheckoutStore } from "@/stores/checkout-store";
import { usePurchaseMutation } from "@/lib/queries";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { cn } from "@/lib/utils";

// Stripe-inspired form schema
const checkoutSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  name: z.string().min(2, "Name must be at least 2 characters"),
  phone: z.string().optional(),
  cardNumber: z.string().min(16, "Card number must be 16 digits"),
  expiry: z.string().regex(/^\d{2}\/\d{2}$/, "Format: MM/YY"),
  cvc: z.string().min(3, "CVC must be at least 3 digits"),
  billingName: z.string().min(2, "Billing name is required"),
  country: z.string().min(2, "Country is required"),
  zip: z.string().min(3, "ZIP code is required"),
});

type CheckoutFormData = z.infer<typeof checkoutSchema>;

export default function StripeCheckoutContent() {
  return (
    <Suspense>
      <StripeCheckoutInner />
    </Suspense>
  );
}

function StripeCheckoutInner() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  const {
    event,
    selectedTier,
    quantity,
    promoValidation,
    getTotal,
    clearCheckout,
  } = useCheckoutStore();

  const purchaseMutation = usePurchaseMutation(event?.id || 0);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
  } = useForm<CheckoutFormData>({
    resolver: zodResolver(checkoutSchema),
    mode: "onChange",
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <CheckoutLoader />;
  }

  if (!event || !selectedTier) {
    return <EmptyCart />;
  }

  const onSubmit = async (data: CheckoutFormData) => {
    setIsProcessing(true);

    // Simulate processing animation
    await new Promise(resolve => setTimeout(resolve, 2000));

    try {
      const result = await purchaseMutation.mutateAsync({
        ticket_tier_id: selectedTier.id,
        email: data.email,
        name: data.name,
        phone: data.phone || undefined,
        quantity,
        promo_code: promoValidation?.code || undefined,
      });

      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      } else if (result.tickets) {
        const ticketIds = result.tickets.map((t) => t.id).join(",");
        clearCheckout();
        router.push(`/success?tickets=${ticketIds}`);
      }
    } catch (err) {
      console.error("Purchase failed:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  const total = getTotal();
  const subtotal = selectedTier.price * quantity;
  const discount = promoValidation ? subtotal - total : 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Stripe-style Header */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href={`/events/${event.id}`}>
              <button className="flex items-center text-gray-600 hover:text-gray-900 transition-colors">
                <ArrowLeft className="mr-2 h-4 w-4" />
                <span className="hidden sm:inline">Back</span>
              </button>
            </Link>

            <div className="flex items-center space-x-2">
              <Shield className="h-4 w-4 text-green-600" />
              <span className="text-sm text-gray-600">Secure Checkout</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Checkout Form - Left 2 cols */}
          <div className="lg:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <h1 className="text-3xl font-bold text-gray-900 mb-8">
                Complete your purchase
              </h1>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
                {/* Contact Information */}
                <section className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                  <h2 className="text-lg font-semibold mb-4 flex items-center">
                    <Mail className="mr-2 h-5 w-5 text-gray-400" />
                    Contact Information
                  </h2>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Email
                      </label>
                      <div className="relative">
                        <input
                          {...register("email")}
                          type="email"
                          className={cn(
                            "w-full px-4 py-3 rounded-lg border transition-all",
                            "focus:outline-none focus:ring-2 focus:ring-blue-500",
                            errors.email ? "border-red-500" : "border-gray-200",
                            focusedField === "email" && "border-blue-500"
                          )}
                          placeholder="your@email.com"
                          onFocus={() => setFocusedField("email")}
                          onBlur={() => setFocusedField(null)}
                        />
                        {errors.email && (
                          <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Full Name
                        </label>
                        <input
                          {...register("name")}
                          type="text"
                          className={cn(
                            "w-full px-4 py-3 rounded-lg border transition-all",
                            "focus:outline-none focus:ring-2 focus:ring-blue-500",
                            errors.name ? "border-red-500" : "border-gray-200"
                          )}
                          placeholder="John Doe"
                        />
                        {errors.name && (
                          <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Phone (Optional)
                        </label>
                        <input
                          {...register("phone")}
                          type="tel"
                          className="w-full px-4 py-3 rounded-lg border border-gray-200 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="+1 (555) 123-4567"
                        />
                      </div>
                    </div>
                  </div>
                </section>

                {/* Payment Information */}
                <section className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                  <h2 className="text-lg font-semibold mb-4 flex items-center">
                    <CreditCard className="mr-2 h-5 w-5 text-gray-400" />
                    Payment Details
                  </h2>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Card Number
                      </label>
                      <div className="relative">
                        <input
                          {...register("cardNumber")}
                          type="text"
                          maxLength={16}
                          className={cn(
                            "w-full px-4 py-3 pr-12 rounded-lg border transition-all",
                            "focus:outline-none focus:ring-2 focus:ring-blue-500",
                            errors.cardNumber ? "border-red-500" : "border-gray-200"
                          )}
                          placeholder="1234 5678 9012 3456"
                        />
                        <div className="absolute right-3 top-3.5">
                          <CreditCard className="h-5 w-5 text-gray-400" />
                        </div>
                        {errors.cardNumber && (
                          <p className="mt-1 text-sm text-red-600">{errors.cardNumber.message}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Expiry Date
                        </label>
                        <input
                          {...register("expiry")}
                          type="text"
                          maxLength={5}
                          className={cn(
                            "w-full px-4 py-3 rounded-lg border transition-all",
                            "focus:outline-none focus:ring-2 focus:ring-blue-500",
                            errors.expiry ? "border-red-500" : "border-gray-200"
                          )}
                          placeholder="MM/YY"
                        />
                        {errors.expiry && (
                          <p className="mt-1 text-sm text-red-600">{errors.expiry.message}</p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          CVC
                        </label>
                        <input
                          {...register("cvc")}
                          type="text"
                          maxLength={4}
                          className={cn(
                            "w-full px-4 py-3 rounded-lg border transition-all",
                            "focus:outline-none focus:ring-2 focus:ring-blue-500",
                            errors.cvc ? "border-red-500" : "border-gray-200"
                          )}
                          placeholder="123"
                        />
                        {errors.cvc && (
                          <p className="mt-1 text-sm text-red-600">{errors.cvc.message}</p>
                        )}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Name on Card
                      </label>
                      <input
                        {...register("billingName")}
                        type="text"
                        className={cn(
                          "w-full px-4 py-3 rounded-lg border transition-all",
                          "focus:outline-none focus:ring-2 focus:ring-blue-500",
                          errors.billingName ? "border-red-500" : "border-gray-200"
                        )}
                        placeholder="John Doe"
                      />
                      {errors.billingName && (
                        <p className="mt-1 text-sm text-red-600">{errors.billingName.message}</p>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Country
                        </label>
                        <select
                          {...register("country")}
                          className="w-full px-4 py-3 rounded-lg border border-gray-200 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="US">United States</option>
                          <option value="CA">Canada</option>
                          <option value="GB">United Kingdom</option>
                          <option value="AU">Australia</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          ZIP Code
                        </label>
                        <input
                          {...register("zip")}
                          type="text"
                          className={cn(
                            "w-full px-4 py-3 rounded-lg border transition-all",
                            "focus:outline-none focus:ring-2 focus:ring-blue-500",
                            errors.zip ? "border-red-500" : "border-gray-200"
                          )}
                          placeholder="10001"
                        />
                        {errors.zip && (
                          <p className="mt-1 text-sm text-red-600">{errors.zip.message}</p>
                        )}
                      </div>
                    </div>
                  </div>
                </section>

                {/* Submit Button */}
                <motion.button
                  type="submit"
                  disabled={isProcessing || !isValid}
                  className={cn(
                    "w-full py-4 px-6 rounded-lg font-semibold text-white transition-all",
                    "transform hover:scale-[1.02] active:scale-[0.98]",
                    isProcessing || !isValid
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-lg"
                  )}
                  whileTap={{ scale: 0.98 }}
                >
                  <AnimatePresence mode="wait">
                    {isProcessing ? (
                      <motion.div
                        key="processing"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center justify-center"
                      >
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-3" />
                        Processing...
                      </motion.div>
                    ) : (
                      <motion.div
                        key="pay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center justify-center"
                      >
                        <Lock className="mr-2 h-5 w-5" />
                        Pay ${(total / 100).toFixed(2)}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.button>

                {/* Security Badge */}
                <div className="flex items-center justify-center space-x-6 text-sm text-gray-500">
                  <div className="flex items-center">
                    <Shield className="mr-1 h-4 w-4 text-green-600" />
                    SSL Encrypted
                  </div>
                  <div className="flex items-center">
                    <Lock className="mr-1 h-4 w-4 text-green-600" />
                    Secure Payment
                  </div>
                </div>
              </form>
            </motion.div>
          </div>

          {/* Order Summary - Right col */}
          <div className="lg:sticky lg:top-24 h-fit">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
              className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
            >
              <h2 className="text-lg font-semibold mb-4">Order Summary</h2>

              {/* Event Details */}
              <div className="space-y-4 pb-4 border-b border-gray-200">
                <div className="flex items-start space-x-3">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <Ticket className="h-5 w-5 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{event.name}</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {selectedTier.name}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center text-sm text-gray-600">
                    <Calendar className="mr-2 h-4 w-4" />
                    {new Date(event.event_date + 'T' + event.event_time).toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <MapPin className="mr-2 h-4 w-4" />
                    {event.venue?.name}
                  </div>
                </div>
              </div>

              {/* Pricing Breakdown */}
              <div className="py-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    {selectedTier.name} × {quantity}
                  </span>
                  <span className="font-medium">${(subtotal / 100).toFixed(2)}</span>
                </div>

                {discount > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-green-600">Promo discount</span>
                    <span className="text-green-600">-${(discount / 100).toFixed(2)}</span>
                  </div>
                )}

                <div className="pt-3 border-t border-gray-200">
                  <div className="flex justify-between">
                    <span className="text-lg font-semibold">Total</span>
                    <span className="text-lg font-bold text-blue-600">
                      ${(total / 100).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Trust Badges */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="space-y-3">
                  <div className="flex items-center text-sm text-gray-600">
                    <CheckCircle2 className="mr-2 h-4 w-4 text-green-600" />
                    Instant ticket delivery
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <CheckCircle2 className="mr-2 h-4 w-4 text-green-600" />
                    100% secure checkout
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <CheckCircle2 className="mr-2 h-4 w-4 text-green-600" />
                    24/7 customer support
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CheckoutLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-pulse space-y-4">
        <div className="h-12 w-12 bg-gray-200 rounded-full mx-auto" />
        <div className="h-4 w-32 bg-gray-200 rounded mx-auto" />
      </div>
    </div>
  );
}

function EmptyCart() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center max-w-md"
      >
        <div className="mb-6">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gray-100">
            <Ticket className="h-10 w-10 text-gray-400" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your cart is empty</h1>
        <p className="text-gray-600 mb-8">
          Browse our events and find something amazing to attend.
        </p>
        <Link href="/events">
          <button className="inline-flex items-center px-6 py-3 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors">
            Browse Events
            <ChevronRight className="ml-2 h-4 w-4" />
          </button>
        </Link>
      </motion.div>
    </div>
  );
}