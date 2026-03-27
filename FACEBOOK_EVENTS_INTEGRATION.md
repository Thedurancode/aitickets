# Facebook Events API Integration Guide

## TL;DR: It's Complicated ⚠️

Facebook Events API **exists but is heavily restricted**. Here's what you need to know in 2025:

---

## 🚨 Current Status (2025)

### **The Bad News:**
- ❌ **Regular Graph API for events is severely limited** (GDPR restrictions since ~2018)
- ❌ **Event creation was removed from public API in 2014**
- ❌ **Cannot read public events from pages you don't own**
- ❌ **Most event-related endpoints deprecated or restricted**

### **The Good News:**
- ✅ **Official Events API exists** (but requires approval)
- ✅ **Can create events on Pages you manage**
- ✅ **Can post about events to Facebook** (what you already have via Postiz/Meta Ads)

---

## 📊 What's Actually Possible

### **Option 1: Official Events API** (Restricted)
**Status:** Requires Meta partnership/approval
**Best For:** Large event organizers, official ticketing platforms

**What you CAN do:**
- Create events on Facebook Pages you manage
- Update event details programmatically
- Manage ticket links
- Access event insights

**What you CANNOT do:**
- Create events on behalf of users
- Access public event data from other pages
- Scrape event listings

**Requirements:**
- ✅ Business Verification
- ✅ App Review & Approval
- ✅ `pages_manage_events` permission (advanced access)
- ✅ `pages_read_engagement` permission
- ✅ Partnership/approval from Meta

**API Endpoint:**
```
POST /{page-id}/events
GET /{event-id}
POST /{event-id}  # Update
DELETE /{event-id}
```

**Documentation:** https://developers.facebook.com/docs/pages/official-events/

---

### **Option 2: What You Already Have** ✅ (Recommended)

You **already** have better Facebook integration through:

#### **A. Postiz Social Media Publishing**
**File:** `app/services/social_media.py`

**What you can do:**
- ✅ Post event announcements to Facebook Pages
- ✅ Include event flyer/image
- ✅ Add ticket link
- ✅ Schedule posts
- ✅ Post to multiple pages at once

**Example:**
```python
from app.services.social_media import post_to_social

post_to_social(
    text="""🎉 Jazz Night at Blue Note

📅 March 30, 2025 at 8:00 PM
📍 Blue Note Jazz Club
🎫 Tickets: https://ai-tickets.fly.dev/events/123

Limited seats available!""",
    integration_ids=["facebook_page_123"],
    image_urls=["https://event-flyer.jpg"],
    post_type="now"
)
```

**Result:** Event announcement visible to all your Facebook followers

---

#### **B. Meta Ads (Facebook/Instagram Ads)**
**File:** `app/services/meta_ads.py`

**What you can do:**
- ✅ Create paid ad campaigns for events
- ✅ Target by location (radius around venue)
- ✅ Audience targeting (interests, demographics)
- ✅ Track performance (impressions, clicks, conversions)
- ✅ A/B test ad creatives

**Example:**
```python
from app.services.meta_ads import create_event_campaign

create_event_campaign(
    db=db,
    event_id=123,
    daily_budget_cents=2000,  # $20/day
    radius_miles=25,
    objective="OUTCOME_TRAFFIC"
)
```

**Result:** Paid ads on Facebook/Instagram driving traffic to your ticket page

---

### **Option 3: Manual Facebook Events** (Current Best Practice)

**What most event organizers do:**
1. Create event on Facebook manually
2. Use your AI Tickets platform for actual ticketing
3. Link Facebook Event to your ticket page
4. Promote via posts (automated via Postiz)
5. Run ads (automated via Meta Ads API)

**Workflow:**
```
[Your Event]
    ↓
[Manual Facebook Event Creation]
    ↓
[Add ticket link → https://your-site.com/events/123]
    ↓
[Automated Posts via Postiz] ✅
    ↓
[Automated Ads via Meta Ads] ✅
    ↓
[Track performance via Meta Ads API] ✅
```

---

## 🔧 Implementation Options

### **If You Want Official Events API Access:**

#### **Step 1: Business Verification**
- Verify your business with Meta
- Provide legal documentation
- Can take 3-7 business days

#### **Step 2: Create Facebook App**
```bash
1. Go to developers.facebook.com
2. Create New App → Business Type
3. Add "Pages" product
4. Add "Official Events API" product
```

#### **Step 3: Request Permissions**
Required permissions:
- `pages_manage_events` (Advanced Access)
- `pages_read_engagement` (Advanced Access)
- `pages_manage_metadata` (Standard Access)

#### **Step 4: App Review**
- Submit for App Review
- Explain use case
- Provide video demo
- Wait 5-7 days for approval

