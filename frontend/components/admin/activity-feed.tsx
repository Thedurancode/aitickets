"use client";

import { motion } from "framer-motion";
import { ShoppingCart, ScanLine } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AdminActivity } from "@/types/api";

interface ActivityFeedProps {
  activities: AdminActivity[];
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-lg">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {activities.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            No activity yet
          </p>
        ) : (
          <div className="space-y-3">
            {activities.map((activity, i) => (
              <motion.div
                key={`${activity.name}-${activity.time}-${i}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center gap-3 text-sm"
              >
                <div
                  className={`p-1.5 rounded-md ${
                    activity.type === "check_in"
                      ? "bg-blue-500/10"
                      : "bg-green-500/10"
                  }`}
                >
                  {activity.type === "check_in" ? (
                    <ScanLine className="h-3.5 w-3.5 text-blue-400" />
                  ) : (
                    <ShoppingCart className="h-3.5 w-3.5 text-green-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-foreground">
                    {activity.name}
                  </span>
                  <span className="text-muted-foreground">
                    {" "}
                    {activity.type === "check_in"
                      ? "checked in"
                      : "purchased"}{" "}
                  </span>
                  <span className="text-foreground">{activity.tier}</span>
                </div>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {timeAgo(activity.time)}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
