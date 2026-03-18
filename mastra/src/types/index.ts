import { z } from "zod";

// ── Input Schemas ──

export const eventInputSchema = z.object({
  artist_name: z.string().describe("Performing artist or act name"),
  event_name: z.string().describe("Event title"),
  venue_name: z.string().describe("Venue name"),
  city: z.string().describe("City where the event takes place"),
  state: z.string().optional().describe("State or province"),
  country: z.string().default("US").describe("Country code"),
  event_date: z.string().describe("Event date in ISO format"),
  event_type: z
    .enum([
      "concert",
      "festival",
      "comedy",
      "sports",
      "theater",
      "club",
      "conference",
      "other",
    ])
    .describe("Type of event"),
  ticket_price_min: z.number().optional().describe("Minimum ticket price"),
  ticket_price_max: z.number().optional().describe("Maximum ticket price"),
  capacity: z.number().optional().describe("Venue capacity"),
  description: z.string().optional().describe("Event description"),
  genre: z.string().optional().describe("Music genre or event genre"),
  age_restriction: z.string().optional().describe("Age restriction (e.g., 18+, all ages)"),
  tenant_id: z.string().optional().describe("Multi-tenant account ID"),
});

export type EventInput = z.infer<typeof eventInputSchema>;

// ── Research Output ──

export const researchOutputSchema = z.object({
  artist_intelligence: z.object({
    name: z.string(),
    genre: z.string(),
    monthly_listeners: z.number().optional(),
    social_following: z.object({
      instagram: z.number().optional(),
      tiktok: z.number().optional(),
      twitter: z.number().optional(),
      spotify: z.number().optional(),
    }),
    recent_releases: z.array(z.string()),
    tour_history: z.array(z.string()),
    similar_artists: z.array(z.string()),
  }),
  engagement_score: z.number().min(0).max(100).describe("0-100 engagement score"),
  market_analysis: z.object({
    city_demand: z.enum(["low", "medium", "high", "very_high"]),
    competition: z.array(
      z.object({
        event_name: z.string(),
        date: z.string(),
        relevance: z.string(),
      })
    ),
    market_saturation: z.enum(["undersaturated", "balanced", "oversaturated"]),
  }),
  demand_forecast: z.object({
    estimated_attendance: z.number(),
    confidence: z.number().min(0).max(1),
    sell_through_prediction: z.number().min(0).max(100),
    recommended_capacity_utilization: z.number().min(0).max(100),
  }),
  venue_insights: z.object({
    venue_name: z.string(),
    capacity: z.number().optional(),
    typical_events: z.array(z.string()),
    area_demographics: z.string(),
  }),
});

export type ResearchOutput = z.infer<typeof researchOutputSchema>;

// ── Audience Output ──

export const audienceOutputSchema = z.object({
  segments: z.array(
    z.object({
      name: z.string(),
      description: z.string(),
      size_estimate: z.enum(["small", "medium", "large"]),
      age_range: z.string(),
      interests: z.array(z.string()),
      behaviors: z.array(z.string()),
      platforms: z.array(z.string()),
      messaging_angle: z.string(),
    })
  ),
  primary_audience: z.object({
    age_range: z.string(),
    gender_split: z.string(),
    income_level: z.string(),
    lifestyle: z.string(),
  }),
  platform_strategy: z.array(
    z.object({
      platform: z.string(),
      priority: z.enum(["primary", "secondary", "tertiary"]),
      audience_match: z.number().min(0).max(100),
      best_content_type: z.string(),
      best_posting_times: z.array(z.string()),
    })
  ),
});

export type AudienceOutput = z.infer<typeof audienceOutputSchema>;

// ── Marketing Strategy Output ──

export const marketingStrategyOutputSchema = z.object({
  campaign_name: z.string(),
  campaign_phases: z.array(
    z.object({
      phase: z.string(),
      name: z.string(),
      start_offset_days: z.number().describe("Days before event"),
      end_offset_days: z.number(),
      objective: z.string(),
      channels: z.array(z.string()),
      tactics: z.array(z.string()),
      budget_allocation_pct: z.number(),
      kpis: z.array(z.string()),
    })
  ),
  messaging_strategy: z.object({
    headline: z.string(),
    subheadline: z.string(),
    value_propositions: z.array(z.string()),
    urgency_hooks: z.array(z.string()),
    social_proof_angles: z.array(z.string()),
    hashtags: z.array(z.string()),
  }),
  content_calendar: z.array(
    z.object({
      day_offset: z.number(),
      platform: z.string(),
      content_type: z.string(),
      description: z.string(),
      cta: z.string(),
    })
  ),
  budget_recommendation: z.object({
    total_budget: z.number(),
    breakdown: z.record(z.string(), z.number()),
    expected_roas: z.number(),
  }),
});

export type MarketingStrategyOutput = z.infer<typeof marketingStrategyOutputSchema>;

// ── Media Buyer Output ──

