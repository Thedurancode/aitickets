"use client";

import { motion } from "framer-motion";
import { DollarSign, Ticket, Eye, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { AdminDashboardData } from "@/types/api";

interface StatsOverviewProps {
  data: AdminDashboardData;
}

const stats = [
  {
    key: "sold",
    label: "Tickets Sold",
    icon: Ticket,
    getValue: (d: AdminDashboardData) => d.total_tickets_sold.toString(),
    color: "text-primary",
    bg: "bg-primary/10",
  },
  {
    key: "revenue",
    label: "Revenue",
    icon: DollarSign,
    getValue: (d: AdminDashboardData) =>
      `$${(d.total_revenue_cents / 100).toFixed(2)}`,
    color: "text-green-400",
    bg: "bg-green-500/10",
  },
  {
    key: "views",
    label: "Page Views",
    icon: Eye,
    getValue: (d: AdminDashboardData) => d.analytics.total_views.toString(),
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    key: "visitors",
    label: "Unique Visitors",
    icon: Users,
    getValue: (d: AdminDashboardData) =>
      d.analytics.unique_visitors.toString(),
    color: "text-purple-400",
    bg: "bg-purple-500/10",
  },
];

export function StatsOverview({ data }: StatsOverviewProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.key}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
        >
          <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${stat.bg}`}>
                  <stat.icon className={`h-4 w-4 ${stat.color}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">
                    {stat.getValue(data)}
                  </p>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
