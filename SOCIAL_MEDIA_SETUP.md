# Social Media Integration Setup Guide

Complete guide to connecting all social media platforms to your AI Tickets system.

## Overview

Your system now has **8 MCP tools** that allow your AI agent to publish events to ALL major social media platforms:

- Twitter/X
- Facebook
- Instagram
- LinkedIn
- TikTok
- YouTube Community Posts
- Threads (Meta)
- Pinterest
- **Postiz** (multi-platform publishing)

## MCP Tools Available

| Tool | Description |
|------|-------------|
| `publish_event_to_social_media` | Publish to ALL enabled platforms at once |
| `get_enabled_social_platforms` | Check which platforms are configured |
| `preview_social_media_content` | Preview content before posting |
| `publish_to_twitter` | Publish to Twitter/X only |
| `publish_to_facebook` | Publish to Facebook only |
| `publish_to_instagram` | Publish to Instagram only (requires image) |
| `publish_to_linkedin` | Publish to LinkedIn only |
| `publish_via_postiz` | Publish to multiple platforms via Postiz |

## Platform Setup Instructions

### 1. Twitter/X

**Get API Keys:**
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a project and app
3. Generate API keys with Read + Write permissions

**Add to `.env`:**
```bash
TWITTER_API_KEY=your_consumer_key
TWITTER_API_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

**Requirements:**
- Twitter Developer Account (Free or Basic tier)
- API v2 access

---

### 2. Facebook

**Get API Credentials:**
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create app → Add "Facebook Login" and "Facebook Marketing API"
3. Get access token with `pages_manage_posts` permission

**Add to `.env`:**
```bash
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_long_lived_token
FACEBOOK_PAGE_ID=your_page_id
```

**Get Long-Lived Token:**
```bash
# Exchange short-lived token for long-lived (60 days)
curl -i -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

---

### 3. Instagram

**Get API Credentials:**
1. Connect Instagram Business Account to Facebook Page
2. Use same Meta credentials as Facebook
3. Get Instagram Account ID from Graph API

**Add to `.env`:**
```bash
# Same as Facebook, plus:
INSTAGRAM_ACCOUNT_ID=your_instagram_business_id
```

**Get Instagram Account ID:**
```bash
curl -i -X GET "https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_ACCESS_TOKEN"
# Then get Instagram ID:
curl -i -X GET "https://graph.facebook.com/v18.0/{PAGE_ID}?fields=instagram_business_account&access_token=YOUR_ACCESS_TOKEN"
```

**Requirements:**
- Instagram Business Account
- Connected to Facebook Page
- **Image required** for all Instagram posts

---

### 4. LinkedIn

**Get API Credentials:**
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Create app → Request access to "Sign In with LinkedIn" and "Share on LinkedIn"
3. Get OAuth 2.0 credentials

**Add to `.env`:**
```bash
LINKEDIN_ACCESS_TOKEN=your_access_token
LINKEDIN_PERSON_URN=urn:li:person:YOUR_ID
# OR for company pages:
LINKEDIN_COMPANY_ID=your_company_id
```

**Get Person URN:**
```bash
curl -X GET "https://api.linkedin.com/v2/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 5. TikTok

**Get API Credentials:**
1. Go to [TikTok for Developers](https://developers.tiktok.com/)
2. Create app → Request "Content Posting API" access
3. Get OAuth credentials

**Add to `.env`:**
```bash
TIKTOK_ACCESS_TOKEN=your_access_token
TIKTOK_ADVERTISER_ID=your_advertiser_id
```

**Note:** TikTok requires video content. Text/image posts not supported.

---

### 6. Pinterest

**Get API Credentials:**
1. Go to [Pinterest Developers](https://developers.pinterest.com/)
2. Create app → Get API credentials
3. Request OAuth access with `pins:write` scope

**Add to `.env`:**
```bash
PINTEREST_ACCESS_TOKEN=your_access_token
PINTEREST_BOARD_ID=your_board_id
```

---

### 7. Postiz (Recommended - Easiest Setup!)

**Postiz** is a multi-platform publishing tool that can post to ALL platforms at once:
- Facebook, Instagram, Twitter, LinkedIn, TikTok, YouTube, Pinterest, Reddit

**Setup:**
1. Sign up at [Postiz](https://postiz.com/) (or self-host)
2. Connect your social accounts through Postiz dashboard
3. Get API key

**Add to `.env`:**
```bash
POSTIZ_API_KEY=your_api_key
POSTIZ_URL=https://api.postiz.com
# OR if self-hosted:
POSTIZ_URL=https://your-postiz-instance.com
```

**Advantages:**
- ✅ One API key = all platforms
- ✅ Built-in scheduling
- ✅ Analytics dashboard
- ✅ No need to set up each platform individually
- ✅ Can self-host (open source)

---

## Usage Examples

### Publish to All Platforms

```python
# Via AI agent (MCP tool):
publish_event_to_social_media(
    event_id=123
)
```

### Preview Content First

```python
preview_social_media_content(event_id=123)
```

### Publish to Specific Platform

```python
publish_to_twitter(event_id=123)
publish_to_facebook(event_id=123)
publish_to_instagram(event_id=123)  # Requires image
publish_to_linkedin(event_id=123)
```

### Schedule Posts

```python
publish_event_to_social_media(
    event_id=123,
    schedule_time="2026-04-10T18:00:00"
)
```

### Publish to Custom Platform List

```python
publish_event_to_social_media(
    event_id=123,
    platforms=["twitter", "facebook", "linkedin"]
)
```

---

## Content Optimization

The system automatically generates platform-optimized content:

### Twitter/Threads (280 chars)
```
🎉 Summer Music Festival
📅 July 15, 2026 6:00 PM
📍 Chicago, IL

