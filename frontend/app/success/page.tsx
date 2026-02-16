import type { Metadata } from "next";
import SuccessContent from "./success-content";

export const metadata: Metadata = {
  title: "Purchase Confirmed",
  description: "Your tickets have been confirmed.",
  robots: { index: false, follow: false },
};

export default function SuccessPage() {
  return <SuccessContent />;
}
