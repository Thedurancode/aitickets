# Meta Ads API - Quick Reference

## 🔑 Core Classes

### MetaAdsAPI Class
```python
from app.services.meta_ads_integration import MetaAdsAPI

meta_api = MetaAdsAPI(
    access_token="YOUR_ACCESS_TOKEN",
    ad_account_id="act_123456789"
)
```

---

## 📝 API Methods

### 1. Create Campaign
```python
campaign_id = meta_api.create_campaign(
    name="Anuel AA - Awareness Campaign",
    objective="REACH",  # REACH, LINK_CLICKS, CONVERSIONS, VIDEO_VIEWS
    status="PAUSED",
    special_ad_categories=["NONE"]
)
# Returns: "123456789012345"
```

**Objectives:**
- `REACH` - Maximize impressions
- `LINK_CLICKS` - Drive traffic
- `CONVERSIONS` - Purchase events
- `VIDEO_VIEWS` - Video engagement
- `BRAND_AWARENESS` - Brand lift

---

### 2. Create Ad Set (Targeting + Budget)
```python
ad_set_id = meta_api.create_ad_set(
    campaign_id="123456789",
    name="Anuel AA - Ad Set 1",
    optimization_goal="LINK_CLICKS",
    billing_event="IMPRESSIONS",
    bid_amount=500,  # $5.00 max bid (in cents)
    daily_budget=5000,  # $50/day (in cents)
    targeting={
        "age_min": 18,
        "age_max": 35,
        "genders": [1, 2],  # All
        "geo_locations": {
            "countries": ["US"],
            "cities": [
                {"key": "2490299", "radius": 25, "distance_unit": "mile"}  # NYC
            ]
        },
        "locales": [6, 24],  # Spanish + English
        "interests": [
            {"id": "6003139266461", "name": "Live music"}
        ]
    },
    start_time=datetime(2026, 4, 1),
    end_time=datetime(2026, 5, 5)
)
# Returns: "234567890123456"
```

**Optimization Goals:**
- `REACH` - Unique users
- `LINK_CLICKS` - Link clicks
- `IMPRESSIONS` - Ad views
- `LANDING_PAGE_VIEWS` - Page loads
- `OFFSITE_CONVERSIONS` - Pixel events

**Billing Events:**
- `IMPRESSIONS` - Pay per 1000 impressions
- `LINK_CLICKS` - Pay per click

---

### 3. Upload Image
```python
image_hash = meta_api.upload_image(
    image_url="https://i.scdn.co/image/abc123..."  # Spotify, YouTube, Wikipedia
)
# Returns: "abc123def456ghi789"
```

---

### 4. Create Ad Creative
```python
creative_id = meta_api.create_ad_creative(
    name="Anuel AA - Ad Creative 1",
    image_hash="abc123def456",
    message="¡Anuel AA Live in Queens! 🔥\n\nMay 5th - Don't miss out!",
    link="https://ai-tickets.com/events/anuel-aa-queens",
    call_to_action_type="SHOP_NOW",
    page_id="112233445566778",  # Facebook Page ID
    instagram_account_id="17841405793187218"  # Optional
)
# Returns: "345678901234567"
```

**CTA Types:**
- `LEARN_MORE` - Default
- `SHOP_NOW` - E-commerce
- `SIGN_UP` - Registration
- `DOWNLOAD` - App download
- `BOOK_TRAVEL` - Travel booking
- `GET_TICKETS` - Event tickets (if available)

---

### 5. Create Ad
```python
ad_id = meta_api.create_ad(
    ad_set_id="234567890",
    creative_id="345678901",
    name="Anuel AA - Ad 1",
    status="PAUSED"
)
# Returns: "456789012345678"
```

---

### 6. Get Performance Insights
```python
insights = meta_api.get_ad_insights(
    ad_id="456789012345678",
    date_preset="last_7d",  # today, yesterday, last_7d, last_30d, lifetime
    fields=[
        "impressions",
        "clicks",
        "spend",
        "reach",
        "ctr",
        "cpc",
        "actions"  # Includes conversions
    ]
)

print(f"Impressions: {insights['impressions']}")
print(f"Clicks: {insights['clicks']}")
print(f"Spend: ${float(insights['spend']):.2f}")
print(f"CTR: {insights['ctr']}%")
print(f"CPC: ${float(insights['cpc']):.2f}")
```

**Response:**
```json
{
  "impressions": "12543",
  "clicks": "342",
  "spend": "45.67",
  "reach": "9821",
  "ctr": "2.73",
  "cpc": "0.13",
  "actions": [
    {
      "action_type": "purchase",
      "value": "28"
    }
  ]
}
```

---

### 7. Update Ad Status
```python
meta_api.update_ad_status(
    ad_id="456789012345678",
    status="ACTIVE"  # ACTIVE, PAUSED, DELETED
)
```

---

