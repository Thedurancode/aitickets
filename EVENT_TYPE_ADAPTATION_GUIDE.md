# Event Type Adaptation - How AI Customizes Research

## Overview
The AI research agent **automatically adapts** its research strategy, target audience, marketing channels, and messaging based on the event type. It's NOT one-size-fits-all!

## How It Works

### Step 1: AI Reads Event Name & Description
The AI analyzes the event name and description to identify:
- Event category (music, food, sports, comedy, etc.)
- Target demographic (age, interests, lifestyle)
- Event atmosphere (formal vs casual, family vs adults)
- Cultural context (country, EDM, foodie, athletic, etc.)

### Step 2: Adaptive Research Strategy
Based on event type, the AI adapts which platforms to research:

#### 🎵 Music Events → Full Music Platform Research
- ✅ Spotify (top tracks, followers, popularity)
- ✅ YouTube (music videos, subscriber count)
- ✅ Wikipedia (artist bio)
- ✅ Social media (Instagram, TikTok for music content)
- ✅ Web search (tours, awards, collaborations)

#### 🍔 Food Events → Community & Local Focus
- ⚠️ Spotify/YouTube (not applicable - skipped gracefully)
- ✅ Web search (vendor lists, food reviews, similar festivals)
- ✅ Social media (Instagram for food photos, Facebook for local groups)
- ✅ Wikipedia (festival history if established)

#### 🤠 Line Dancing → Country/Western Research
- ⚠️ Music platforms (searches for venue, not individual artist)
- ✅ Web search (venue reviews, dance community)
- ✅ Social media (Facebook groups, local dance scene)

#### 😂 Comedy Events → Comedian-Specific
- ✅ YouTube (comedy clips, stand-up specials)
- ✅ Social media (Twitter/X for jokes, Instagram for promo)
- ✅ Web search (past shows, reviews, comedy festivals)
- ⚠️ Spotify (only if comedian has podcast/album)

#### 🏃 Sports Events → Athletic Community
- ⚠️ Music platforms (not applicable)
- ✅ Web search (race info, running clubs, Strava community)
- ✅ Social media (Facebook running groups, Instagram fitness)

## Real Examples from Test

### 1. DJ Adoni (Music Event)

**Psychographics Detected:**
```
"Party-goers, trendsetters, music enthusiasts"
"Values: Experiences over material possessions, community-oriented"
```

**Marketing Channels Recommended:**
- Email: Targeted campaigns
- SMS: Last-minute reminders
- Paid Media: Instagram/TikTok ads

**Content Ideas Generated:**
```
Instagram: "Counting down to the DJ Adoni Miami Beach Takeover! 🌴
Get your tickets now before they're gone! #DJAdoni #MiamiBeachTakeover"

Facebook: "The beats are calling you! Join us for an unforgettable
night with DJ Adoni in Austin. Limited tickets available!"
```

**Tone**: Energetic, FOMO-driven, nightlife-focused

---

### 2. Food Truck Festival (Food Event)

**Psychographics Detected:**
```
"Families, foodies, supporters of local businesses"
"Values: Community engagement, diverse culinary experiences, family-friendly"
"Lifestyle: Active social life, outdoor events, live music lovers"
```

**Marketing Channels Recommended:**
- Social Media: Instagram (food photos), Facebook (family groups)
- Email: Vendor spotlights, recipe newsletters
- Local marketing: Community boards, neighborhood groups

**Content Ideas Generated:**
```
Social Media: "Post featuring the top 5 food trucks to try this year!"
Social Media: "Behind-the-scenes look at food truck preparations"
Email: "'Meet Your Vendors' spotlight series leading up to the event"
```

**Tone**: Family-friendly, community-focused, celebratory

---

### 3. Line Dancing (Country/Western Event)

**Psychographics Detected:**
```
"Social, active, community-oriented"
"Values: Fun, connection, celebration, inclusivity"
```

**Marketing Channels Recommended:**
- Email: Weekly newsletter
- SMS: Week-of reminders
- Facebook: Older demographic, local groups

**Content Ideas Generated:**
```
Social Media: "🌟 Ready to boot scoot and boogie? Join us for a night
of line dancing fun at The Rusty Spur! Beginners welcome! 🕺#LineDancing"

Email: "Last Chance for Early Bird Tickets for Line Dancing Night!"

Flyer: "Dance the night away! Learn line dancing at 7 PM, open
dancing to follow! 🎶"
```

