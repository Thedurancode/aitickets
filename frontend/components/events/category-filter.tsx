"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { Category } from "@/types/api";

interface CategoryFilterProps {
  categories: Category[];
  selectedCategory: string | null;
  onSelectCategory: (category: string | null) => void;
  isLoading?: boolean;
}

export function CategoryFilter({
  categories,
  selectedCategory,
  onSelectCategory,
  isLoading,
}: CategoryFilterProps) {
  if (isLoading) {
    return (
      <div className="flex gap-2 overflow-x-auto no-scrollbar py-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-10 w-24 rounded-full shimmer flex-shrink-0"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="flex gap-2 overflow-x-auto no-scrollbar py-2 -mx-4 px-4 md:mx-0 md:px-0">
      <CategoryPill
        name="All"
        isSelected={selectedCategory === null}
        onClick={() => onSelectCategory(null)}
      />
      {categories.map((category) => (
        <CategoryPill
          key={category.id}
          name={category.name}
          color={category.color}
          isSelected={selectedCategory === category.name}
          onClick={() => onSelectCategory(category.name)}
        />
      ))}
    </div>
  );
}

interface CategoryPillProps {
  name: string;
  color?: string | null;
  isSelected: boolean;
  onClick: () => void;
}

function CategoryPill({ name, color, isSelected, onClick }: CategoryPillProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={cn(
        "relative px-5 py-2.5 rounded-full text-sm font-medium whitespace-nowrap transition-all flex-shrink-0 border",
        isSelected
          ? "text-white border-primary/50 glow-sm"
          : "text-muted-foreground hover:text-foreground bg-card/50 border-white/5 hover:border-white/10"
      )}
      style={
        isSelected
          ? { backgroundColor: color || "hsl(var(--primary))" }
          : {}
      }
    >
      {name}
    </motion.button>
  );
}