## 🎯 High-Level Functions

### Publish Full Ad to Meta
```python
from app.services.meta_ads_integration import publish_ad_to_meta, get_meta_api
from app.database import SessionLocal
from app.models import AdCreative
from app.config import settings

db = SessionLocal()
ad = db.query(AdCreative).filter(AdCreative.id == 1).first()

meta_api = get_meta_api()
result = await publish_ad_to_meta(
    db=db,
    ad_creative=ad,
    meta_api=meta_api,
    facebook_page_id=settings.facebook_page_id,
    instagram_account_id=settings.instagram_account_id
)

if result['success']:
    print(f"Published! Meta Ad ID: {result['meta_ad_id']}")
else:
    print(f"Failed: {result['error']}")
```

---

### Sync Performance Data
```python
from app.services.meta_ads_integration import sync_meta_performance

result = await sync_meta_performance(db, ad, meta_api)

print(f"Impressions: {result['impressions']}")
print(f"Clicks: {result['clicks']}")
print(f"Conversions: {result['conversions']}")
print(f"ROAS: {result.get('roas', 'N/A')}")
```

---

## 🌍 Targeting Options

### Geographic Targeting
```python
# Country
geo_locations = {
    "countries": ["US", "MX", "PR"]
}

# City with radius
geo_locations = {
    "countries": ["US"],
    "cities": [
        {"key": "2490299", "radius": 25, "distance_unit": "mile"}  # NYC, 25 miles
    ]
}

# Multiple cities
geo_locations = {
    "cities": [
        {"key": "2490299", "radius": 25, "distance_unit": "mile"},  # NYC
        {"key": "2490299", "radius": 15, "distance_unit": "mile"}   # LA
    ]
}

# DMA (Designated Market Area)
geo_locations = {
    "regions": [
        {"key": "3847"}  # New York DMA
    ]
}
```

**Find City Keys:**
```bash
curl -G \
  -d "type=adgeolocation" \
  -d "location_types=['city']" \
  -d "q=New York" \
  -d "access_token=YOUR_TOKEN" \
  "https://graph.facebook.com/v18.0/search"
```

---

### Demographic Targeting
```python
targeting = {
    "age_min": 18,
    "age_max": 65,
    "genders": [1],  # 1 = men, 2 = women, [1,2] = all
}
```

---

### Interest Targeting
```python
targeting = {
    "interests": [
        {"id": "6003139266461", "name": "Live music"},
        {"id": "6003277229371", "name": "Reggaeton"},
        {"id": "6003236849092", "name": "Latin music"}
    ]
}
```

**Find Interest IDs:**
```bash
curl -G \
  -d "type=adinterest" \
  -d "q=reggaeton" \
  -d "access_token=YOUR_TOKEN" \
  "https://graph.facebook.com/v18.0/search"
```

---

### Behavior Targeting
```python
targeting = {
    "behaviors": [
        {"id": "6002714895372", "name": "Frequent travelers"},
        {"id": "6015559470583", "name": "Engaged shoppers"}
    ]
}
```

---

### Language Targeting
```python
targeting = {
    "locales": [6, 24]  # 6 = Spanish (all), 24 = English (US)
}
```

**Common Locale IDs:**
- `6` - Spanish (all)
- `24` - English (US)
- `28` - English (UK)
- `4` - French (all)
- `19` - Portuguese (Brazil)

---

### Device Targeting
```python
targeting = {
    "device_platforms": ["mobile", "desktop"],
    "publisher_platforms": ["facebook", "instagram"],
    "facebook_positions": ["feed", "story", "video_feeds"],
    "instagram_positions": ["stream", "story", "explore"]
}
```

**Platform Options:**
- `facebook` - Facebook
- `instagram` - Instagram
- `messenger` - Messenger
- `audience_network` - Meta Audience Network

**Facebook Positions:**
- `feed` - News Feed
- `story` - Stories
- `video_feeds` - Video feeds
- `right_hand_column` - Right column (desktop)

**Instagram Positions:**
- `stream` - Feed
- `story` - Stories
- `explore` - Explore tab
- `reels` - Reels

---

## 💰 Budget & Bidding

### Budget Types
```python
# Daily budget
daily_budget = 5000  # $50/day (in cents)

# Lifetime budget (for ad set)
lifetime_budget = 150000  # $1,500 total (in cents)
```

### Bid Strategies
```python
# Manual bid (cost cap)
bid_amount = 500  # Max $5 per result

# Lowest cost (automatic)
# Don't set bid_amount, Meta optimizes automatically
```

---

## 📊 Performance Metrics