🎟️ Get tickets: https://tickets.com/events/123
```

### Instagram/Facebook (Medium)
```
🎉 Summer Music Festival

📅 July 15, 2026 at 6:00 PM
📍 Chicago, IL

Join us for an unforgettable experience!

🎟️ Tickets available now!
Link in bio or visit: https://tickets.com/events/123

#Events #LiveEvents #SummerMusicFestival
```

### LinkedIn (Long, Professional)
```
🎉 Exciting News: Summer Music Festival

We're thrilled to announce Summer Music Festival!

📅 Date: July 15, 2026
🕐 Time: 6:00 PM
📍 Location: Chicago, IL

[Full event description...]

🎟️ Secure your tickets now: https://tickets.com/events/123

Don't miss out on this amazing event!

#Events #EventMarketing #LiveEvents #SummerMusicFestival
```

---

## Automation Integration

### Auto-Publish on Event Creation

Add to your event creation flow:

```python
# After creating event:
event = create_event(...)

# Automatically publish to social media:
publish_event_to_social_media(event.id)
```

### Schedule Posts for Optimal Times

```python
from datetime import datetime, timedelta

# Post 2 weeks before event
post_time = event.date - timedelta(days=14)
post_time = post_time.replace(hour=18)  # 6 PM optimal posting time

publish_event_to_social_media(
    event_id=event.id,
    schedule_time=post_time.isoformat()
)
```

---

## Best Practices

### Posting Frequency

**Recommended schedule:**
- **4 weeks before**: Initial announcement
- **2 weeks before**: Reminder post
- **1 week before**: Last chance post
- **24 hours before**: Final reminder
- **Day of event**: Event day post

### Platform-Specific Tips

**Twitter:**
- Keep it concise
- Use relevant hashtags (3-5 max)
- Include eye-catching emoji
- Thread for longer announcements

**Instagram:**
- **Must have high-quality image**
- First line is crucial (what shows before "more")
- 20-30 hashtags max
- Story + Feed post combination

**LinkedIn:**
- More professional tone
- Longer, detailed descriptions
- Focus on value/networking/professional development
- Best for B2B/corporate events

**Facebook:**
- Create Facebook Event + post combination
- Tag location
- Encourage RSVPs/shares
- Use Facebook Live for behind-the-scenes

### Image Requirements

- **Instagram:** Required, min 1080x1080px
- **Pinterest:** Required, min 1000x1500px (vertical)
- **Twitter:** Optional, 1200x675px recommended
- **Facebook/LinkedIn:** Optional but highly recommended

Use your auto-generated flyers (`event.flyer_url`) for consistent branding.

---

## Troubleshooting

### "Skipped: API not configured"

**Solution:** Add the required API keys to your `.env` file

### "Instagram requires an image"

**Solution:** Ensure event has `flyer_url` or `image_url` set

### "Token expired"

**Solution:**
- **Facebook/Instagram:** Regenerate long-lived token (60-day expiry)
- **Twitter:** Access tokens don't expire, but check API access level
- **LinkedIn:** Refresh OAuth token (usually 60 days)

### Check Enabled Platforms

```python
get_enabled_social_platforms()
# Returns list of platforms ready to use
```

---

## Quick Start (Easiest Path)

**Want to get started fast? Use Postiz:**

1. Sign up at [Postiz.com](https://postiz.com/)
2. Connect your social accounts in Postiz dashboard
3. Add to `.env`:
   ```bash
   POSTIZ_API_KEY=your_key_here
   ```
4. Publish to all platforms:
   ```python
   publish_via_postiz(event_id=123)
   ```

Done! Your event is now on all connected platforms.

---

## Summary

You now have a unified MCP server that can publish events to **ALL major social media platforms** through a single interface. Your AI agent can:

✅ Publish to all platforms at once
✅ Preview content before posting
✅ Schedule posts for optimal times
✅ Auto-generate platform-optimized content
✅ Track which platforms are enabled
✅ Handle platform-specific requirements automatically

Choose your approach:
- **Easy:** Use Postiz (one API key for everything)
- **Advanced:** Set up individual platform APIs for maximum control
- **Hybrid:** Mix direct APIs + Postiz for different use cases

Add API keys to `.env` and start publishing!
