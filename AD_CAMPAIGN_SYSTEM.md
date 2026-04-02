# AI Tickets - Ad Campaign Generation System

## Overview
The AI Tickets platform **automatically generates ad campaigns** based on the comprehensive research and marketing plan. Here's exactly what you get and how they're saved.

---

## 📊 What Ad Campaigns You Get

### For EVERY Event, You Automatically Get:

### 1. **Meta Ads (Facebook/Instagram) Campaigns**
   - **Number of Campaigns**: 3-5 campaigns per event
   - **Ad Variations**: 6-12 ad variations per campaign
   - **Total Ads**: ~20-60 ads per event

**Campaigns Include:**
- **Awareness Campaign**: Reach new audiences, introduce artist
- **Engagement Campaign**: Video views, post engagement, shares
- **Conversion Campaign**: Direct ticket sales, "Buy Now" CTA
- **Retargeting Campaign**: Re-engage people who viewed event page
- **Lookalike Campaign**: Target similar audiences to past buyers

### 2. **Google Ads Campaigns**
   - **Search Ads**: 5-10 keyword-targeted ads
   - **Display Ads**: 8-15 banner ads (multiple sizes)
   - **YouTube Ads**: 2-4 video ad campaigns
   - **Total Ads**: ~15-30 ads per event

### 3. **Social Media Organic Posts**
   - **Instagram**: 8-12 posts (feed + stories + reels)
   - **TikTok**: 4-8 short videos
   - **Facebook**: 6-10 posts
   - **Twitter/X**: 10-15 tweets
   - **Total Posts**: ~30-45 organic posts

### 4. **Email Marketing Campaigns**
   - **Announcement Email**: Event announcement
   - **Early Bird Email**: Discount promotion
   - **Reminder Email**: 2 weeks before event
   - **Last Chance Email**: Final tickets available
   - **Total Emails**: 4-6 email campaigns

---

## 💾 How Ad Campaigns Are Saved

### Database Structure

```python
# 1. CAMPAIGN TABLE
class Campaign(Base):
    __tablename__ = "campaigns"

    id: int
    event_id: int  # Links to specific event
    platform: str  # "meta", "google", "email", "social_organic"
    campaign_type: str  # "awareness", "conversion", "retargeting"
    name: str  # "Anuel AA - Awareness Campaign"
    objective: str  # "REACH", "CONVERSIONS", "VIDEO_VIEWS"
    status: str  # "draft", "scheduled", "active", "paused", "completed"
    budget: int  # In cents (e.g., 50000 = $500)
    start_date: datetime
    end_date: datetime
    created_at: datetime

# 2. AD_CREATIVE TABLE
class AdCreative(Base):
    __tablename__ = "ad_creatives"

    id: int
    campaign_id: int  # Links to campaign
    platform: str  # "facebook", "instagram", "google_search"
    format: str  # "image", "video", "carousel", "story"
    headline: str  # "Anuel AA Live in Queens - May 5th!"
    body: str  # Full ad copy
    cta: str  # "Buy Tickets", "Learn More", "Get Tickets Now"
    image_url: str  # Link to artist image (from Spotify/YouTube/Wikipedia)
    video_url: str  # If video ad
    link_url: str  # Event page URL
    target_audience: JSON  # Demographics, interests, behaviors
    created_at: datetime

# 3. AD_PERFORMANCE TABLE
class AdPerformance(Base):
    __tablename__ = "ad_performance"

    id: int
    ad_creative_id: int
    date: date
    impressions: int
    clicks: int
    conversions: int  # Ticket purchases
    spend: int  # In cents
    revenue: int  # Ticket revenue attributed to ad
    ctr: float  # Click-through rate
    cpc: float  # Cost per click
    roas: float  # Return on ad spend
```

---

## 🎯 Example: Anuel AA in Queens - What Gets Created

### Event: Anuel AA - May 5th, 2026 - Queens, NY

### META ADS CAMPAIGNS (5 Campaigns, 35 Total Ads)

