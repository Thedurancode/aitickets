import type { Metadata } from "next";
import NextGenCheckoutContent from "./next-gen-checkout";

export const metadata: Metadata = {
  title: "Next-Gen Checkout | AI Tickets",
  description: "Experience the future of secure payments with our AI-powered checkout.",
  robots: { index: false, follow: false },
};

export default function CheckoutPage() {
  return <NextGenCheckoutContent />;
}