export const mediaBuyerOutputSchema = z.object({
  campaigns: z.array(
    z.object({
      name: z.string(),
      objective: z.enum([
        "AWARENESS",
        "TRAFFIC",
        "ENGAGEMENT",
        "LEADS",
        "CONVERSIONS",
      ]),
      daily_budget: z.number(),
      duration_days: z.number(),
      ad_sets: z.array(
        z.object({
          name: z.string(),
          funnel_stage: z.enum(["cold", "warm", "hot"]),
          targeting: z.object({
            age_min: z.number(),
            age_max: z.number(),
            genders: z.array(z.number()),
            geo_locations: z.object({
              cities: z.array(z.string()),
              radius_km: z.number(),
            }),
            interests: z.array(
              z.object({
                id: z.string().optional(),
                name: z.string(),
              })
            ),
            behaviors: z.array(z.string()),
            custom_audiences: z.array(z.string()),
            excluded_audiences: z.array(z.string()),
          }),
          placements: z.array(z.string()),
          optimization_goal: z.string(),
        })
      ),
      ads: z.array(
        z.object({
          name: z.string(),
          format: z.enum(["image", "video", "carousel", "story"]),
          primary_text: z.string(),
          headline: z.string(),
          description: z.string(),
          cta: z.string(),
          link_url: z.string().optional(),
        })
      ),
    })
  ),
  scaling_logic: z.object({
    initial_daily_budget: z.number(),
    scale_trigger: z.string(),
    scale_increment_pct: z.number(),
    max_daily_budget: z.number(),
    kill_switch: z.string(),
  }),
  total_budget: z.number(),
  expected_results: z.object({
    impressions: z.number(),
    clicks: z.number(),
    conversions: z.number(),
    cost_per_conversion: z.number(),
  }),
});

export type MediaBuyerOutput = z.infer<typeof mediaBuyerOutputSchema>;

// ── Creative Director Output ──

export const creativeOutputSchema = z.object({
  creative_direction: z.object({
    mood: z.string(),
    color_palette: z.array(z.string()),
    typography_style: z.string(),
    visual_references: z.array(z.string()),
  }),
  instagram: z.object({
    feed_posts: z.array(
      z.object({
        concept: z.string(),
        image_prompt: z.string(),
        caption: z.string(),
        hashtags: z.array(z.string()),
      })
    ),
    stories: z.array(
      z.object({
        concept: z.string(),
        frames: z.array(z.string()),
        cta: z.string(),
      })
    ),
    reels: z.array(
      z.object({
        concept: z.string(),
        script: z.string(),
        duration_seconds: z.number(),
        music_suggestion: z.string(),
      })
    ),
  }),
  tiktok: z.array(
    z.object({
      concept: z.string(),
      hook: z.string(),
      script: z.string(),
      duration_seconds: z.number(),
      trending_sound: z.string().optional(),
      hashtags: z.array(z.string()),
    })
  ),
  banner_designs: z.array(
    z.object({
      size: z.string(),
      platform: z.string(),
      headline: z.string(),
      subtext: z.string(),
      image_prompt: z.string(),
    })
  ),
  flyer: z.object({
    headline: z.string(),
    subheadline: z.string(),
    image_prompt: z.string(),
    color_scheme: z.string(),
    style: z.string(),
  }),
});

export type CreativeOutput = z.infer<typeof creativeOutputSchema>;

// ── Distribution Output ──

export const distributionOutputSchema = z.object({
  master_event_record: z.object({
    title: z.string(),
    description: z.string(),
    short_description: z.string(),
    date: z.string(),
    venue: z.string(),
    city: z.string(),
    category: z.string(),
    tags: z.array(z.string()),
    seo_title: z.string(),
    seo_description: z.string(),
    seo_keywords: z.array(z.string()),
    og_title: z.string(),
    og_description: z.string(),
  }),
  platform_listings: z.array(
    z.object({
      platform: z.string(),
      title: z.string(),
      description: z.string(),
      category: z.string(),
      tags: z.array(z.string()),
      custom_fields: z.record(z.string(), z.string()),
      ready_to_publish: z.boolean(),
      validation_issues: z.array(z.string()),
    })
  ),
});

export type DistributionOutput = z.infer<typeof distributionOutputSchema>;

// ── Publishing Output ──

export const publishingOutputSchema = z.object({
  results: z.array(
    z.object({
      platform: z.string(),
      status: z.enum(["success", "failed", "skipped"]),
      url: z.string().optional(),
      platform_id: z.string().optional(),
      error: z.string().optional(),
      published_at: z.string().optional(),
    })
  ),
  summary: z.object({
    total: z.number(),
    succeeded: z.number(),
    failed: z.number(),
    skipped: z.number(),
  }),
});

export type PublishingOutput = z.infer<typeof publishingOutputSchema>;

// ── Full Engine Output (aggregate) ──

export const fullEngineOutputSchema = z.object({
  event_input: eventInputSchema,
  research: researchOutputSchema,
  audience: audienceOutputSchema,
  marketing: marketingStrategyOutputSchema,
  creatives: creativeOutputSchema,
  distribution: distributionOutputSchema,
  media_buying: mediaBuyerOutputSchema.optional(),
  publishing: publishingOutputSchema.optional(),
  generated_at: z.string(),
  processing_time_ms: z.number(),
});

export type FullEngineOutput = z.infer<typeof fullEngineOutputSchema>;