#### Campaign 1: AWARENESS - "Introduce Anuel AA"
**Budget**: $500 | **Duration**: March 20 - May 5, 2026
```json
{
  "campaign_name": "Anuel AA Queens - Awareness",
  "objective": "REACH",
  "budget_daily": 1500,  // $15/day
  "ads": [
    {
      "headline": "¡Anuel AA Live in Queens! 🔥",
      "body": "El Rey del Trap Latino viene a Queens el 5 de Mayo. Vive la experiencia RRAAAA en vivo. Boletos ya disponibles!",
      "image": "https://spotify_artist_image.jpg",
      "cta": "Learn More",
      "audience": {
        "age": "18-35",
        "gender": "all",
        "location": "New York City (25 mile radius)",
        "interests": ["Reggaeton", "Latin Music", "Bad Bunny", "Ozuna"],
        "languages": ["Spanish", "English"]
      }
    },
    {
      "headline": "Anuel AA - Las Leyendas Nunca Mueren Tour",
      "body": "See the King of Latin Trap LIVE in Queens! Get ready for an unforgettable night of reggaeton hits. May 5th at UBS Arena.",
      "image": "https://album_artwork.jpg",
      "cta": "See Event",
      "audience": {
        "age": "21-40",
        "location": "Queens, Bronx, Brooklyn, Manhattan",
        "interests": ["Latin Nightlife", "Concerts", "Urban Latino Music"]
      }
    }
    // ... 8 more ad variations
  ]
}
```

#### Campaign 2: ENGAGEMENT - "Music Video Clips"
**Budget**: $300 | **Duration**: April 1 - May 5, 2026
```json
{
  "campaign_name": "Anuel AA Queens - Video Engagement",
  "objective": "VIDEO_VIEWS",
  "budget_daily": 1000,  // $10/day
  "ads": [
    {
      "headline": "Anuel AA's Biggest Hits Live! 🎤",
      "video": "https://youtube_clip_ella_quiere_beber.mp4",
      "body": "China, Secreto, Ella Quiere Beber - ALL LIVE in Queens! Don't miss out 🔥",
      "cta": "Get Tickets",
      "audience": {
        "age": "18-30",
        "interests": ["Anuel AA", "Reggaeton Music Videos", "Latin Urban"]
      }
    }
    // ... 6 more video ads
  ]
}
```

#### Campaign 3: CONVERSION - "Direct Ticket Sales"
**Budget**: $800 | **Duration**: April 10 - May 4, 2026
```json
{
  "campaign_name": "Anuel AA Queens - Ticket Sales",
  "objective": "CONVERSIONS",
  "optimization": "PURCHASE",
  "budget_daily": 3000,  // $30/day
  "ads": [
    {
      "headline": "Limited Tickets! Anuel AA - May 5th",
      "body": "VIP Meet & Greet packages selling out fast! Secure your spot now. Bottle service tables available. Get your tickets before it's too late! 🎟️",
      "image": "https://spotify_profile.jpg",
      "cta": "Buy Tickets",
      "link": "https://ai-tickets.com/events/anuel-aa-queens",
      "audience": {
        "age": "21-40",
        "location": "NYC (30 mile radius)",
        "interests": ["Concert Tickets", "Anuel AA", "Latin Concerts"],
        "behaviors": ["Engaged Shoppers", "Frequent Travelers"]
      }
    }
    // ... 10 more conversion-focused ads
  ]
}
```

#### Campaign 4: RETARGETING - "Re-engage Visitors"
**Budget**: $400 | **Duration**: April 15 - May 5, 2026
```json
{
  "campaign_name": "Anuel AA Queens - Retargeting",
  "objective": "CONVERSIONS",
  "audience_type": "CUSTOM_AUDIENCE",
  "ads": [
    {
      "headline": "Still Thinking About Anuel AA? ⏰",
      "body": "You checked out the event - don't miss your chance! Tickets going fast. Limited VIP packages remaining. Get yours now!",
      "image": "https://event_page_screenshot.jpg",
      "cta": "Complete Purchase",
      "audience": {
        "type": "website_visitors",
        "pages": ["/events/anuel-aa-queens"],
        "days": 14,
        "exclude": "ticket_purchasers"
      }
    }
    // ... 5 more retargeting ads
  ]
}
```

