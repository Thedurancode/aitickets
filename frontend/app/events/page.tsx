import type { Metadata } from "next";
import { BreadcrumbJsonLd } from "@/components/seo/breadcrumb-json-ld";
import EventsPageContent from "./events-page-content";

export const metadata: Metadata = {
  title: "Browse Events",
  description:
    "Discover and purchase tickets to the best events happening near you. Browse concerts, sports, theater, and more.",
  openGraph: {
    title: "Browse Events",
    description: "Discover and purchase tickets to the best events near you.",
  },
};

export default function EventsPage() {
  return (
    <>
      <BreadcrumbJsonLd
        items={[
          { name: "Home", href: "/" },
          { name: "Events" },
        ]}
      />
      <EventsPageContent />
    </>
  );
}
