# Meta Ads API Integration - Complete Setup Guide

## Overview
This guide walks you through setting up Meta Ads API integration to automatically publish ads to Facebook and Instagram.

---

## 📋 Prerequisites

1. **Facebook Business Account**
2. **Facebook Page** (for your business)
3. **Instagram Business Account** (optional, for Instagram ads)
4. **Meta Ad Account** (linked to Business Account)
5. **Facebook App** (with Marketing API access)

---

## 🚀 Step-by-Step Setup

### Step 1: Create Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click **"My Apps"** → **"Create App"**
3. Select **"Business"** as app type
4. Fill in:
   - **App Name**: "AI Tickets Ad Manager"
   - **Contact Email**: your email
   - **Business Account**: Select your business account
5. Click **"Create App"**

**Save your App ID and App Secret** (found in Settings → Basic)

---

### Step 2: Add Marketing API

1. In your app dashboard, click **"Add Product"**
2. Find **"Marketing API"** and click **"Set Up"**
3. This enables your app to create and manage ads

---

### Step 3: Get Access Token

#### Option A: Short-Term Token (for testing)

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from dropdown
3. Click **"Get User Access Token"**
4. Select permissions:
   - `ads_management`
   - `ads_read`
   - `business_management`
   - `pages_read_engagement`
   - `pages_manage_ads`
5. Click **"Generate Access Token"**
6. **Copy the token** (valid for ~1 hour)

#### Option B: Long-Lived Token (for production)

1. Get short-term token from Option A
2. Exchange for long-lived token (60 days):

```bash
curl -G \
  -d "grant_type=fb_exchange_token" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "fb_exchange_token=SHORT_LIVED_TOKEN" \
  "https://graph.facebook.com/v18.0/oauth/access_token"
```

3. Response:
```json
{
  "access_token": "LONG_LIVED_TOKEN",
  "token_type": "bearer",
  "expires_in": 5184000
}
```

4. **Save this token** - use it in `.env`

---

### Step 4: Get Ad Account ID

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Click **"Ad Accounts"** in left menu
3. Select your ad account
4. URL will be: `https://business.facebook.com/adsmanager/manage/accounts?act=123456789`
5. **Copy the number after `act=`**
6. **Format**: `act_123456789` (include the `act_` prefix)

---

### Step 5: Get Facebook Page ID

