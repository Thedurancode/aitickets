import type { Metadata } from "next";
import CheckoutContent from "./checkout-content";

export const metadata: Metadata = {
  title: "Checkout",
  description: "Complete your ticket purchase.",
  robots: { index: false, follow: false },
};

export default function CheckoutPage() {
  return <CheckoutContent />;
}
