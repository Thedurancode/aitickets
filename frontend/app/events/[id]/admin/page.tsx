"use client";

import { useParams, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { ShieldAlert, Loader2 } from "lucide-react";
import { useAdminDashboard } from "@/lib/queries";
import { AdminHeader } from "@/components/admin/admin-header";
import { StatsOverview } from "@/components/admin/stats-overview";
import { TierBreakdown } from "@/components/admin/tier-breakdown";
import { EventSettings } from "@/components/admin/event-settings";
import { ImageUpload } from "@/components/admin/image-upload";
import { ActivityFeed } from "@/components/admin/activity-feed";
import { FadeIn } from "@/components/layout/page-transition";

export default function EventAdminPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const eventId = Number(params.id);
  const token = searchParams.get("token") || "";

  const { data, isLoading, error } = useAdminDashboard(eventId, token);

  if (!token) {
    return (
      <div className="container py-16 max-w-3xl text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <ShieldAlert className="h-16 w-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-foreground mb-2">
            Access Denied
          </h1>
          <p className="text-muted-foreground">
            A valid admin token is required to access this page.
          </p>
        </motion.div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container py-16 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container py-16 max-w-3xl text-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <ShieldAlert className="h-16 w-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-foreground mb-2">
            Unable to Load Dashboard
          </h1>
          <p className="text-muted-foreground">
            {error instanceof Error
              ? error.message
              : "The admin link may be invalid or expired."}
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="container py-8 md:py-12 max-w-6xl">
      <FadeIn>
        <AdminHeader data={data} />
      </FadeIn>

      <StatsOverview data={data} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <FadeIn delay={0.1}>
            <TierBreakdown tiers={data.tiers} />
          </FadeIn>
          <FadeIn delay={0.2}>
            <EventSettings data={data} eventId={eventId} token={token} />
          </FadeIn>
        </div>

        <div className="space-y-6">
          <FadeIn delay={0.15}>
            <ImageUpload
              currentImageUrl={data.event.image_url}
              eventId={eventId}
              token={token}
            />
          </FadeIn>
          <FadeIn delay={0.25}>
            <ActivityFeed activities={data.recent_activity} />
          </FadeIn>
        </div>
      </div>
    </div>
  );
}
