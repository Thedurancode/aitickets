import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { EventDetail, TicketTier, PromoValidationResponse } from "@/types/api";

interface BuyerInfo {
  name: string;
  email: string;
  phone: string;
}

interface CheckoutState {
  // Event & Ticket Selection
  event: EventDetail | null;
  selectedTier: TicketTier | null;
  quantity: number;

  // Promo Code
  promoCode: string | null;
  promoValidation: PromoValidationResponse | null;

  // Buyer Info
  buyerInfo: BuyerInfo;

  // Actions
  setEvent: (event: EventDetail) => void;
  selectTier: (tier: TicketTier | null) => void;
  setQuantity: (quantity: number) => void;
  incrementQuantity: () => void;
  decrementQuantity: () => void;
  setPromoCode: (code: string | null) => void;
  setPromoValidation: (validation: PromoValidationResponse | null) => void;
  setBuyerInfo: (info: Partial<BuyerInfo>) => void;
  clearCheckout: () => void;

  // Computed
  getSubtotal: () => number;
  getDiscount: () => number;
  getTotal: () => number;
}

const initialBuyerInfo: BuyerInfo = {
  name: "",
  email: "",
  phone: "",
};

export const useCheckoutStore = create<CheckoutState>()(
  persist(
    (set, get) => ({
      event: null,
      selectedTier: null,
      quantity: 1,
      promoCode: null,
      promoValidation: null,
      buyerInfo: initialBuyerInfo,

      setEvent: (event) => set({ event }),

      selectTier: (tier) =>
        set({
          selectedTier: tier,
          quantity: 1,
          promoCode: null,
          promoValidation: null,
        }),

      setQuantity: (quantity) => {
        const tier = get().selectedTier;
        if (!tier) return;
        const maxQuantity = Math.min(tier.tickets_remaining, 10);
        const clampedQuantity = Math.max(1, Math.min(quantity, maxQuantity));
        set({ quantity: clampedQuantity });
      },

      incrementQuantity: () => {
        const { quantity, selectedTier } = get();
        if (!selectedTier) return;
        const maxQuantity = Math.min(selectedTier.tickets_remaining, 10);
        if (quantity < maxQuantity) {
          set({ quantity: quantity + 1 });
        }
      },

      decrementQuantity: () => {
        const { quantity } = get();
        if (quantity > 1) {
          set({ quantity: quantity - 1 });
        }
      },

      setPromoCode: (code) => set({ promoCode: code }),

      setPromoValidation: (validation) => set({ promoValidation: validation }),

      setBuyerInfo: (info) =>
        set((state) => ({
          buyerInfo: { ...state.buyerInfo, ...info },
        })),

      clearCheckout: () =>
        set({
          event: null,
          selectedTier: null,
          quantity: 1,
          promoCode: null,
          promoValidation: null,
          buyerInfo: initialBuyerInfo,
        }),

      getSubtotal: () => {
        const { selectedTier, quantity } = get();
        if (!selectedTier) return 0;
        return selectedTier.price * quantity;
      },

      getDiscount: () => {
        const { promoValidation, quantity } = get();
        if (!promoValidation?.valid) return 0;
        return promoValidation.discount_amount_cents * quantity;
      },

      getTotal: () => {
        const subtotal = get().getSubtotal();
        const discount = get().getDiscount();
        const rawTotal = Math.max(0, subtotal - discount);
        // Stripe minimum is $0.50 (50 cents) - if below, make it free
        const STRIPE_MINIMUM_CENTS = 50;
        return rawTotal > 0 && rawTotal < STRIPE_MINIMUM_CENTS ? 0 : rawTotal;
      },
    }),
    {
      name: "checkout-storage",
      partialize: (state) => ({
        buyerInfo: state.buyerInfo,
        event: state.event,
        selectedTier: state.selectedTier,
        quantity: state.quantity,
        promoCode: state.promoCode,
        promoValidation: state.promoValidation,
      }),
    }
  )
);
