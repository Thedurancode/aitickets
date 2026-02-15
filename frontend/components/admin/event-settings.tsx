"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Save, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useAdminUpdateEvent } from "@/lib/queries";
import type { AdminDashboardData } from "@/types/api";

const settingsSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  event_date: z.string().min(1, "Date is required"),
  event_time: z.string().min(1, "Time is required"),
  doors_open_time: z.string().optional(),
  promo_video_url: z.string().url().optional().or(z.literal("")),
  post_event_video_url: z.string().url().optional().or(z.literal("")),
  is_visible: z.boolean(),
});

type SettingsFormData = z.infer<typeof settingsSchema>;

interface EventSettingsProps {
  data: AdminDashboardData;
  eventId: number;
  token: string;
}

export function EventSettings({ data, eventId, token }: EventSettingsProps) {
  const { event } = data;
  const updateMutation = useAdminUpdateEvent(eventId, token);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      name: event.name,
      description: event.description || "",
      event_date: event.event_date,
      event_time: event.event_time,
      doors_open_time: event.doors_open_time || "",
      promo_video_url: event.promo_video_url || "",
      post_event_video_url: event.post_event_video_url || "",
      is_visible: event.is_visible,
    },
  });

  const onSubmit = (formData: SettingsFormData) => {
    updateMutation.mutate(formData);
  };

  return (
    <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-lg">Event Settings</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Event Name</Label>
            <Input id="name" {...register("name")} />
            {errors.name && (
              <p className="text-sm text-red-400">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <textarea
              id="description"
              {...register("description")}
              rows={3}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="event_date">Date</Label>
              <Input id="event_date" type="date" {...register("event_date")} />
              {errors.event_date && (
                <p className="text-sm text-red-400">
                  {errors.event_date.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="event_time">Time</Label>
              <Input id="event_time" type="time" {...register("event_time")} />
              {errors.event_time && (
                <p className="text-sm text-red-400">
                  {errors.event_time.message}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="doors_open_time">Doors Open Time</Label>
            <Input
              id="doors_open_time"
              type="time"
              {...register("doors_open_time")}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="promo_video_url">Promo Video URL</Label>
            <Input
              id="promo_video_url"
              placeholder="https://youtube.com/watch?v=..."
              {...register("promo_video_url")}
            />
            {errors.promo_video_url && (
              <p className="text-sm text-red-400">
                {errors.promo_video_url.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="post_event_video_url">
              Post-Event Video URL
            </Label>
            <Input
              id="post_event_video_url"
              placeholder="https://youtube.com/watch?v=..."
              {...register("post_event_video_url")}
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_visible"
              {...register("is_visible")}
              className="h-4 w-4 rounded border-input"
            />
            <Label htmlFor="is_visible" className="cursor-pointer">
              Event is publicly visible
            </Label>
          </div>

          <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
            <Button
              type="submit"
              disabled={!isDirty || updateMutation.isPending}
              className="w-full gap-2"
            >
              {updateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save Changes
            </Button>
          </motion.div>

          {updateMutation.isSuccess && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-green-400 text-center"
            >
              Changes saved successfully
            </motion.p>
          )}

          {updateMutation.isError && (
            <p className="text-sm text-red-400 text-center">
              Failed to save. Please try again.
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