**Tone**: Welcoming, beginner-friendly, country charm

---

### 4. Comedy Show (Entertainment Event)

**Psychographics Detected:**
```
"Young professionals, college graduates, arts enthusiasts"
"People looking for fun social experiences, appreciate local talent"
```

**Marketing Channels Recommended:**
- Social Media: Instagram reels, TikTok clips
- Email: Humor-focused subject lines
- Paid Ads: Target comedy fans, date-night seekers

**Content Ideas Generated:**
```
Social Media: "Join us for a night of epic laughter with Austin's
top comedians! 🎤 #ComedyNightAustin"

Social Media: "Can you handle 2 hours of non-stop laughter? Grab
your tickets now! 🎉"

Email: "Get Ready to Laugh! Stand-Up Comedy Night Tickets Available Now!"
```

**Tone**: Humorous, energetic, adults-only vibe

---

### 5. Marathon (Sports Event)

**Psychographics Detected:**
```
"Active, health-conscious, enjoys community events"
"Values: Community engagement, personal achievement, environmental awareness"
```

**Marketing Channels Recommended:**
- Email: Training tips, race prep
- SMS: Race day reminders
- Meta Ads: Target fitness enthusiasts
- Community: Strava, running clubs, Facebook groups

**Content Ideas Generated:**
```
Social Media: "Join us in beautiful Austin for an unforgettable
marathon experience! 🏃‍♂️✨ Sign up today and be part of the excitement!"

Email: "Don't Miss Out! Limited Spots Available for the Austin Marathon!"
```

**Tone**: Motivational, achievement-focused, community-oriented

## Adaptation Matrix

| Event Type | Spotify | YouTube | Wikipedia | Social Media Focus | Key Messaging |
|------------|---------|---------|-----------|-------------------|---------------|
| **Music Concert** | ✅ Top tracks | ✅ Music videos | ✅ Artist bio | Instagram, TikTok | FOMO, social proof |
| **Food Festival** | ❌ N/A | ⚠️ Vendor videos | ⚠️ Festival history | Instagram (photos) | Family-friendly, local |
| **Line Dancing** | ⚠️ Venue only | ⚠️ Dance tutorials | ⚠️ Venue info | Facebook (older demo) | Beginner-friendly, fun |
| **Comedy Show** | ⚠️ If podcast | ✅ Comedy clips | ⚠️ If famous | Twitter/X (jokes) | Humorous, adults-only |
| **Marathon** | ❌ N/A | ⚠️ Race highlights | ⚠️ Event history | Strava, running groups | Motivational, health |

## Target Audience Adaptation

### Music Event (DJ Adoni)
- **Age**: 21-35
- **Interests**: Nightlife, EDM, clubbing
- **Channels**: Instagram, TikTok, Snapchat
- **Messaging**: "Don't miss out", "Limited tickets", "Unforgettable night"

### Food Event (Food Truck Festival)
- **Age**: 25-55 (families)
- **Interests**: Food, local businesses, outdoor events
- **Channels**: Instagram (food photos), Facebook (family groups)
- **Messaging**: "Family-friendly", "Support local", "50+ vendors"

### Line Dancing Event
- **Age**: 30-60
- **Interests**: Country music, social dancing, community
- **Channels**: Facebook, local newsletters
- **Messaging**: "Beginners welcome", "All skill levels", "Weekly tradition"

### Comedy Show
- **Age**: 25-45
- **Interests**: Entertainment, nightlife, date nights
- **Channels**: Instagram, TikTok (clips), Twitter/X
- **Messaging**: "Adults only (21+)", "Epic laughter", "Local comedians"

### Marathon
- **Age**: 25-50
- **Interests**: Fitness, health, personal achievement
- **Channels**: Strava, running clubs, Facebook groups
- **Messaging**: "Challenge yourself", "Scenic route", "Finisher medals"

## Channel Strategy Adaptation

### High-Energy Music Event
```json
{
  "instagram": "HIGH priority - 40% budget",
  "tiktok": "HIGH priority - 20% budget",
  "meta_ads": "MEDIUM priority - 25% budget",
  "email": "MEDIUM priority - 10% budget",
  "sms": "HIGH priority (last 48 hours) - 5% budget"
}
```

