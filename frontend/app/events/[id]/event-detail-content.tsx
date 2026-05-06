"use client";

import { Suspense, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Music, MapPin, Users, Instagram, Twitter, Facebook, Youtube, Award, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useEvent, usePurchaseMutation } from "@/lib/queries";
import { useQuery } from "@tanstack/react-query";
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

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { data: artist } = useQuery({
    queryKey: ["artist", eventId],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/events/${eventId}/artist`);
      if (!res.ok) return null;
      const data = await res.json();
      return data?.has_artist ? data : null;
    },
    enabled: !!eventId,
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
    <div className="container px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
      {/* Back button */}
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        className="mb-4 sm:mb-6"
      >
        <Link href="/events">
          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Events
          </Button>
        </Link>
      </motion.div>

      <div className="grid gap-4 sm:gap-6 lg:grid-cols-3 lg:gap-8">
        {/* Main content */}
        <div className="lg:col-span-2">
          {eventLoading ? <EventHeroSkeleton /> : event && <EventHero event={event} />}

          {/* Artist Section */}
          {artist && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card className="mt-4 sm:mt-6 bg-card/50 border-white/5 backdrop-blur-sm overflow-hidden">
                <div className="flex flex-col sm:flex-row">
                  {/* Artist Image */}
                  {(artist.primary_image_url || artist.spotify_image_url) && (
                    <div className="sm:w-48 shrink-0">
                      <img
                        src={artist.primary_image_url || artist.spotify_image_url}
                        alt={artist.name}
                        className="w-full h-48 sm:h-full object-cover"
                      />
                    </div>
                  )}

                  <div className="flex-1 p-4 sm:p-6 space-y-4">
                    {/* Name & Genre */}
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Music className="h-4 w-4 text-primary" />
                        <span className="text-xs text-primary font-medium uppercase tracking-wider">Artist</span>
                      </div>
                      <h3 className="text-xl font-bold">{artist.name}</h3>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {artist.genre && <span className="text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">{artist.genre}</span>}
                        {artist.sub_genres?.map((g: string) => (
                          <span key={g} className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-muted-foreground border border-white/10">{g}</span>
                        ))}
                      </div>
                    </div>

                    {/* Bio */}
                    {artist.bio && (
                      <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3">{artist.bio}</p>
                    )}

                    {/* Social Stats */}
                    <div className="flex flex-wrap gap-3">
                      {artist.instagram_handle && (
                        <a href={`https://instagram.com/${artist.instagram_handle.replace('@','')}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
                          <Instagram className="h-3.5 w-3.5" />
                          {artist.instagram_handle}
                          {artist.instagram_followers > 0 && <span className="text-primary font-medium">{(artist.instagram_followers / 1000000).toFixed(1)}M</span>}
                        </a>
                      )}
                      {artist.twitter_handle && (
                        <a href={`https://twitter.com/${artist.twitter_handle.replace('@','')}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
                          <Twitter className="h-3.5 w-3.5" />
                          {artist.twitter_handle}
                        </a>
                      )}
                      {artist.facebook_page && (
                        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Facebook className="h-3.5 w-3.5" />
                          {artist.facebook_page}
                        </span>
                      )}
                      {artist.youtube_subscribers > 0 && (
                        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Youtube className="h-3.5 w-3.5" />
                          {(artist.youtube_subscribers / 1000000).toFixed(1)}M subs
                        </span>
                      )}
                    </div>

                    {/* Top Tracks */}
                    {artist.spotify_top_tracks?.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground font-medium mb-1.5">Top Tracks</p>
                        <div className="flex flex-wrap gap-1.5">
                          {artist.spotify_top_tracks.slice(0, 6).map((track: string, i: number) => (
                            <span key={i} className="text-xs px-2 py-0.5 rounded bg-white/5 text-muted-foreground">
                              {track}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Similar Artists & Achievements in a row */}
                    <div className="flex flex-wrap gap-4 text-xs">
                      {artist.similar_artists?.length > 0 && (
                        <div>
                          <p className="text-muted-foreground font-medium mb-1">Similar Artists</p>
                          <p className="text-foreground">{artist.similar_artists.slice(0, 4).join(' · ')}</p>
                        </div>
                      )}
                      {artist.primary_markets?.length > 0 && (
                        <div>
                          <p className="text-muted-foreground font-medium mb-1 flex items-center gap-1"><MapPin className="h-3 w-3" /> Top Markets</p>
                          <p className="text-foreground">{artist.primary_markets.slice(0, 4).join(' · ')}</p>
                        </div>
                      )}
                      {artist.typical_venue_size && (
                        <div>
                          <p className="text-muted-foreground font-medium mb-1 flex items-center gap-1"><TrendingUp className="h-3 w-3" /> Venue Size</p>
                          <p className="text-foreground capitalize">{artist.typical_venue_size}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          )}
        </div>

        {/* Ticket purchase panel */}
        <div className="lg:col-span-1">
          <div className="lg:sticky lg:top-20">
            <Card className="bg-card/50 border-white/5 backdrop-blur-sm">
              <CardHeader className="px-4 sm:px-6">
                <CardTitle>Get Tickets</CardTitle>
              </CardHeader>
              <CardContent className="px-4 sm:px-6 space-y-4 sm:space-y-6">
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
                        className="space-y-4 sm:space-y-6"
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
