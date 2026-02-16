"use client";

import { Suspense, useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useEvents, useCategories } from "@/lib/queries";
import { usePageView } from "@/hooks/use-pageview";
import { EventGrid } from "@/components/events/event-grid";
import { CategoryFilter } from "@/components/events/category-filter";
import { SearchInput } from "@/components/events/search-input";
import { FadeIn } from "@/components/layout/page-transition";

export default function EventsPageContent() {
  return (
    <Suspense>
      <EventsPageInner />
    </Suspense>
  );
}

function EventsPageInner() {
  usePageView({ page: "listing" });
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: events, isLoading: eventsLoading } = useEvents({
    category: selectedCategory || undefined,
  });

  const { data: categories, isLoading: categoriesLoading } = useCategories();

  // Client-side search filtering
  const filteredEvents = useMemo(() => {
    if (!events) return [];
    if (!searchQuery.trim()) return events;

    const query = searchQuery.toLowerCase();
    return events.filter(
      (event) =>
        event.name.toLowerCase().includes(query) ||
        event.description?.toLowerCase().includes(query) ||
        event.venue.name.toLowerCase().includes(query)
    );
  }, [events, searchQuery]);

  return (
    <div className="container py-8 md:py-12">
      <FadeIn>
        <div className="mb-10 text-center md:text-left">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-4"
          >
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm text-primary">Discover amazing events</span>
          </motion.div>
          <h1 className="text-4xl md:text-5xl font-bold mb-3 text-foreground">
            Find Your Next
            <br />
            <span className="text-muted-foreground">Experience</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl">
            Browse tickets to the best events happening near you
          </p>
        </div>
      </FadeIn>

      <FadeIn delay={0.1}>
        <div className="space-y-4 mb-10">
          <SearchInput
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search events, venues..."
          />
          <CategoryFilter
            categories={categories || []}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            isLoading={categoriesLoading}
          />
        </div>
      </FadeIn>

      <EventGrid events={filteredEvents} isLoading={eventsLoading} />
    </div>
  );
}