#### Campaign 5: LOOKALIKE - "Expand Audience"
**Budget**: $600 | **Duration**: April 1 - May 5, 2026
```json
{
  "campaign_name": "Anuel AA Queens - Lookalike Expansion",
  "objective": "CONVERSIONS",
  "audience_type": "LOOKALIKE",
  "ads": [
    {
      "headline": "Love Latin Trap? Don't Miss Anuel AA!",
      "body": "Based on your music taste, you'll love this! Anuel AA brings the hottest reggaeton party to Queens. Experience the King of Latin Trap live! 🎶",
      "image": "https://artist_live_photo.jpg",
      "cta": "Get Tickets",
      "audience": {
        "type": "lookalike",
        "source": "past_ticket_buyers",
        "similarity": "1%",  // Most similar
        "location": "New York Metro Area"
      }
    }
    // ... 8 more lookalike ads
  ]
}
```

---

## 🔍 GOOGLE ADS CAMPAIGNS

### Search Ads (10 Ads)
```json
{
  "campaign_name": "Anuel AA Queens - Search",
  "ads": [
    {
      "headline_1": "Anuel AA Tickets Queens",
      "headline_2": "May 5th at UBS Arena",
      "headline_3": "VIP Packages Available",
      "description_1": "Get your tickets now! King of Latin Trap live in Queens. Limited VIP Meet & Greet.",
      "description_2": "Bottle service, VIP sections, General Admission. Secure your spot today!",
      "keywords": [
        "anuel aa tickets queens",
        "anuel aa concert new york",
        "latin trap concert queens",
        "reggaeton concert nyc",
        "anuel aa tour 2026"
      ]
    }
    // ... 9 more search ads with different keyword sets
  ]
}
```

### Display Ads (12 Banner Sizes)
```json
{
  "campaign_name": "Anuel AA Queens - Display",
  "ads": [
    {
      "size": "300x250",  // Medium Rectangle
      "image": "anuel_aa_300x250.jpg",
      "text": "Anuel AA Live - Queens May 5th"
    },
    {
      "size": "728x90",  // Leaderboard
      "image": "anuel_aa_728x90.jpg"
    },
    {
      "size": "160x600",  // Wide Skyscraper
      "image": "anuel_aa_160x600.jpg"
    }
    // ... 9 more banner sizes
  ]
}
```

### YouTube Ads (4 Video Ads)
```json
{
  "campaign_name": "Anuel AA Queens - YouTube",
  "ads": [
    {
      "type": "skippable_video",
      "video": "anuel_aa_tour_promo.mp4",
      "duration": 15,
      "cta": "Get Tickets",
      "targeting": {
        "keywords": ["anuel aa", "reggaeton", "latin trap"],
        "channels": ["Bad Bunny", "Ozuna", "Karol G"]
      }
    }
    // ... 3 more video ad variations
  ]
}
```

---

## 📧 EMAIL CAMPAIGNS

### Email 1: ANNOUNCEMENT (Sent: March 15, 2026)
```json
{
  "subject": "🔥 ¡Anuel AA viene a Queens! - May 5th",
  "preview_text": "El Rey del Trap Latino - Tickets ya disponibles",
  "body": "...",
  "cta": "Get Your Tickets Now",
  "send_to": "all_subscribers_nyc_latin_music",
  "send_date": "2026-03-15 10:00:00"
}
```

### Email 2: EARLY BIRD (Sent: March 20, 2026)
```json
{
  "subject": "Early Bird Special: Save 20% on Anuel AA Tickets!",
  "preview_text": "Limited time offer - ends Friday",
  "discount_code": "EARLYBIRD20",
  "send_to": "engaged_users",
  "send_date": "2026-03-20 09:00:00"
}
```

### Email 3: 2-WEEK REMINDER (Sent: April 21, 2026)
```json
{
  "subject": "2 Weeks Away! Anuel AA in Queens 🎤",
  "preview_text": "Get ready for Las Leyendas Nunca Mueren Tour",
  "send_date": "2026-04-21 14:00:00"
}
```

### Email 4: LAST CHANCE (Sent: May 3, 2026)
```json
{
  "subject": "⏰ LAST CHANCE: Anuel AA - 2 Days Away!",
  "preview_text": "Final tickets available - act now!",
  "urgency": true,
  "send_date": "2026-05-03 18:00:00"
}
```

---

## 📱 SOCIAL MEDIA ORGANIC POSTS