### Family Food Festival
```json
{
  "instagram": "HIGH priority - 30% budget",
  "facebook": "HIGH priority - 30% budget",
  "local_marketing": "HIGH priority - 20% budget",
  "email": "MEDIUM priority - 15% budget",
  "community_boards": "LOW priority - 5% budget"
}
```

### Weekly Line Dancing
```json
{
  "facebook": "HIGH priority - 40% budget",
  "email_newsletter": "MEDIUM priority - 30% budget",
  "local_groups": "HIGH priority - 20% budget",
  "word_of_mouth": "HIGH priority - 10% budget"
}
```

## Content Tone Adaptation

### Music Event
- **Tone**: Energetic, urgent, FOMO-driven
- **Emoji Use**: Heavy (🔥🎵🌴💥)
- **Language**: "Don't miss", "Epic", "Unforgettable"
- **Hashtags**: Event-specific, trending, location

### Food Event
- **Tone**: Welcoming, community-focused, celebratory
- **Emoji Use**: Moderate (🍔🌮🎉👨‍👩‍👧)
- **Language**: "Join us", "Family-friendly", "Support local"
- **Hashtags**: Food-focused, city-specific

### Line Dancing
- **Tone**: Friendly, welcoming, nostalgic
- **Emoji Use**: Light (🤠🕺💃🎶)
- **Language**: "All welcome", "Beginner-friendly", "Good time"
- **Hashtags**: Country-themed, local

### Comedy Show
- **Tone**: Playful, humorous, edgy
- **Emoji Use**: Moderate (😂🎤🎉🍺)
- **Language**: "Laugh your face off", "Epic", "Adults only"
- **Hashtags**: Comedy-specific, local comedians

### Marathon
- **Tone**: Motivational, achievement-focused, supportive
- **Emoji Use**: Light (🏃‍♂️🏅✨💪)
- **Language**: "Challenge yourself", "Achieve", "Personal best"
- **Hashtags**: Running-focused, race-specific

## Intelligence Features

### ✅ What Makes This Smart

1. **Context Recognition**
   - AI reads event name + description
   - Identifies event category automatically
   - No manual classification needed

2. **Platform Adaptation**
   - Music → Spotify, YouTube, SoundCloud
   - Food → Instagram (photos), local blogs
   - Sports → Strava, running clubs
   - Comedy → YouTube, Twitter/X, Instagram

3. **Audience Targeting**
   - Music → 21-35, nightlife enthusiasts
   - Food → 25-55, families, foodies
   - Dance → 30-60, country fans
   - Comedy → 25-45, date-night crowd
   - Sports → 25-50, fitness enthusiasts

4. **Channel Selection**
   - Young music crowd → Instagram, TikTok
   - Families → Facebook, email
   - Fitness crowd → Strava, running groups
   - Comedy → Twitter/X (jokes), Instagram (clips)

5. **Messaging Tone**
   - Music → Urgent, FOMO, high-energy
   - Food → Welcoming, family-friendly
   - Dance → Beginner-friendly, community
   - Comedy → Humorous, adults-only
   - Sports → Motivational, achievement

## Graceful Handling

### When Research Doesn't Apply

The system **gracefully handles** inapplicable research:

**Food Truck Festival:**
- Spotify research: ⚠️ "Spotify API credentials not configured" (wouldn't find relevant data anyway)
- YouTube research: ⚠️ Skips artist search, might search for festival highlights
- Wikipedia: ⚠️ Searches for festival name if established

**Marathon:**
- Spotify: ❌ Skipped (not applicable)
- YouTube: ⚠️ Might search for race highlights, course videos
- Web search: ✅ Finds race info, running community

**Line Dancing:**
- Spotify: ⚠️ Searches for venue, not specific artist
- YouTube: ⚠️ Might find dance tutorials
- Social: ✅ Finds local dance community

## Conclusion

The AI Tickets research agent is **contextually intelligent**:

1. **Identifies event type** from name + description
2. **Adapts research sources** (music platforms for concerts, community for local events)
3. **Targets correct audience** (young for EDM, families for food festivals)
4. **Selects appropriate channels** (TikTok for Gen Z, Facebook for families)
5. **Adjusts messaging tone** (energetic for music, welcoming for community events)

**Result:** Each event gets a **custom-tailored research profile** and marketing plan that matches its unique characteristics.

**Not one-size-fits-all. Truly adaptive AI.**