1. Go to your [Facebook Page](https://www.facebook.com/your-page)
2. Click **"About"**
3. Scroll down to **"Page ID"**
4. **Copy the ID**

Alternatively, use Graph API:
```bash
curl -G \
  -d "access_token=YOUR_ACCESS_TOKEN" \
  "https://graph.facebook.com/v18.0/me/accounts"
```

---

### Step 6: Get Instagram Account ID (Optional)

1. Ensure Instagram account is linked to Facebook Page
2. Go to [Meta Business Suite](https://business.facebook.com/)
3. Click **"Instagram accounts"**
4. Select your account
5. **Copy the Instagram Account ID**

Alternatively, use Graph API:
```bash
curl -G \
  -d "fields=instagram_business_account" \
  -d "access_token=YOUR_ACCESS_TOKEN" \
  "https://graph.facebook.com/v18.0/YOUR_PAGE_ID"
```

Response:
```json
{
  "instagram_business_account": {
    "id": "17841405793187218"
  }
}
```

---

### Step 7: Configure AI Tickets

Add to your `.env` file:

```bash
# Meta Ads API Configuration
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_long_lived_access_token
META_AD_ACCOUNT_ID=act_123456789
META_BUSINESS_ID=your_business_id
FACEBOOK_PAGE_ID=your_facebook_page_id
INSTAGRAM_ACCOUNT_ID=your_instagram_account_id
```

Example:
```bash
META_APP_ID=1234567890123456
META_APP_SECRET=abc123def456ghi789jkl012mno345pq
META_ACCESS_TOKEN=EAABsbCS1iHgBO7ZCxKpZCZBqR4w...
META_AD_ACCOUNT_ID=act_987654321
META_BUSINESS_ID=234567890123456
FACEBOOK_PAGE_ID=112233445566778
INSTAGRAM_ACCOUNT_ID=17841405793187218
```

---

## 🧪 Test Your Integration

### Test 1: Verify Access Token

```bash
curl -G \
  -d "access_token=YOUR_ACCESS_TOKEN" \
  "https://graph.facebook.com/v18.0/me?fields=id,name"
```

Expected response:
```json
{
  "id": "123456789",
  "name": "Your Name"
}
```

---

### Test 2: Verify Ad Account Access

```bash
curl -G \
  -d "access_token=YOUR_ACCESS_TOKEN" \
  "https://graph.facebook.com/v18.0/act_123456789?fields=name,account_status,currency"
```

Expected response:
```json
{
  "name": "AI Tickets Ad Account",
  "account_status": 1,
  "currency": "USD",
  "id": "act_123456789"
}
```

---

### Test 3: Test Ad Publishing (Python)

Create `test_meta_ads.py`:

```python
import asyncio
from app.database import SessionLocal
from app.models import Event, AdCampaign, AdCreative
from app.services.meta_ads_integration import get_meta_api, publish_ad_to_meta
from app.config import settings

async def test_meta_publishing():
    """Test publishing an ad to Meta"""

    db = SessionLocal()

    # Get first ad
    ad = db.query(AdCreative).filter(
        AdCreative.status == "approved",
        AdCreative.platform.in_(["facebook", "instagram"])
    ).first()

    if not ad:
        print("No approved Facebook/Instagram ads found")
        return

    print(f"Publishing ad: {ad.headline}")

    # Get Meta API
    meta_api = get_meta_api()

    # Publish
    result = await publish_ad_to_meta(
        db=db,
        ad_creative=ad,
        meta_api=meta_api,
        facebook_page_id=settings.facebook_page_id,
        instagram_account_id=settings.instagram_account_id
    )

    if result['success']:
        print("✅ Success!")
        print(f"Meta Ad ID: {result['meta_ad_id']}")
        print(f"Meta Campaign ID: {result['meta_campaign_id']}")
    else:
        print("❌ Failed!")
        print(f"Error: {result['error']}")

    db.close()

if __name__ == "__main__":
    asyncio.run(test_meta_publishing())
```

Run:
```bash
python test_meta_ads.py
```

---

## 📊 What Happens When You Publish

### Publishing Flow:

```
1. User clicks "Publish to Meta" in UI
   ↓
2. POST /api/ad-campaigns/ads/{ad_id}/publish
   ↓
3. publish_ad_to_meta() function runs:

   a. Upload image to Meta
      - Downloads image from URL (Spotify, YouTube, Wikipedia)
      - Uploads to Meta Ad Account
      - Returns image_hash

   b. Create Campaign (if not exists)
      - Name: "Anuel AA - Awareness Campaign"
      - Objective: "REACH" or "CONVERSIONS"
      - Status: PAUSED (for safety)
      - Returns meta_campaign_id

   c. Create Ad Set
      - Targeting: Age, location, interests, languages
      - Budget: Daily budget from campaign
      - Schedule: Start/end dates
      - Returns meta_ad_set_id

   d. Create Ad Creative
      - Image: image_hash from step a
      - Message: Headline + body
      - Link: Event page URL
      - CTA: "Buy Tickets" or "Learn More"
      - Returns meta_creative_id

   e. Create Ad
      - Links ad_set + creative together
      - Status: PAUSED (user must activate in Meta Ads Manager)
      - Returns meta_ad_id

   f. Update database
      - Save meta_ad_id to ad_creative.platform_ad_id
      - Set status = "active"
      - Set published_at = now()

4. Return success + Meta IDs to UI
```

---

## 🎛️ Activate Your Ad

**IMPORTANT**: Ads are published to Meta with status **PAUSED** for safety.

### To activate:

1. Go to [Meta Ads Manager](https://business.facebook.com/adsmanager)
2. Find your campaign (e.g., "Anuel AA - Awareness Campaign")
3. Review the ad creative
4. Check targeting, budget, schedule
5. Click **"Turn On"** to activate
6. Ads will start running immediately

---

## 📈 Performance Tracking

### Sync Performance Data

The system can automatically pull performance metrics from Meta:

```python
from app.services.meta_ads_integration import sync_meta_performance, get_meta_api

# Sync performance for an ad
meta_api = get_meta_api()
result = await sync_meta_performance(db, ad_creative, meta_api)

print(f"Impressions: {result['impressions']}")
print(f"Clicks: {result['clicks']}")
print(f"Conversions: {result['conversions']}")
print(f"Spend: {result['spend']}")
print(f"CTR: {result['ctr']}")
print(f"ROAS: {result.get('roas', 'N/A')}")
```

### Schedule Daily Sync (Cron Job)

Create `sync_ad_performance.py`:

```python
import asyncio
from app.database import SessionLocal
from app.models import AdCreative
from app.services.meta_ads_integration import get_meta_api, sync_meta_performance

async def sync_all_meta_ads():
    """Sync performance for all active Meta ads"""

    db = SessionLocal()
    meta_api = get_meta_api()

    ads = db.query(AdCreative).filter(
        AdCreative.status == "active",
        AdCreative.platform.in_(["facebook", "instagram"]),
        AdCreative.platform_ad_id.isnot(None)
    ).all()

    print(f"Syncing {len(ads)} ads...")

    for ad in ads:
        try:
            result = await sync_meta_performance(db, ad, meta_api)
            print(f"✅ {ad.headline[:30]}... - {result['impressions']} impressions")
        except Exception as e:
            print(f"❌ {ad.headline[:30]}... - Error: {str(e)}")

    db.close()
    print("Sync complete!")

if __name__ == "__main__":
    asyncio.run(sync_all_meta_ads())
```

Add to crontab (runs daily at 2am):
```bash
0 2 * * * /path/to/venv/bin/python /path/to/sync_ad_performance.py
```

---

## 🔍 Debugging

### Common Errors

#### Error: "Invalid OAuth access token"
**Solution**: Token expired. Generate new long-lived token (Step 3)

#### Error: "Insufficient permissions"
**Solution**: Re-generate token with all required permissions:
- `ads_management`
- `ads_read`
- `business_management`
- `pages_manage_ads`

#### Error: "Ad account not found"
**Solution**: Verify `META_AD_ACCOUNT_ID` includes `act_` prefix

#### Error: "Page ID is required"
**Solution**: Set `FACEBOOK_PAGE_ID` in `.env`

#### Error: "Image upload failed"
**Solution**: Check image URL is publicly accessible

---

## 🔐 Security Best Practices

### 1. Never commit access tokens to Git
```bash
# .gitignore
.env
.env.*
```

### 2. Use environment variables
```python
# Good ✅
access_token = settings.meta_access_token

# Bad ❌
access_token = "EAABsbCS1iHgBO7ZCxKpZCZBqR4w..."
```

### 3. Rotate tokens regularly
- Long-lived tokens expire after 60 days
- Set calendar reminder to refresh before expiry

### 4. Use separate tokens for dev/production
```bash
# .env.development
META_ACCESS_TOKEN=dev_token_here

# .env.production
META_ACCESS_TOKEN=prod_token_here
```

---

## 📚 Additional Resources

### Meta Marketing API Documentation
- [Getting Started](https://developers.facebook.com/docs/marketing-api/get-started)
- [Campaign Structure](https://developers.facebook.com/docs/marketing-api/campaign-structure)
- [Targeting](https://developers.facebook.com/docs/marketing-api/audiences/reference/targeting)
- [Insights (Performance)](https://developers.facebook.com/docs/marketing-api/insights)

### Graph API Explorer
- [Test API calls](https://developers.facebook.com/tools/explorer/)

### Meta Business Help Center
- [Ads Manager Help](https://www.facebook.com/business/help)

---

## ✅ Checklist

Before going live, ensure:

- [ ] Facebook App created with Marketing API enabled
- [ ] Long-lived access token generated (60-day validity)
- [ ] Ad Account ID copied (with `act_` prefix)
- [ ] Facebook Page ID obtained
- [ ] Instagram Account ID obtained (if using Instagram ads)
- [ ] All credentials added to `.env`
- [ ] Test ad published successfully to Meta
- [ ] Ad appears in Meta Ads Manager
- [ ] Performance sync working

---

## 🎯 Next Steps

1. **Set up credentials** (Steps 1-7)
2. **Test integration** (`test_meta_ads.py`)
3. **Publish first ad** (via UI)
4. **Verify in Meta Ads Manager**
5. **Activate ad** (turn on in Ads Manager)
6. **Monitor performance** (sync daily)

---

## 💡 Pro Tips

### Budget Recommendations
- Start small: $10-20/day for awareness
- Test ads before scaling
- Monitor CTR (aim for 1%+)
- Pause low-performing ads after 3 days

### Best Practices
- Use high-quality images (640x640 minimum)
- Keep headlines under 40 characters for mobile
- Test Spanish vs English copy
- Target 25-mile radius for local events
- Run ads 30-45 days before event

### Performance Goals
- CTR: 1-3% (click-through rate)
- CPC: $0.50-$2.00 (cost per click)
- ROAS: 3:1 or higher (return on ad spend)
- Conversion rate: 5-15% (clicks → tickets)

---

## 🆘 Support

If you encounter issues:

1. Check [Meta Developer Community](https://developers.facebook.com/community/)
2. Review [Meta Ads API Changelog](https://developers.facebook.com/docs/graph-api/changelog)
3. Contact Meta Business Support (if you have managed ad spend)

---

**You're all set!** 🎉

Your AI Tickets platform can now automatically publish ads to Facebook and Instagram!