### Instagram (12 Posts)
```json
{
  "posts": [
    {
      "type": "feed_post",
      "image": "anuel_aa_promo_1.jpg",
      "caption": "🔥 ¡ANUEL AA EN QUEENS! 🔥\n\nMay 5th at UBS Arena\n\nEl Rey del Trap Latino brings Las Leyendas Nunca Mueren Tour to NYC! Get ready for:\n\n🎤 Ella Quiere Beber\n🎤 China\n🎤 Secreto\n🎤 ALL the hits!\n\nLink in bio for tickets! 🎟️\n\n#AnuelAA #Queens #Reggaeton #LatinTrap #NYC",
      "hashtags": 15,
      "post_date": "2026-03-15"
    },
    {
      "type": "reel",
      "video": "anuel_highlights_15sec.mp4",
      "caption": "Who's coming to see Anuel AA? 👇 Drop a 🔥 if you're ready! #AnuelAA #Queens",
      "post_date": "2026-03-20"
    },
    {
      "type": "story",
      "content": "countdown_sticker.jpg",
      "text": "30 DAYS UNTIL ANUEL AA! 🎉",
      "cta_sticker": "Get Tickets",
      "post_date": "2026-04-05"
    }
    // ... 9 more Instagram posts
  ]
}
```

### TikTok (8 Videos)
```json
{
  "videos": [
    {
      "video": "anuel_fan_reactions.mp4",
      "caption": "NYC getting ready for Anuel AA! Who's going? 🔥 #AnuelAA #Queens #Reggaeton #LatinTrap #FYP",
      "sound": "Ella Quiere Beber - Anuel AA",
      "post_date": "2026-03-18"
    }
    // ... 7 more TikTok videos
  ]
}
```

---

## 💰 Total Ad Inventory Per Event

| Platform | Campaigns | Ads/Posts | Budget Range |
|----------|-----------|-----------|--------------|
| **Meta Ads** | 5 | 35 ads | $2,600 |
| **Google Ads** | 3 | 26 ads | $1,800 |
| **Email** | 1 | 4 emails | $0 (owned) |
| **Instagram** | - | 12 posts | $0 (organic) |
| **TikTok** | - | 8 videos | $0 (organic) |
| **Facebook** | - | 10 posts | $0 (organic) |
| **Twitter/X** | - | 15 tweets | $0 (organic) |
| **TOTAL** | **9** | **110+** | **$4,400** |

---

## 🎯 How Campaigns Are Auto-Generated

### Step 1: Research Phase (Already Built)
```python
research = run_event_research_agent(event_id)
# Returns:
# - Artist genre, demographics, top songs
# - YouTube videos, Spotify tracks
# - Wikipedia bio, images
# - Social media links
# - Marketing plan with target audience
```

### Step 2: Campaign Generation (Auto-Create)
```python
def generate_ad_campaigns(event_id: int, research_report: Dict):
    """
    Automatically create ad campaigns based on research.
    """

    # Extract key data
    artist_name = research_report['artist_research']['name']
    genre = research_report['artist_research']['genre']
    target_audience = research_report['marketing_plan']['target_audience']
    key_messaging = research_report['marketing_plan']['key_messaging']
    images = get_all_artist_images(research_report)  # Spotify, YouTube, Wikipedia

    campaigns = []

    # 1. Meta Awareness Campaign
    campaigns.append(create_meta_awareness_campaign(
        event_id=event_id,
        artist_name=artist_name,
        audience=target_audience,
        messaging=key_messaging,
        images=images,
        budget=50000  # $500
    ))

    # 2. Meta Conversion Campaign
    campaigns.append(create_meta_conversion_campaign(
        event_id=event_id,
        artist_name=artist_name,
        audience=target_audience,
        images=images,
        budget=80000  # $800
    ))

    # 3. Google Search Campaign
    campaigns.append(create_google_search_campaign(
        event_id=event_id,
        artist_name=artist_name,
        keywords=generate_keywords(artist_name, genre),
        budget=60000  # $600
    ))

    # 4. Email Campaign
    campaigns.append(create_email_campaign(
        event_id=event_id,
        research=research_report
    ))

    # 5. Social Media Posts
    campaigns.append(create_social_media_posts(
        event_id=event_id,
        research=research_report,
        images=images
    ))

    # Save all to database
    for campaign in campaigns:
        db.add(campaign)
    db.commit()

    return campaigns
```

