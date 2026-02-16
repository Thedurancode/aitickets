import type { Metadata } from "next";
import MyTicketsContent from "./my-tickets-content";

export const metadata: Metadata = {
  title: "My Tickets",
  description: "Look up and manage your event tickets.",
  robots: { index: false, follow: false },
};

export default function MyTicketsPage() {
  return <MyTicketsContent />;
}