#### **Step 5: Implement API**
```python
import requests

def create_facebook_event(page_id, access_token, event_data):
    """Create Facebook event via Official Events API."""
    url = f"https://graph.facebook.com/v22.0/{page_id}/events"

    payload = {
        "name": event_data["name"],
        "start_time": event_data["start_time"],  # ISO 8601
        "end_time": event_data["end_time"],
        "description": event_data["description"],
        "location": event_data["location"],
        "ticket_uri": event_data["ticket_url"],
        "is_online": False,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()
```

---

## 📋 Comparison: Options

| Feature | Official Events API | Postiz Posts | Meta Ads | Manual |
|---------|-------------------|--------------|----------|--------|
| **Create FB Event** | ✅ Yes | ❌ No (post only) | ❌ No | ✅ Yes |
| **Approval Required** | ✅ Yes (hard) | ❌ No | ⚠️ Ad account | ❌ No |
| **Automation** | ✅ Full | ✅ Full | ✅ Full | ❌ Manual |
| **Cost** | Free | Free | Paid ads | Free |
| **Effort** | 🔥 Very High | ⭐ Already Done | ⭐ Already Done | ⭐ Easy |
| **Reach** | Organic | Organic | Paid | Organic |
| **Best For** | Large orgs | Announcements | Promotion | Small events |

---

## 🎯 My Recommendation

### **Don't Bother with Official Events API** ❌

**Why:**
1. **Extremely difficult approval process** (weeks of work)
2. **You already have better alternatives** (Postiz + Meta Ads)
3. **Manual Facebook Events work fine** for organic reach
4. **Facebook Events are declining** in importance (most discovery happens on ticketing platforms)

### **What to Do Instead:** ✅

**Use your existing integrations:**

1. **Create event in AI Tickets** (your platform)
2. **Auto-post to Facebook** via Postiz ✅
3. **Run Facebook/Instagram ads** via Meta Ads API ✅
4. **Manually create Facebook Event** (5 minutes)
5. **Link Facebook Event to your ticket page**

**Result:**
- ✅ Full automation for posts & ads
- ✅ Facebook Event for organic discovery
- ✅ Single source of truth (your platform)
- ✅ No API approval needed

---

## 💡 Enhanced Strategy

### **Add This to Your Event Publisher:**

I can enhance your `event_publisher.py` to auto-generate Facebook Event instructions:

```python
def generate_facebook_event_manual_instructions(event):
    """Generate copy-paste instructions for manual Facebook Event creation."""

    return {
        "platform": "facebook_manual",
        "instructions": "Create Facebook Event manually with these details:",
        "event_name": event.name,
        "start_time": f"{event.event_date} {event.event_time}",
        "location": event.venue.name if event.venue else "TBD",
        "description": event.description,
        "ticket_url": f"{settings.base_url}/events/{event.id}",
        "cover_photo_url": event.image_url,
        "copy_paste_description": f"""{event.name}

{event.description}

📅 {event.event_date} at {event.event_time}
📍 {event.venue.name if event.venue else 'TBD'}

🎫 Get tickets: {settings.base_url}/events/{event.id}

Organized by {settings.org_name}""",
        "automated": {
            "facebook_post": "✅ Will auto-post via Postiz",
            "facebook_ads": "✅ Will auto-create via Meta Ads API"
        }
    }
```

---

## 🔑 Environment Variables (If Pursuing Official API)

```env
# Facebook Official Events API (requires approval)
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_token
FACEBOOK_PAGE_ID=your_page_id
```

---

## 📚 Resources

- **Official Events API Docs:** https://developers.facebook.com/docs/pages/official-events/
- **Graph API Events Reference:** https://developers.facebook.com/docs/graph-api/reference/event/
- **Business Verification:** https://www.facebook.com/business/help/
- **App Review:** https://developers.facebook.com/docs/app-review/

---

## ✅ Final Verdict

| Question | Answer |
|----------|--------|
| **Can you integrate Facebook Events API?** | Yes, but extremely difficult |
| **Should you?** | **No** - use what you have |
| **What do you have?** | ✅ Postiz (auto posts) + ✅ Meta Ads (paid promo) |
| **What's missing?** | Programmatic FB Event creation (not worth it) |
| **Recommendation** | Manual FB Events + automated posts/ads |

---

## 🚀 Action Items

### **Do This:**
1. ✅ Continue using Postiz for Facebook posts
2. ✅ Continue using Meta Ads for promotion
3. ✅ Manually create Facebook Events (5 min/event)
4. ✅ Add "Create Facebook Event" reminder to your publishing workflow

### **Don't Do This:**
1. ❌ Pursue Official Events API approval (not worth the effort)
2. ❌ Try to scrape Facebook Events (against TOS)
3. ❌ Use unofficial/third-party Facebook Event APIs (risky)

---

**Bottom Line:** You asked about Facebook Events. The API exists but is extremely restricted. **You already have better Facebook integration** through Postiz (posts) and Meta Ads (promotion). Just create the Facebook Event manually (5 minutes) and let your automated systems handle the rest.
