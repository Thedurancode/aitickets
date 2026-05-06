"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  User as UserIcon,
  Mail,
  Phone,
  Calendar,
  Ticket,
  LogOut,
  Edit3,
  Bell,
  MessageSquare,
  Megaphone,
  Check,
  X,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { auth, type User } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TicketItem {
  id: number;
  status: string;
  created_at: string;
  ticket_tier?: {
    name: string;
    price: number;
    event?: {
      name: string;
      event_date: string;
      event_time?: string;
    };
  };
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [saving, setSaving] = useState(false);

  // Notification prefs (local state, synced with user)
  const [emailNotif, setEmailNotif] = useState(true);
  const [smsNotif, setSmsNotif] = useState(false);
  const [marketingNotif, setMarketingNotif] = useState(false);

  const loadData = useCallback(async () => {
    if (!auth.isLoggedIn()) {
      router.push("/login");
      return;
    }

    try {
      const userData = await auth.getUser();
      setUser(userData);
      setEditName(userData.name);
      setEditPhone(userData.phone || "");
      setEmailNotif(userData.email_opt_in ?? true);
      setSmsNotif(userData.sms_opt_in ?? false);
      setMarketingNotif(userData.marketing_opt_in ?? false);

      // Fetch user tickets by email
      try {
        const res = await fetch(
          `${API_BASE}/api/tickets/by-email?email=${encodeURIComponent(userData.email)}`
        );
        if (res.ok) {
          const data = await res.json();
          setTickets(data);
        }
      } catch {
        // Tickets fetch is non-critical
      }
    } catch {
      auth.logout();
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleLogout = () => {
    auth.logout();
    router.push("/login");
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const updated = await auth.updateProfile({
        name: editName,
        phone: editPhone,
      });
      setUser(updated);
      setEditing(false);
    } catch {
      // keep editing open on error
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!user) return null;

  const memberSince = user.created_at
    ? new Date(user.created_at).toLocaleDateString("en-US", {
        month: "long",
        year: "numeric",
      })
    : "N/A";

  const statusColor: Record<string, string> = {
    PAID: "bg-green-500/10 text-green-400 border-green-500/20",
    PENDING: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    CANCELLED: "bg-red-500/10 text-red-400 border-red-500/20",
    USED: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Profile Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="bg-card/50 border-white/10 backdrop-blur-sm">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-start gap-6">
              {/* Avatar */}
              <div className="flex-shrink-0">
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.name}
                    className="h-20 w-20 rounded-full object-cover ring-2 ring-white/10"
                  />
                ) : (
                  <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center ring-2 ring-white/10">
                    <UserIcon className="h-10 w-10 text-primary" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                {editing ? (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-foreground text-xs">Name</Label>
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="bg-background/50 border-white/10 mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-foreground text-xs">Phone</Label>
                      <Input
                        value={editPhone}
                        onChange={(e) => setEditPhone(e.target.value)}
                        className="bg-background/50 border-white/10 mt-1"
                        placeholder="(optional)"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleSaveProfile} disabled={saving}>
                        {saving ? "Saving..." : "Save"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-white/10"
                        onClick={() => setEditing(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 mb-1">
                      <h2 className="text-xl font-bold text-foreground">{user.name}</h2>
                      {user.is_admin && (
                        <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20 text-xs">
                          <Shield className="h-3 w-3 mr-1" />
                          Admin
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                      <Mail className="h-3.5 w-3.5" />
                      {user.email}
                    </div>
                    {user.phone && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                        <Phone className="h-3.5 w-3.5" />
                        {user.phone}
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5" />
                      Member since {memberSince}
                    </div>
                  </>
                )}
              </div>

              {/* Actions */}
              {!editing && (
                <div className="flex gap-2 sm:flex-col">
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-white/10"
                    onClick={() => setEditing(true)}
                  >
                    <Edit3 className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-white/10 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    onClick={handleLogout}
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* My Tickets */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <Card className="bg-card/50 border-white/10 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-foreground flex items-center gap-2">
              <Ticket className="h-5 w-5 text-primary" />
              My Tickets
            </CardTitle>
          </CardHeader>
          <CardContent>
            {tickets.length === 0 ? (
              <p className="text-muted-foreground text-sm py-4 text-center">
                No tickets yet. Browse events to get started!
              </p>
            ) : (
              <div className="space-y-3">
                {tickets.map((ticket, idx) => (
                  <motion.div
                    key={ticket.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex items-center justify-between p-3 rounded-lg bg-background/30 border border-white/5"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-foreground text-sm truncate">
                        {ticket.ticket_tier?.event?.name || "Event"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {ticket.ticket_tier?.name || "General"}{" "}
                        {ticket.ticket_tier?.event?.event_date
                          ? `- ${new Date(ticket.ticket_tier.event.event_date).toLocaleDateString()}`
                          : ""}
                      </p>
                    </div>
                    <Badge
                      className={`text-xs ${statusColor[ticket.status] || "bg-gray-500/10 text-gray-400 border-gray-500/20"}`}
                    >
                      {ticket.status}
                    </Badge>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Notification Preferences */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
      >
        <Card className="bg-card/50 border-white/10 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-foreground flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              Notification Preferences
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ToggleRow
              icon={<Mail className="h-4 w-4" />}
              label="Email notifications"
              description="Ticket confirmations, event reminders"
              checked={emailNotif}
              onChange={setEmailNotif}
            />
            <ToggleRow
              icon={<MessageSquare className="h-4 w-4" />}
              label="SMS notifications"
              description="Text message alerts for your events"
              checked={smsNotif}
              onChange={setSmsNotif}
            />
            <ToggleRow
              icon={<Megaphone className="h-4 w-4" />}
              label="Marketing emails"
              description="New events, promotions, and recommendations"
              checked={marketingNotif}
              onChange={setMarketingNotif}
            />
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

function ToggleRow({
  icon,
  label,
  description,
  checked,
  onChange,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-3">
        <div className="text-muted-foreground">{icon}</div>
        <div>
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? "bg-primary" : "bg-white/10"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}
