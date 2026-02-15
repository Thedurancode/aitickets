"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { EventListParams, PurchaseRequest } from "@/types/api";

// Query Keys
export const queryKeys = {
  events: {
    all: ["events"] as const,
    list: (params?: EventListParams) => ["events", "list", params] as const,
    detail: (id: number) => ["events", "detail", id] as const,
    tiers: (eventId: number) => ["events", "tiers", eventId] as const,
  },
  categories: {
    all: ["categories"] as const,
  },
  tickets: {
    detail: (id: number) => ["tickets", "detail", id] as const,
    byEmail: (email: string) => ["tickets", "by-email", email] as const,
  },
  admin: {
    dashboard: (eventId: number, token: string) => ["admin", "dashboard", eventId, token] as const,
  },
};

// Event Queries
export function useEvents(params?: EventListParams) {
  return useQuery({
    queryKey: queryKeys.events.list(params),
    queryFn: () => api.events.list(params),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useEvent(id: number, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: queryKeys.events.detail(id),
    queryFn: () => api.events.get(id),
    staleTime: options?.refetchInterval ? 1000 * 60 : 1000 * 60 * 5,
    enabled: !!id,
    refetchInterval: options?.refetchInterval,
    refetchIntervalInBackground: false,
  });
}

export function useEventTiers(eventId: number) {
  return useQuery({
    queryKey: queryKeys.events.tiers(eventId),
    queryFn: () => api.events.getTiers(eventId),
    staleTime: 1000 * 60, // 1 minute (availability changes more often)
    enabled: !!eventId,
  });
}

// Category Queries
export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories.all,
    queryFn: () => api.categories.list(),
    staleTime: 1000 * 60 * 30, // 30 minutes
  });
}

// Ticket Queries
export function useTicket(ticketId: number) {
  return useQuery({
    queryKey: queryKeys.tickets.detail(ticketId),
    queryFn: () => api.tickets.get(ticketId),
    enabled: !!ticketId,
  });
}

export function useTicketsByEmail(email: string) {
  return useQuery({
    queryKey: queryKeys.tickets.byEmail(email),
    queryFn: () => api.tickets.byEmail(email),
    enabled: !!email && email.includes("@"),
    staleTime: 1000 * 60 * 2,
  });
}

// Purchase Mutation
export function usePurchaseMutation(eventId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PurchaseRequest) => api.tickets.purchase(eventId, data),
    onSuccess: () => {
      // Invalidate event tiers to refresh availability
      queryClient.invalidateQueries({ queryKey: queryKeys.events.tiers(eventId) });
    },
  });
}

// Promo Validation Mutation
export function usePromoValidation() {
  return useMutation({
    mutationFn: ({ code, ticketTierId }: { code: string; ticketTierId: number }) =>
      api.promo.validate(code, ticketTierId),
  });
}

// Admin Queries
export function useAdminDashboard(eventId: number, token: string) {
  return useQuery({
    queryKey: queryKeys.admin.dashboard(eventId, token),
    queryFn: () => api.admin.getData(eventId, token),
    enabled: !!eventId && !!token,
    staleTime: 1000 * 30,
    refetchInterval: 1000 * 30,
    refetchIntervalInBackground: false,
  });
}

export function useAdminUpdateEvent(eventId: number, token: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.admin.updateEvent(eventId, token, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.dashboard(eventId, token) });
    },
  });
}

export function useAdminUploadImage(eventId: number, token: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.admin.uploadImage(eventId, token, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.dashboard(eventId, token) });
    },
  });
}
