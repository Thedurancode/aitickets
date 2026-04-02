# Google Ads API Integration - Complete Setup Guide

## Overview
This guide walks you through setting up Google Ads API integration to automatically publish Search, Display, and YouTube ads.

---

## 📋 Prerequisites

1. **Google Ads Account** (active and billing enabled)
2. **Google Cloud Project**
3. **Google Ads API enabled** on your project
4. **Developer Token** (from Google Ads)
5. **OAuth2 Credentials** (Client ID, Client Secret, Refresh Token)

---

## 🚀 Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Create Project"**
3. Name: "AI Tickets Ads"
4. Click **"Create"**

---

### Step 2: Enable Google Ads API

1. In your Google Cloud project, go to **APIs & Services** → **Library**
2. Search for **"Google Ads API"**
3. Click on it and click **"Enable"**

---

### Step 3: Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. If prompted, configure consent screen:
   - User Type: **External**
   - App name: "AI Tickets"
   - Support email: your email
   - Scopes: Add `https://www.googleapis.com/auth/adwords`
   - Test users: Add your email
4. Application type: **Desktop app**
5. Name: "AI Tickets OAuth Client"
6. Click **"Create"**

**Save your Client ID and Client Secret**

---

### Step 4: Get Developer Token

1. Go to [Google Ads](https://ads.google.com/)
2. Click **Tools & Settings** → **API Center** (under "Setup")
3. If you don't have a developer token:
   - Fill out the application form
   - Describe your use case: "Event ticketing platform auto-generating ads"
   - Wait for approval (can take 24-48 hours)

**For testing**, you can use test accounts without approval.

4. Copy your **Developer Token**

---

### Step 5: Generate Refresh Token

You need to exchange your OAuth2 credentials for a refresh token.

#### Option A: Using Google Ads API generate_user_credentials.py

1. Install Google Ads Python client:
```bash
pip install google-ads
```

2. Download and run the credential generator:
```bash
python -m google.ads.googleads.generate_user_credentials
```

3. Enter when prompted:
   - **Client ID**: (from Step 3)
   - **Client Secret**: (from Step 3)

4. A browser will open → Log in with your Google Ads account

5. Grant permissions

6. You'll receive:
   - **Refresh Token** (save this!)

#### Option B: Manual OAuth Flow

Create `get_refresh_token.py`:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/adwords']

CLIENT_ID = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
credentials = flow.run_local_server(port=0)

print(f"Refresh Token: {credentials.refresh_token}")
```

Run:
```bash
python get_refresh_token.py
```

**Save the refresh token**

---

### Step 6: Get Customer ID

1. Go to [Google Ads](https://ads.google.com/)
2. Click on your account name in top-right
3. You'll see your **Customer ID** (format: `123-456-7890`)
4. **Remove hyphens**: `1234567890`

---

### Step 7: Configure AI Tickets

Add to `.env`:

```bash
# Google Ads API Configuration
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=1234567890
GOOGLE_ADS_LOGIN_CUSTOMER_ID=  # Leave empty unless using MCC account
```

Example:
```bash
GOOGLE_ADS_DEVELOPER_TOKEN=ABcdEF1234567890
GOOGLE_ADS_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=GOCSPX-abc123def456
GOOGLE_ADS_REFRESH_TOKEN=1//0abcdefghijklmnop
GOOGLE_ADS_CUSTOMER_ID=9876543210
GOOGLE_ADS_LOGIN_CUSTOMER_ID=
```

---

## 🧪 Test Your Integration

### Test 1: Verify API Access

Create `test_google_ads_access.py`:

```python
from google.ads.googleads.client import GoogleAdsClient

credentials = {
    "developer_token": "YOUR_DEVELOPER_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "use_proto_plus": True
}

client = GoogleAdsClient.load_from_dict(credentials)
customer_service = client.get_service("CustomerService")

# Get customer info
customer_id = "1234567890"  # Your customer ID (no hyphens)
customer_resource_name = customer_service.customer_path(customer_id)

ga_service = client.get_service("GoogleAdsService")
query = f"""
    SELECT
        customer.id,
        customer.descriptive_name,
        customer.currency_code,
        customer.time_zone
    FROM customer
    WHERE customer.resource_name = '{customer_resource_name}'
"""

response = ga_service.search(customer_id=customer_id, query=query)

for row in response:
    print(f"Customer ID: {row.customer.id}")
    print(f"Name: {row.customer.descriptive_name}")
    print(f"Currency: {row.customer.currency_code}")
    print(f"Timezone: {row.customer.time_zone}")
```

Run:
```bash
python test_google_ads_access.py
```

Expected output:
```
Customer ID: 1234567890
Name: AI Tickets Ad Account
Currency: USD
Timezone: America/New_York
```

---

### Test 2: Test Search Ad Publishing

Create `test_google_search_ad.py`:

```python
import asyncio
from app.database import SessionLocal
from app.models import AdCreative
from app.services.google_ads_integration import get_google_ads_api, publish_search_ad_to_google

async def test_publishing():
    db = SessionLocal()

    # Get first approved Google search ad
    ad = db.query(AdCreative).filter(
        AdCreative.status == "approved",
        AdCreative.platform == "google_search"
    ).first()

    if not ad:
        print("No approved Google search ads found")
        return

    print(f"Publishing ad: {ad.headline}")

    # Get Google API
    google_api = get_google_ads_api()

    # Publish
    result = await publish_search_ad_to_google(db, ad, google_api)

    if result['success']:
        print("✅ Success!")
        print(f"Google Ad ID: {result['google_ad_id']}")
        print(f"Campaign ID: {result['google_campaign_id']}")
    else:
        print("❌ Failed!")
        print(f"Error: {result['error']}")

    db.close()

if __name__ == "__main__":
    asyncio.run(test_publishing())
```

Run:
```bash
python test_google_search_ad.py
```

---

## 📊 What Happens When You Publish

### Search Ad Publishing Flow:

```
1. User clicks "Publish to Google" in UI
   ↓
2. POST /api/ad-campaigns/ads/{ad_id}/publish
   ↓
3. publish_search_ad_to_google() runs:

   a. Create Campaign (if not exists)
      - Name: "Anuel AA - Queens Concert"
      - Type: SEARCH
      - Budget: $80/day
      - Status: PAUSED
      → Returns campaign_resource_name

   b. Create Ad Group
      - Name: "Anuel AA - Ad Group 1"
      - Max CPC: $5.00
      → Returns ad_group_resource_name

   c. Add Keywords
      - Keywords from targeting:
        ["anuel aa tickets", "reggaeton concert nyc", "latin concert queens"]
      - Match type: PHRASE
      → Returns keyword_resource_names[]

   d. Create Responsive Search Ad
      - Headlines: ["Anuel AA Tickets Queens", "May 5th at UBS Arena", "Get Tickets Now"]
      - Descriptions: ["Experience Anuel AA live...", "Limited VIP packages..."]
      - Final URL: https://ai-tickets.com/events/anuel-aa
      - Status: PAUSED
      → Returns ad_resource_name

   e. Update database
      - Save ad_resource_name to ad_creative.platform_ad_id
      - Set status = "active"
      - Set published_at = now()

4. Return success + Google resource names
```

---

## 🎛️ Activate Your Ad

**IMPORTANT**: Ads are created with status **PAUSED** for safety.

### To activate:

1. Go to [Google Ads](https://ads.google.com/)
2. Click **Campaigns** → Find your campaign
3. Review the ad:
   - Headlines, descriptions
   - Keywords
   - Budget, bids
4. Click **"Enable"** to activate
5. Ads will start running in Google Search results

---

## 📈 Performance Tracking

### Sync Performance Data

```python
from app.services.google_ads_integration import sync_google_performance, get_google_ads_api

google_api = get_google_ads_api()
result = await sync_google_performance(db, ad_creative, google_api)

print(f"Impressions: {result['impressions']}")
print(f"Clicks: {result['clicks']}")
print(f"Conversions: {result['conversions']}")
print(f"Spend: {result['spend']}")
print(f"CTR: {result['ctr']}")
print(f"CPC: {result['cpc']}")
```

### Schedule Daily Sync (Cron Job)

Create `sync_google_performance.py`:

```python
import asyncio
from app.database import SessionLocal
from app.models import AdCreative
from app.services.google_ads_integration import get_google_ads_api, sync_google_performance

async def sync_all_google_ads():
    """Sync performance for all active Google ads"""
    db = SessionLocal()
    google_api = get_google_ads_api()

    ads = db.query(AdCreative).filter(
        AdCreative.status == "active",
        AdCreative.platform.in_(["google_search", "google_display", "youtube"]),
        AdCreative.platform_ad_id.isnot(None)
    ).all()

    print(f"Syncing {len(ads)} ads...")

    for ad in ads:
        try:
            result = await sync_google_performance(db, ad, google_api)
            print(f"✅ {ad.headline[:30]}... - {result['impressions']} impressions")
        except Exception as e:
            print(f"❌ {ad.headline[:30]}... - Error: {str(e)}")

    db.close()

if __name__ == "__main__":
    asyncio.run(sync_all_google_ads())
```

Add to crontab (runs daily at 3am):
```bash
0 3 * * * /path/to/venv/bin/python /path/to/sync_google_performance.py
```

---

## 🎯 Ad Types Supported

### 1. Responsive Search Ads (RSA)
- **3-15 headlines** (max 30 chars each)
- **2-4 descriptions** (max 90 chars each)
- Google auto-tests combinations
- Best for: Search campaigns

### 2. Responsive Display Ads (RDA)
- **1-5 headlines** (max 30 chars)
- **1-5 descriptions** (max 90 chars)
- **Images**: 1.91:1 ratio (1200x628), Square (1200x1200)
- Best for: Brand awareness

### 3. YouTube Video Ads
- **Skippable in-stream** (5 sec skip)
- **Non-skippable** (15-20 sec)
- **Bumper** (6 sec)
- Best for: Video engagement

---

## 🎯 Targeting Options

### Geographic Targeting
```python
# Target New York City
location_ids = ["1023191"]  # NYC geo target ID

# Multiple locations
location_ids = ["1023191", "1014221"]  # NYC + Los Angeles
```

**Find Location IDs**:
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://googleads.googleapis.com/v15/geoTargetConstants:suggest?locale=en&country_code=US&names=New%20York"
```

### Keyword Targeting (Search Ads)
```python
keywords = [
    {"text": "concert tickets nyc", "match_type": "PHRASE"},
    {"text": "reggaeton concert", "match_type": "BROAD"},
    {"text": "anuel aa tickets", "match_type": "EXACT"}
]
```

**Match Types:**
- `EXACT` - Exact match only: [concert tickets]
- `PHRASE` - Phrase match: "concert tickets"
- `BROAD` - Broad match: concert tickets

### Audience Targeting (Display Ads)
```python
# Affinity audiences (interests)
affinity_audiences = [
    "Concert & Music Festival Fans",
    "Latin Music Fans"
]

# In-market audiences (purchase intent)
in_market_audiences = [
    "Event Tickets",
    "Concert Tickets"
]

# Demographics
demographics = {
    "age_ranges": ["18-24", "25-34", "35-44"],
    "genders": ["MALE", "FEMALE", "UNDETERMINED"],
    "parental_status": ["PARENT", "NOT_A_PARENT"]
}
```

---

## 💰 Budget & Bidding

### Campaign Budget
```python
# Daily budget
daily_budget_micros = 80_000_000  # $80/day (micros: 1,000,000 = $1)

# Total budget (for campaign with end date)
total_budget_micros = 2_400_000_000  # $2,400 total
```

### Bidding Strategies

**1. Manual CPC** (Cost-Per-Click)
```python
cpc_bid_micros = 5_000_000  # Max $5 per click
```

**2. Maximize Clicks**
```python
# Google automatically bids to get most clicks within budget
bidding_strategy = "MAXIMIZE_CLICKS"
```

**3. Target CPA** (Cost-Per-Acquisition)
```python
target_cpa_micros = 20_000_000  # Target $20 per conversion
```

**4. Maximize Conversions**
```python
# Google optimizes for most conversions within budget
bidding_strategy = "MAXIMIZE_CONVERSIONS"
```

---

## 🔍 Debugging

### Common Errors

#### Error: "AUTHENTICATION_ERROR"
**Solution**: Refresh token expired or invalid
- Generate new refresh token (Step 5)

#### Error: "DEVELOPER_TOKEN_NOT_APPROVED"
**Solution**: Developer token not yet approved
- Use test account while waiting
- Or wait for Google approval

#### Error: "CUSTOMER_NOT_ENABLED"
**Solution**: Google Ads API not enabled for customer
- Go to API Center in Google Ads
- Enable API access

#### Error: "REQUEST_ERROR: Invalid customer ID"
**Solution**: Customer ID format incorrect
- Remove hyphens: `1234567890` not `123-456-7890`

---

## 🔐 Security Best Practices

### 1. Never commit credentials
```bash
# .gitignore
.env
.env.*
google-ads.yaml
```

### 2. Use environment variables
```python
# Good ✅
developer_token = settings.google_ads_developer_token

# Bad ❌
developer_token = "ABcdEF1234567890"
```

### 3. Rotate refresh tokens regularly
- Refresh tokens don't expire but can be revoked
- Regenerate every 6 months for security

### 4. Use separate tokens for dev/production
```bash
# .env.development
GOOGLE_ADS_CUSTOMER_ID=1234567890  # Test account

# .env.production
GOOGLE_ADS_CUSTOMER_ID=9876543210  # Production account
```

---

## 📚 Additional Resources

### Google Ads API Documentation
- [Getting Started](https://developers.google.com/google-ads/api/docs/start)
- [OAuth Guide](https://developers.google.com/google-ads/api/docs/oauth/overview)
- [Search Ads](https://developers.google.com/google-ads/api/docs/samples/set-up-search-campaign)
- [Performance Reporting](https://developers.google.com/google-ads/api/docs/reporting/overview)

### API Reference
- [Python Client Library](https://github.com/googleads/google-ads-python)
- [Code Examples](https://github.com/googleads/google-ads-python/tree/main/examples)

### Google Ads Help
- [Ads Help Center](https://support.google.com/google-ads)

---

## ✅ Checklist

Before going live:

- [ ] Google Cloud project created
- [ ] Google Ads API enabled
- [ ] OAuth2 credentials created (Client ID + Secret)
- [ ] Developer token obtained (or using test account)
- [ ] Refresh token generated
- [ ] Customer ID copied (no hyphens)
- [ ] All credentials in `.env`
- [ ] Test ad published successfully
- [ ] Ad appears in Google Ads
- [ ] Performance sync working

---

## 🎯 Next Steps

1. **Set up credentials** (Steps 1-7)
2. **Test API access** (`test_google_ads_access.py`)
3. **Publish first ad** (via UI)
4. **Verify in Google Ads**
5. **Activate ad** (enable in Google Ads)
6. **Monitor performance** (sync daily)

---

## 💡 Pro Tips

### Budget Recommendations
- Start with $50-100/day for search
- Test keywords before scaling
- Monitor Quality Score (aim for 7+)
- Pause keywords with CTR < 1%

### Best Practices
- Use 10-20 keywords per ad group
- Include negative keywords (e.g., "free")
- Test 3+ headline variations
- Use all 15 headline slots for RSAs
- Enable auto-apply recommendations

### Performance Goals
- CTR: 2-5% (search ads)
- Quality Score: 7-10
- CPC: $0.50-$3.00 (varies by industry)
- Conversion rate: 3-10%

---

**You're ready to publish Google Ads!** 🚀
