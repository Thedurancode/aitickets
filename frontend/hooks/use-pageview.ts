"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

export function usePageView(options?: { eventId?: number; page?: string }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const page = options?.page || pathname.split("/").pop() || "unknown";
    api.analytics.trackPageView({
      event_id: options?.eventId,
      page,
      referrer: typeof document !== "undefined" ? document.referrer : undefined,
      utm_source: searchParams.get("utm_source") || undefined,
      utm_medium: searchParams.get("utm_medium") || undefined,
      utm_campaign: searchParams.get("utm_campaign") || undefined,
    }).catch(() => {});
  }, [pathname]);
}
