"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Calendar, MapPin, Users, DollarSign, Ticket, Plus, Pencil, Trash2,
  Eye, EyeOff, TrendingUp, Lock, LogOut, BarChart3, Settings, Music,
  Loader2, Check, X, ExternalLink, Image as ImageIcon, Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_PASSWORD = "emprezario2024";

interface Event {
  id: number;
  name: string;
  description: string | null;
  event_date: string;
  event_time: string;
  doors_open_time: string | null;
  image_url: string | null;
  status: string;
  is_visible: boolean;
  venue_id: number;
  venue?: { name: string; address: string };
  ticket_tiers?: Array<{
    id: number;
    name: string;
    price: number;
    quantity_available: number;
    tickets_sold?: number;
  }>;
  created_at: string;
}

interface Venue {
  id: number;
  name: string;
  address: string | null;
  logo_url: string | null;
}

interface DashboardMetrics {
  total_events: number;
  total_tickets_sold: number;
  total_revenue_cents: number;
  active_events: number;
}

export default function AdminPage() {
  const [authed, setAuthed] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [events, setEvents] = useState<Event[]>([]);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"events" | "venues" | "analytics">("events");
  const [editingEvent, setEditingEvent] = useState<Event | null>(null);
  const [editForm, setEditForm] = useState<{
    name: string;
    description: string;
    event_date: string;
    event_time: string;
    doors_open_time: string;
    image_url: string;
    status: string;
    is_visible: boolean;
    promoter_name: string;
    promoter_email: string;
    promoter_phone: string;
    tiers: Array<{ id: number; name: string; price: number; quantity_available: number }>;
  } | null>(null);
  const [saving, setSaving] = useState(false);
  const [imagePreview, setImagePreview] = useState<string>("");

  const openEditModal = (event: Event) => {
    setEditingEvent(event);
    setEditForm({
      name: event.name || "",
      description: event.description || "",
      event_date: event.event_date || "",
      event_time: event.event_time || "",
      doors_open_time: event.doors_open_time || "",
      image_url: event.image_url || "",
      status: event.status || "scheduled",
      is_visible: event.is_visible,
      promoter_name: (event as any).promoter_name || "",
      promoter_email: (event as any).promoter_email || "",
      promoter_phone: (event as any).promoter_phone || "",
      tiers: (event.ticket_tiers || []).map((t) => ({
        id: t.id,
        name: t.name,
        price: t.price,
        quantity_available: t.quantity_available,
      })),
    });
    setImagePreview(event.image_url || "");
  };

  const closeEditModal = () => {
    setEditingEvent(null);
    setEditForm(null);
    setImagePreview("");
  };

  const refreshEvents = async () => {
    const evts = await fetch(`${API_URL}/api/events`).then((r) => r.json());
    setEvents(Array.isArray(evts) ? evts : []);
  };

  const handleSaveEvent = async () => {
    if (!editingEvent || !editForm) return;
    setSaving(true);
    try {
      // Update event fields
      await fetch(`${API_URL}/api/events/${editingEvent.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editForm.name,
          description: editForm.description || null,
          event_date: editForm.event_date,
          event_time: editForm.event_time,
          doors_open_time: editForm.doors_open_time || null,
          image_url: editForm.image_url || null,
          status: editForm.status,
          is_visible: editForm.is_visible,
          promoter_name: editForm.promoter_name || null,
          promoter_email: editForm.promoter_email || null,
          promoter_phone: editForm.promoter_phone || null,
        }),
      });

      // Update each ticket tier
      for (const tier of editForm.tiers) {
        await fetch(`${API_URL}/mcp/tools/update_ticket_tier`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            arguments: {
              tier_id: tier.id,
              name: tier.name,
              price: tier.price,
              quantity_available: tier.quantity_available,
            },
          }),
        });
      }

      await refreshEvents();
      closeEditModal();
    } catch (err) {
      console.error("Failed to save event:", err);
    } finally {
      setSaving(false);
    }
  };

  // Check stored auth
  useEffect(() => {
    const stored = typeof window !== "undefined" && sessionStorage.getItem("admin_auth");
    if (stored === "true") setAuthed(true);
  }, []);

  const handleLogin = () => {
    if (password === ADMIN_PASSWORD) {
      setAuthed(true);
      sessionStorage.setItem("admin_auth", "true");
      setError("");
    } else {
      setError("Invalid password");
    }
  };

  const handleLogout = () => {
    setAuthed(false);
    sessionStorage.removeItem("admin_auth");
  };

  // Fetch data
  useEffect(() => {
    if (!authed) return;
    setLoading(true);
    Promise.all([
      fetch(`${API_URL}/api/events`).then((r) => r.json()),
      fetch(`${API_URL}/api/venues`).then((r) => r.json()),
      fetch(`${API_URL}/api/dashboard/metrics`).then((r) => r.json()).catch(() => null),
    ]).then(([evts, vns, met]) => {
      setEvents(Array.isArray(evts) ? evts : []);
      setVenues(Array.isArray(vns) ? vns : []);
      setMetrics(met);
      setLoading(false);
    });
  }, [authed]);

  const toggleVisibility = async (eventId: number, visible: boolean) => {
    await fetch(`${API_URL}/mcp/tools/set_event_visibility`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ arguments: { event_id: eventId, is_visible: !visible } }),
    });
    setEvents((prev) => prev.map((e) => (e.id === eventId ? { ...e, is_visible: !visible } : e)));
  };

  const deleteEvent = async (eventId: number) => {
    if (!confirm("Delete this event?")) return;
    await fetch(`${API_URL}/mcp/tools/delete_event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ arguments: { event_id: eventId } }),
    });
    setEvents((prev) => prev.filter((e) => e.id !== eventId));
  };

  // Login screen
  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="w-[380px] bg-card/50 border-white/10 backdrop-blur-sm">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 p-3 rounded-xl bg-primary/10 w-fit">
                <Lock className="h-6 w-6 text-primary" />
              </div>
              <CardTitle className="text-xl">Admin Panel</CardTitle>
              <p className="text-sm text-muted-foreground">Enter password to continue</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <Button className="w-full" onClick={handleLogin}>
                Sign In
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  const totalRevenue = events.reduce((sum, e) => {
    return sum + (e.ticket_tiers || []).reduce((s, t) => s + (t.tickets_sold || 0) * t.price, 0);
  }, 0);
  const totalSold = events.reduce((sum, e) => {
    return sum + (e.ticket_tiers || []).reduce((s, t) => s + (t.tickets_sold || 0), 0);
  }, 0);
  const totalCapacity = events.reduce((sum, e) => {
    return sum + (e.ticket_tiers || []).reduce((s, t) => s + t.quantity_available, 0);
  }, 0);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-white/5 bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="container px-4 sm:px-6 flex h-14 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <Settings className="h-4 w-4 text-primary" />
            </div>
            <span className="font-bold text-lg">Admin Panel</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex bg-white/5 rounded-lg p-0.5">
              {(["events", "venues", "analytics"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${
                    activeTab === tab ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="container px-4 sm:px-6 py-6 space-y-6">
        {/* Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card className="bg-card/50 border-white/10">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Events</p>
              <p className="text-2xl font-bold">{events.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-white/10">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Tickets Sold</p>
              <p className="text-2xl font-bold">{totalSold.toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-white/10">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Revenue</p>
              <p className="text-2xl font-bold text-green-400">${(totalRevenue / 100).toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-white/10">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Capacity</p>
              <p className="text-2xl font-bold">{totalCapacity.toLocaleString()}</p>
            </CardContent>
          </Card>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Events Tab */}
            {activeTab === "events" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-bold">Events ({events.length})</h2>
                  <a href="/events" target="_blank">
                    <Button variant="outline" size="sm">
                      <ExternalLink className="h-3.5 w-3.5 mr-1.5" /> Public Site
                    </Button>
                  </a>
                </div>
                {events.map((event) => {
                  const sold = (event.ticket_tiers || []).reduce((s, t) => s + (t.tickets_sold || 0), 0);
                  const cap = (event.ticket_tiers || []).reduce((s, t) => s + t.quantity_available, 0);
                  const rev = (event.ticket_tiers || []).reduce((s, t) => s + (t.tickets_sold || 0) * t.price, 0);
                  return (
                    <Card key={event.id} className="bg-card/50 border-white/10 overflow-hidden">
                      <div className="flex flex-col sm:flex-row">
                        {event.image_url ? (
                          <img src={event.image_url} alt="" className="w-full sm:w-40 h-32 sm:h-auto object-cover" />
                        ) : (
                          <div className="w-full sm:w-40 h-32 sm:h-auto bg-white/5 flex items-center justify-center">
                            <Music className="h-8 w-8 text-muted-foreground/30" />
                          </div>
                        )}
                        <div className="flex-1 p-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="font-bold">{event.name}</h3>
                              <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                                <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {event.event_date}</span>
                                <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {event.event_time}</span>
                                {event.venue && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {event.venue.name}</span>}
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              <Badge variant={event.is_visible ? "default" : "secondary"} className="text-[10px]">
                                {event.is_visible ? "Live" : "Hidden"}
                              </Badge>
                            </div>
                          </div>

                          {/* Tiers */}
                          <div className="flex flex-wrap gap-2 mt-3">
                            {(event.ticket_tiers || []).map((tier) => (
                              <div key={tier.id} className="text-xs px-2 py-1 rounded bg-white/5 border border-white/10">
                                {tier.name}: <span className="font-bold">${(tier.price / 100).toFixed(0)}</span>
                                <span className="text-muted-foreground ml-1">({tier.quantity_available})</span>
                              </div>
                            ))}
                          </div>

                          {/* Stats row */}
                          <div className="flex items-center gap-4 mt-3 text-xs">
                            <span className="text-muted-foreground">Sold: <span className="text-foreground font-bold">{sold}/{cap}</span></span>
                            <span className="text-muted-foreground">Revenue: <span className="text-green-400 font-bold">${(rev / 100).toLocaleString()}</span></span>
                          </div>

                          {/* Actions */}
                          <div className="flex gap-2 mt-3">
                            <a href={`/events/${event.id}`} target="_blank">
                              <Button variant="outline" size="sm" className="text-xs h-7">
                                <Eye className="h-3 w-3 mr-1" /> View
                              </Button>
                            </a>
                            <Button variant="outline" size="sm" className="text-xs h-7" onClick={() => openEditModal(event)}>
                              <Pencil className="h-3 w-3 mr-1" /> Edit
                            </Button>
                            <Button variant="outline" size="sm" className="text-xs h-7" onClick={() => toggleVisibility(event.id, event.is_visible)}>
                              {event.is_visible ? <EyeOff className="h-3 w-3 mr-1" /> : <Eye className="h-3 w-3 mr-1" />}
                              {event.is_visible ? "Hide" : "Show"}
                            </Button>
                            <Button variant="outline" size="sm" className="text-xs h-7 text-red-400 hover:text-red-300" onClick={() => deleteEvent(event.id)}>
                              <Trash2 className="h-3 w-3 mr-1" /> Delete
                            </Button>
                          </div>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Venues Tab */}
            {activeTab === "venues" && (
              <div className="space-y-3">
                <h2 className="text-lg font-bold">Venues ({venues.length})</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {venues.map((venue) => (
                    <Card key={venue.id} className="bg-card/50 border-white/10">
                      {venue.logo_url ? (
                        <img src={venue.logo_url} alt="" className="w-full h-32 object-cover rounded-t-lg" />
                      ) : (
                        <div className="w-full h-32 bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center rounded-t-lg">
                          <MapPin className="h-8 w-8 text-primary/30" />
                        </div>
                      )}
                      <CardContent className="p-4">
                        <h3 className="font-bold">{venue.name}</h3>
                        {venue.address && <p className="text-xs text-muted-foreground mt-1">{venue.address}</p>}
                        <p className="text-xs text-muted-foreground mt-2">
                          {events.filter((e) => e.venue_id === venue.id).length} event(s)
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Analytics Tab */}
            {activeTab === "analytics" && (
              <div className="space-y-4">
                <h2 className="text-lg font-bold">Analytics</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {events.map((event) => {
                    const sold = (event.ticket_tiers || []).reduce((s, t) => s + (t.tickets_sold || 0), 0);
                    const cap = (event.ticket_tiers || []).reduce((s, t) => s + t.quantity_available, 0);
                    const rev = (event.ticket_tiers || []).reduce((s, t) => s + (t.tickets_sold || 0) * t.price, 0);
                    const pct = cap > 0 ? (sold / cap) * 100 : 0;
                    return (
                      <Card key={event.id} className="bg-card/50 border-white/10">
                        <CardContent className="p-4">
                          <h3 className="font-bold text-sm">{event.name}</h3>
                          <p className="text-xs text-muted-foreground">{event.event_date}</p>
                          <div className="mt-3 space-y-2">
                            <div className="flex justify-between text-xs">
                              <span className="text-muted-foreground">Tickets</span>
                              <span className="font-bold">{sold} / {cap} ({pct.toFixed(0)}%)</span>
                            </div>
                            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
                            </div>
                            <div className="flex justify-between text-xs">
                              <span className="text-muted-foreground">Revenue</span>
                              <span className="font-bold text-green-400">${(rev / 100).toLocaleString()}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Edit Event Modal */}
      <AnimatePresence>
        {editingEvent && editForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 flex items-start justify-center overflow-y-auto py-8"
            onClick={(e) => { if (e.target === e.currentTarget) closeEditModal(); }}
          >
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.97 }}
              className="w-full max-w-2xl mx-4"
            >
              <Card className="bg-card/95 border-white/10 backdrop-blur-xl">
                <CardHeader className="flex flex-row items-center justify-between pb-4">
                  <CardTitle className="text-lg">Edit Event</CardTitle>
                  <Button variant="ghost" size="icon" onClick={closeEditModal} className="h-8 w-8">
                    <X className="h-4 w-4" />
                  </Button>
                </CardHeader>
                <CardContent className="space-y-5">
                  {/* Event Name */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Event Name</label>
                    <Input
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      className="bg-white/5 border-white/10"
                    />
                  </div>

                  {/* Description */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Description</label>
                    <textarea
                      value={editForm.description}
                      onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                      rows={3}
                      className="w-full rounded-md bg-white/5 border border-white/10 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                    />
                  </div>

                  {/* Date & Times */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">Event Date</label>
                      <Input
                        type="date"
                        value={editForm.event_date}
                        onChange={(e) => setEditForm({ ...editForm, event_date: e.target.value })}
                        className="bg-white/5 border-white/10"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">Event Time</label>
                      <Input
                        type="time"
                        value={editForm.event_time}
                        onChange={(e) => setEditForm({ ...editForm, event_time: e.target.value })}
                        className="bg-white/5 border-white/10"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">Doors Open</label>
                      <Input
                        type="time"
                        value={editForm.doors_open_time}
                        onChange={(e) => setEditForm({ ...editForm, doors_open_time: e.target.value })}
                        className="bg-white/5 border-white/10"
                      />
                    </div>
                  </div>

                  {/* Event Image */}
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground">Event Image</label>

                    {/* Current image preview */}
                    <div className="rounded-xl overflow-hidden border border-white/10 bg-white/5 relative group">
                      {imagePreview ? (
                        <img src={imagePreview} alt="Event" className="w-full h-48 object-cover" onError={() => setImagePreview("")} />
                      ) : (
                        <div className="w-full h-48 flex flex-col items-center justify-center text-muted-foreground">
                          <ImageIcon className="h-10 w-10 mb-2 opacity-30" />
                          <p className="text-sm">No image set</p>
                        </div>
                      )}
                      {/* Overlay with upload/change buttons */}
                      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                        <label className="cursor-pointer">
                          <input
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={async (e) => {
                              const file = e.target.files?.[0];
                              if (!file || !editingEvent) return;
                              const formData = new FormData();
                              formData.append("file", file);
                              try {
                                const res = await fetch(`${API_URL}/api/events/${editingEvent.id}/image`, {
                                  method: "POST",
                                  body: formData,
                                });
                                const data = await res.json();
                                const imgUrl = data.image_url?.startsWith("http") ? data.image_url : `${API_URL}${data.image_url}`;
                                setEditForm({ ...editForm!, image_url: imgUrl });
                                setImagePreview(imgUrl);
                              } catch (err) {
                                console.error("Upload failed:", err);
                              }
                            }}
                          />
                          <div className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2">
                            <ImageIcon className="h-4 w-4" /> Upload Image
                          </div>
                        </label>
                      </div>
                    </div>

                    {/* URL paste as alternative */}
                    <div className="flex gap-2">
                      <Input
                        value={editForm.image_url}
                        onChange={(e) => {
                          setEditForm({ ...editForm, image_url: e.target.value });
                          setImagePreview(e.target.value);
                        }}
                        placeholder="Or paste image URL..."
                        className="bg-white/5 border-white/10 flex-1 text-xs h-8"
                      />
                    </div>
                  </div>

                  {/* Status & Visibility */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">Status</label>
                      <select
                        value={editForm.status}
                        onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                        className="w-full h-9 rounded-md bg-white/5 border border-white/10 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                      >
                        <option value="scheduled">Scheduled</option>
                        <option value="postponed">Postponed</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">Visibility</label>
                      <Button
                        variant="outline"
                        className={`w-full justify-start text-xs h-9 ${editForm.is_visible ? "border-green-500/30 text-green-400" : "border-white/10 text-muted-foreground"}`}
                        onClick={() => setEditForm({ ...editForm, is_visible: !editForm.is_visible })}
                      >
                        {editForm.is_visible ? <Eye className="h-3 w-3 mr-2" /> : <EyeOff className="h-3 w-3 mr-2" />}
                        {editForm.is_visible ? "Visible (Live)" : "Hidden"}
                      </Button>
                    </div>
                  </div>

                  {/* Promoter Info */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Promoter Details</label>
                    <div className="grid grid-cols-3 gap-3">
                      <Input
                        value={editForm.promoter_name}
                        onChange={(e) => setEditForm({ ...editForm, promoter_name: e.target.value })}
                        placeholder="Name"
                        className="bg-white/5 border-white/10"
                      />
                      <Input
                        value={editForm.promoter_email}
                        onChange={(e) => setEditForm({ ...editForm, promoter_email: e.target.value })}
                        placeholder="Email"
                        className="bg-white/5 border-white/10"
                      />
                      <Input
                        value={editForm.promoter_phone}
                        onChange={(e) => setEditForm({ ...editForm, promoter_phone: e.target.value })}
                        placeholder="Phone"
                        className="bg-white/5 border-white/10"
                      />
                    </div>
                  </div>

                  {/* Ticket Tiers */}
                  {editForm.tiers.length > 0 && (
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-muted-foreground">Ticket Tiers</label>
                      <div className="space-y-2">
                        {editForm.tiers.map((tier, idx) => (
                          <div key={tier.id} className="grid grid-cols-3 gap-2 p-2.5 rounded-lg bg-white/5 border border-white/10">
                            <div className="space-y-1">
                              <label className="text-[10px] text-muted-foreground">Tier Name</label>
                              <Input
                                value={tier.name}
                                onChange={(e) => {
                                  const tiers = [...editForm.tiers];
                                  tiers[idx] = { ...tiers[idx], name: e.target.value };
                                  setEditForm({ ...editForm, tiers });
                                }}
                                className="bg-white/5 border-white/10 h-8 text-xs"
                              />
                            </div>
                            <div className="space-y-1">
                              <label className="text-[10px] text-muted-foreground">Price ($)</label>
                              <Input
                                type="number"
                                step="0.01"
                                min="0"
                                value={(tier.price / 100).toFixed(2)}
                                onChange={(e) => {
                                  const tiers = [...editForm.tiers];
                                  tiers[idx] = { ...tiers[idx], price: Math.round(parseFloat(e.target.value || "0") * 100) };
                                  setEditForm({ ...editForm, tiers });
                                }}
                                className="bg-white/5 border-white/10 h-8 text-xs"
                              />
                            </div>
                            <div className="space-y-1">
                              <label className="text-[10px] text-muted-foreground">Quantity</label>
                              <Input
                                type="number"
                                min="0"
                                value={tier.quantity_available}
                                onChange={(e) => {
                                  const tiers = [...editForm.tiers];
                                  tiers[idx] = { ...tiers[idx], quantity_available: parseInt(e.target.value || "0") };
                                  setEditForm({ ...editForm, tiers });
                                }}
                                className="bg-white/5 border-white/10 h-8 text-xs"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Save / Cancel */}
                  <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
                    <Button variant="outline" onClick={closeEditModal} disabled={saving}>
                      Cancel
                    </Button>
                    <Button onClick={handleSaveEvent} disabled={saving}>
                      {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Check className="h-4 w-4 mr-2" />}
                      {saving ? "Saving..." : "Save Changes"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