### Available Fields
```python
fields = [
    # Delivery
    "impressions",
    "reach",
    "frequency",

    # Engagement
    "clicks",
    "unique_clicks",
    "ctr",
    "unique_ctr",

    # Cost
    "spend",
    "cpc",
    "cpm",
    "cpp",

    # Conversions
    "actions",
    "cost_per_action_type",
    "conversions",
    "conversion_values",

    # Video (if video ad)
    "video_avg_time_watched_actions",
    "video_p25_watched_actions",
    "video_p50_watched_actions",
    "video_p75_watched_actions",
    "video_p100_watched_actions"
]
```

### Action Types
```python
# In insights['actions']
action_types = [
    "like",
    "comment",
    "share",
    "post_engagement",
    "page_engagement",
    "link_click",
    "post",
    "photo_view",
    "video_view",
    "purchase",  # Conversions
    "add_to_cart",
    "initiate_checkout",
    "lead"
]
```

---

## 🔧 Helper Functions

### Create Targeting Spec
```python
targeting = meta_api.create_targeting_spec(
    age_min=18,
    age_max=35,
    genders=[1, 2],
    geo_locations={
        "countries": ["US"],
        "cities": [{"key": "2490299", "radius": 25, "distance_unit": "mile"}]
    },
    interests=[
        {"id": "6003139266461", "name": "Live music"}
    ],
    locales=[6, 24]  # Spanish + English
)
```

---

## 🚨 Error Handling

### Common Errors
```python
try:
    campaign_id = meta_api.create_campaign(...)
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print("Bad request:", e.response.json())
    elif e.response.status_code == 401:
        print("Invalid access token")
    elif e.response.status_code == 403:
        print("Insufficient permissions")
    elif e.response.status_code == 190:
        print("Access token expired")
```

### Error Response Format
```json
{
  "error": {
    "message": "Invalid OAuth access token",
    "type": "OAuthException",
    "code": 190,
    "fbtrace_id": "ABC123"
  }
}
```

---

## 📈 Performance Optimization Tips

### 1. Start Paused
```python
# Always create with status="PAUSED"
# Review in Ads Manager before activating
meta_api.create_campaign(status="PAUSED")
```

### 2. Test Creatives
```python
# Create multiple creatives for A/B testing
creative_1 = meta_api.create_ad_creative(message="Spanish copy...")
creative_2 = meta_api.create_ad_creative(message="English copy...")
```

### 3. Monitor Daily
```python
# Check performance every day
insights = meta_api.get_ad_insights(ad_id, date_preset="yesterday")
if float(insights['ctr']) < 1.0:
    print("Low CTR - consider pausing")
```

### 4. Optimize Targeting
```python
# Narrow targeting for better performance
targeting = {
    "age_min": 21,  # Narrower age range
    "age_max": 35,
    "interests": [...],  # Add 2-3 interests
    "behaviors": [...],  # Add relevant behaviors
    "geo_locations": {"cities": [...]}  # Target specific cities
}
```

---

## ✅ Complete Example

```python
from app.services.meta_ads_integration import MetaAdsAPI
from datetime import datetime, timedelta

# Initialize
meta_api = MetaAdsAPI(
    access_token="YOUR_TOKEN",
    ad_account_id="act_123456789"
)

# 1. Create campaign
campaign_id = meta_api.create_campaign(
    name="Anuel AA - Queens Concert",
    objective="CONVERSIONS",
    status="PAUSED"
)

# 2. Upload image
image_hash = meta_api.upload_image(
    "https://i.scdn.co/image/anuel-aa-profile.jpg"
)

# 3. Create targeting
targeting = meta_api.create_targeting_spec(
    age_min=18,
    age_max=40,
    geo_locations={
        "cities": [{"key": "2490299", "radius": 25, "distance_unit": "mile"}]
    },
    interests=[{"id": "6003277229371", "name": "Reggaeton"}],
    locales=[6, 24]
)

# 4. Create ad set
ad_set_id = meta_api.create_ad_set(
    campaign_id=campaign_id,
    name="Anuel AA - Conversion Ad Set",
    optimization_goal="OFFSITE_CONVERSIONS",
    billing_event="IMPRESSIONS",
    bid_amount=1000,  # $10
    daily_budget=8000,  # $80/day
    targeting=targeting,
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(days=30)
)

# 5. Create creative
creative_id = meta_api.create_ad_creative(
    name="Anuel AA - Ad 1",
    image_hash=image_hash,
    message="¡Anuel AA Live in Queens! 🔥\n\nMay 5th at UBS Arena\nGet your tickets now!",
    link="https://ai-tickets.com/events/anuel-aa",
    call_to_action_type="SHOP_NOW",
    page_id="YOUR_PAGE_ID"
)

# 6. Create ad
ad_id = meta_api.create_ad(
    ad_set_id=ad_set_id,
    creative_id=creative_id,
    name="Anuel AA - Conversion Ad 1",
    status="PAUSED"
)

print(f"✅ Ad created: {ad_id}")
print("Go to Meta Ads Manager to review and activate!")
```

---

**You're ready to publish ads to Meta!** 🚀
