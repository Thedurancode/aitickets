"use client";

import { Suspense, useState, useMemo, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ChevronLeft, ChevronRight, Calendar, MapPin, Ticket, Play } from "lucide-react";
import Link from "next/link";
import { useEvents, useCategories } from "@/lib/queries";
import { usePageView } from "@/hooks/use-pageview";
import { EventGrid } from "@/components/events/event-grid";
import { CategoryFilter } from "@/components/events/category-filter";
import { SearchInput } from "@/components/events/search-input";
import { FadeIn } from "@/components/layout/page-transition";
import { Button } from "@/components/ui/button";

// Hero video/image slides
const HERO_SLIDES = [
  {
    video: "https://cdn.coverr.co/videos/coverr-crowd-at-a-concert-2330/1080p.mp4",
    fallback: "https://images.unsplash.com/photo-1540039155733-5bb30b53aa14?w=1920&q=80",
    title: "Live Concerts",
    subtitle: "Feel the energy of live music",
    cta: "Browse Concerts",
    color: "from-purple-900/80",
  },
  {
    video: "https://cdn.coverr.co/videos/coverr-night-club-crowd-9643/1080p.mp4",
    fallback: "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=1920&q=80",
    title: "Nightlife & Parties",
    subtitle: "Your night starts here",
    cta: "Find Events",
    color: "from-blue-900/80",
  },
  {
    video: "https://cdn.coverr.co/videos/coverr-people-dancing-at-a-party-6930/1080p.mp4",
    fallback: "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=1920&q=80",
    title: "Unforgettable Experiences",
    subtitle: "Make memories that last forever",
    cta: "Get Tickets",
    color: "from-rose-900/80",
  },
];

function HeroSlider() {
  const [current, setCurrent] = useState(0);
  const [videoLoaded, setVideoLoaded] = useState(false);

  const next = useCallback(() => setCurrent((c) => (c + 1) % HERO_SLIDES.length), []);
  const prev = useCallback(() => setCurrent((c) => (c - 1 + HERO_SLIDES.length) % HERO_SLIDES.length), []);

  // Auto-advance
  useEffect(() => {
    const timer = setInterval(next, 6000);
    return () => clearInterval(timer);
  }, [next]);

  const slide = HERO_SLIDES[current];

  return (
    <div className="relative w-full h-[70vh] min-h-[500px] max-h-[700px] overflow-hidden -mt-16">
      {/* Video/Image Background */}
      <AnimatePresence mode="wait">
        <motion.div
          key={current}
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1 }}
          className="absolute inset-0"
        >
          <video
            src={slide.video}
            autoPlay
            muted
            loop
            playsInline
            onLoadedData={() => setVideoLoaded(true)}
            className="absolute inset-0 w-full h-full object-cover"
          />
          {/* Fallback image */}
          {!videoLoaded && (
            <img src={slide.fallback} alt="" className="absolute inset-0 w-full h-full object-cover" />
          )}
        </motion.div>
      </AnimatePresence>

      {/* Gradient overlay */}
      <div className={`absolute inset-0 bg-gradient-to-t ${slide.color} via-black/40 to-black/60`} />
      <div className="absolute inset-0 bg-gradient-to-r from-black/60 via-transparent to-transparent" />

      {/* Content */}
      <div className="relative z-10 h-full flex items-center">
        <div className="container px-4 sm:px-6 lg:px-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={current}
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="max-w-2xl"
            >
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 mb-6"
              >
                <Play className="h-3 w-3 text-white fill-white" />
                <span className="text-xs text-white/90 font-medium tracking-wider uppercase">Now Showing</span>
              </motion.div>

              <h1 className="text-5xl sm:text-6xl md:text-7xl font-black text-white mb-4 leading-none tracking-tight">
                {slide.title}
              </h1>
              <p className="text-xl sm:text-2xl text-white/80 mb-8 font-light">
                {slide.subtitle}
              </p>

              <div className="flex flex-wrap gap-4">
                <Link href="#events">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="px-8 py-4 bg-white text-black font-bold text-lg rounded-full hover:bg-white/90 transition-all shadow-2xl shadow-white/20"
                  >
                    {slide.cta}
                  </motion.button>
                </Link>
                <Link href="#events">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="px-8 py-4 bg-white/10 backdrop-blur-md text-white font-semibold text-lg rounded-full border border-white/30 hover:bg-white/20 transition-all"
                  >
                    <Ticket className="inline h-5 w-5 mr-2" />
                    View All Events
                  </motion.button>
                </Link>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation arrows */}
      <button onClick={prev} className="absolute left-4 top-1/2 -translate-y-1/2 z-20 p-3 rounded-full bg-black/30 backdrop-blur-sm text-white/80 hover:bg-black/50 hover:text-white transition-all">
        <ChevronLeft className="h-6 w-6" />
      </button>
      <button onClick={next} className="absolute right-4 top-1/2 -translate-y-1/2 z-20 p-3 rounded-full bg-black/30 backdrop-blur-sm text-white/80 hover:bg-black/50 hover:text-white transition-all">
        <ChevronRight className="h-6 w-6" />
      </button>

      {/* Slide indicators */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex gap-2">
        {HERO_SLIDES.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={`h-1.5 rounded-full transition-all duration-500 ${
              i === current ? "w-10 bg-white" : "w-4 bg-white/40 hover:bg-white/60"
            }`}
          />
        ))}
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-background to-transparent" />
    </div>
  );
}

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
    <>
      {/* Hero Video Slider */}
      <HeroSlider />

      <div id="events" className="container px-4 sm:px-6 lg:px-8 py-8 md:py-12">

      <FadeIn delay={0.1}>
        <div className="space-y-3 sm:space-y-4 mb-6 sm:mb-10">
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
    </>
  );
}