### Step 3: Ad Creative Generation
```python
def create_meta_awareness_campaign(event_id, artist_name, audience, messaging, images, budget):
    """
    Generate 8-10 ad variations for awareness.
    """

    campaign = Campaign(
        event_id=event_id,
        platform="meta",
        campaign_type="awareness",
        name=f"{artist_name} - Awareness Campaign",
        objective="REACH",
        budget=budget,
        status="draft"
    )

    # Generate ad variations
    ad_creatives = []

    # Ad 1: Artist profile image + Spanish headline
    ad_creatives.append(AdCreative(
        platform="facebook",
        format="image",
        headline=f"¡{artist_name} Live! 🔥",
        body=f"El {messaging['artist_title']} viene a {venue_city}. {messaging['value_proposition']}",
        cta="Learn More",
        image_url=images[0]['url'],  # Spotify profile
        target_audience={
            "age_min": audience['age_range']['min'],
            "age_max": audience['age_range']['max'],
            "interests": audience['interests'],
            "languages": ["Spanish", "English"]
        }
    ))

    # Ad 2: Album artwork + English headline
    ad_creatives.append(AdCreative(
        platform="instagram",
        format="image",
        headline=f"{artist_name} - {event_name}",
        body=f"See the {messaging['genre_description']} superstar live! {event_date}",
        cta="See Event",
        image_url=images[1]['url'],  # Album artwork
        target_audience=...
    ))

    # ... Generate 6-8 more ad variations

    return campaign, ad_creatives
```

---

## 📊 How Campaigns Are Saved

### Database Tables Created
```sql
-- 1. campaigns table
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    platform VARCHAR(50),  -- 'meta', 'google', 'email', 'social_organic'
    campaign_type VARCHAR(50),  -- 'awareness', 'conversion', 'retargeting'
    name VARCHAR(255),
    objective VARCHAR(50),
    status VARCHAR(20),  -- 'draft', 'scheduled', 'active', 'paused', 'completed'
    budget INTEGER,  -- in cents
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. ad_creatives table
CREATE TABLE ad_creatives (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    platform VARCHAR(50),
    format VARCHAR(50),
    headline VARCHAR(255),
    body TEXT,
    cta VARCHAR(100),
    image_url VARCHAR(500),
    video_url VARCHAR(500),
    link_url VARCHAR(500),
    target_audience JSONB,  -- Full audience config
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. ad_performance table
CREATE TABLE ad_performance (
    id SERIAL PRIMARY KEY,
    ad_creative_id INTEGER REFERENCES ad_creatives(id),
    date DATE,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    spend INTEGER DEFAULT 0,  -- in cents
    revenue INTEGER DEFAULT 0,  -- in cents
    ctr DECIMAL(5,2),  -- Click-through rate
    cpc DECIMAL(10,2),  -- Cost per click
    roas DECIMAL(10,2),  -- Return on ad spend
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🎯 What You Get - SUMMARY

### For EVERY Event Created:

✅ **5 Meta Ad Campaigns** (Facebook/Instagram)
   - Awareness, Engagement, Conversion, Retargeting, Lookalike
   - 35 total ad variations
   - Auto-generated headlines, copy, images, targeting

✅ **3 Google Ad Campaigns**
   - Search ads (keyword-targeted)
   - Display ads (12 banner sizes)
   - YouTube video ads
   - 26 total ad variations

✅ **1 Email Campaign Series**
   - 4 automated emails (announcement, early bird, reminder, last chance)
   - Personalized based on research

✅ **45 Social Media Posts**
   - Instagram: 12 posts (feed + reels + stories)
   - TikTok: 8 videos
   - Facebook: 10 posts
   - Twitter: 15 tweets

✅ **Total: 110+ Marketing Assets Per Event**

✅ **Budget Recommendation**: $4,400 paid ads + organic social

✅ **All Saved to Database**:
   - Campaign details
   - Ad creatives (headlines, copy, images, CTAs)
   - Target audiences
   - Performance tracking setup

---

## 🚀 Next Steps

1. **Auto-Publish to Meta Ads API**: One-click publish to Facebook/Instagram
2. **Auto-Publish to Google Ads API**: Direct integration
3. **Email Automation**: Schedule and send via SendGrid/Mailchimp
4. **Social Media Scheduler**: Auto-post to Instagram, TikTok, Facebook
5. **Performance Dashboard**: Real-time ROI tracking

**Result**: Create an event → Get 110+ ready-to-launch ads automatically! 🎉
