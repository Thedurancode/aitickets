# Ad Campaign System - Demo & Testing

## 🎯 Demo Script

### Complete End-to-End Flow Test

Run the complete ad campaign workflow demo:

```bash
python3 test_complete_ad_flow.py
```

### What It Demonstrates

The demo shows the **full 8-step workflow**:

1. **Create Event** - Anuel AA concert in Queens, NY
2. **Run Research** - Discover images from Spotify, YouTube, Wikipedia
3. **Generate Campaigns** - Auto-create Meta, Google, Email campaigns
4. **Review & Customize** - Edit headlines and ad copy
5. **Approve Ads** - Mark ads as ready for publishing
6. **Publish Ads** - Simulate publishing to Meta and Google
7. **Track Performance** - Simulate metrics (impressions, clicks, conversions)
8. **Summary** - Show complete results and next steps

### Sample Output

```
████████████████████████████████████████████████████████████████████████████████
█                                                                              █
█                   COMPLETE AD CAMPAIGN FLOW - DEMO                           █
█          Event → Research → Generate → Customize → Approve → Publish         █
█                                                                              █
████████████████████████████████████████████████████████████████████████████████

================================================================================
STEP 1: CREATE EVENT
================================================================================

✅ Event Created!
   Name: Anuel AA - Las Leyendas Nunca Mueren Tour
   Venue: UBS Arena
   Date: May 05, 2026
   Time: 21:00
   Ticket Tiers: 4
   Price Range: $75 - $1500

================================================================================
STEP 2: RUN RESEARCH AGENT
================================================================================

🔍 Researching artist: Anuel AA
   Discovering images from Spotify, YouTube, Wikipedia...

✅ Research Complete!

📸 IMAGES DISCOVERED:
   Spotify Profile: https://i.scdn.co/image/anuel-aa-profile-640x640.jpg
   Album Artwork: https://i.scdn.co/image/llnm-album-640x640.jpg
   YouTube Thumbnail: https://i.ytimg.com/vi/abc123/maxresdefault.jpg
   Wikipedia Photo: https://upload.wikimedia.org/wikipedia/commons/anuel...

🎯 TARGET AUDIENCE:
   Primary: 18-35 urban Latino youth, reggaeton fans
   Age Range: 18-35
   Interests: Reggaeton, Latin Urban Music, Bad Bunny, Ozuna

================================================================================
STEP 3: AUTO-GENERATE AD CAMPAIGNS
================================================================================

🤖 Generating campaigns...
   Creating Meta Awareness, Meta Conversion, Google Search, Email campaigns...

✅ Campaigns Generated!
   Total Campaigns: 4
   Total Ads: 9
   Total Budget: $1,900.00

📊 CAMPAIGNS CREATED:
   • Anuel AA - Awareness Campaign
     Platform: META | Type: awareness
     Ads: 3 | Budget: $500.00
   • Anuel AA - Ticket Sales Campaign
     Platform: META | Type: conversion
     Ads: 2 | Budget: $800.00
   • Anuel AA - Search Campaign
     Platform: GOOGLE | Type: search
     Ads: 2 | Budget: $600.00
   • Anuel AA - Email Series
     Platform: EMAIL | Type: nurture
     Ads: 2 | Budget: $0.00

[... continues through all 8 steps ...]

================================================================================
DEMO COMPLETE!
================================================================================

🎯 This demo showed the complete ad campaign workflow:
   Event → Research → Generate → Customize → Approve → Publish → Track

💡 In production:
   • Research agent uses real APIs (Spotify, YouTube, Wikipedia)
   • Publishing actually calls Meta Ads API and Google Ads API
   • Performance syncs daily from ad platforms
   • All controlled via admin UI

📚 See documentation:
   • META_ADS_SETUP_GUIDE.md - Set up Meta credentials
   • GOOGLE_ADS_SETUP_GUIDE.md - Set up Google credentials
   • ADS_INTEGRATION_SUMMARY.md - Complete overview
```

---

## 🧪 Individual Component Tests

### Test Meta Ads Publishing

```bash
python3 test_meta_ads.py
```

Creates and publishes a test ad to Meta (Facebook/Instagram).

**Requirements**: Meta credentials in `.env`

### Test Google Ads Publishing

```bash
python3 test_google_ads.py
```

Creates and publishes a test search ad to Google.

**Requirements**: Google Ads credentials in `.env`

### Test Campaign Generator

```bash
python3 test_campaign_generator.py
```

Tests the auto-generation of ad campaigns from research data.

---

## 📋 Test Checklist

Before running tests:

- [ ] Database initialized (`alembic upgrade head`)
- [ ] At least one venue exists in database
- [ ] `.env` configured (for API tests)

### Meta Ads Tests

- [ ] Meta credentials in `.env`
- [ ] Facebook Page ID configured
- [ ] Instagram Account ID configured (optional)
- [ ] Test ad publishes successfully
- [ ] Ad appears in Meta Ads Manager

### Google Ads Tests

- [ ] Google Ads credentials in `.env`
- [ ] Developer token obtained
- [ ] OAuth refresh token generated
- [ ] Customer ID configured
- [ ] Test ad publishes successfully
- [ ] Ad appears in Google Ads

---

## 🎨 Demo Features

The demo script showcases:

### ✅ Auto-Generated Content
- Event details from database
- Images discovered from research
- Targeted ad copy (Spanish + English)
- Budget allocation by platform
- Targeting (age, location, interests, languages)

### ✅ Customization
- Edit headlines
- Swap images
- Adjust targeting
- Modify budgets

### ✅ Multi-Platform
- Meta Ads (Facebook/Instagram)
- Google Ads (Search)
- Email campaigns
- Organic social media

### ✅ Performance Tracking
- Impressions
- Clicks (CTR)
- Conversions
- Spend
- Revenue
- ROAS (Return on Ad Spend)

---

## 🔧 Customizing the Demo

### Change the Event

Edit `step_1_create_event()` in `test_complete_ad_flow.py`:

```python
event = Event(
    name="Your Event Name",
    description="Your event description",
    event_date=datetime(2026, 6, 15).date(),
    # ... other fields
)
```

### Change the Artist

Edit `step_2_run_research()`:

```python
research_report = {
    "artist_research": {
        "name": "Your Artist",
        "genre": "Your Genre",
        # ...
    }
}
```

### Adjust Budgets

Edit `step_3_generate_campaigns()` or modify values in `campaign_generator.py`:

```python
# Meta Awareness
budget = 100000  # $1,000 instead of $500

# Google Search
budget = 120000  # $1,200 instead of $600
```

---

## 📊 Expected Performance (Production)

Based on industry averages for event ticket sales:

### Meta Ads (Facebook/Instagram)
- **CTR**: 2-3%
- **Conversion Rate**: 5-8%
- **CPC**: $0.50-$1.50
- **ROAS**: 3:1 to 5:1

### Google Search Ads
- **CTR**: 3-5%
- **Conversion Rate**: 5-10%
- **CPC**: $1.00-$3.00
- **ROAS**: 4:1 to 6:1

### Email Campaigns
- **Open Rate**: 20-30%
- **Click Rate**: 5-10%
- **Conversion Rate**: 10-15%
- **Cost**: $0 (owned channel)

---

## 🐛 Troubleshooting

### Demo Script Errors

**Error**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Run from project root directory
```bash
cd /Users/edduran/Documents/GitHub/ai-tickets
python3 test_complete_ad_flow.py
```

**Error**: `No such table: venues`

**Solution**: Initialize database
```bash
alembic upgrade head
```

**Error**: `Foreign key constraint failed`

**Solution**: Create a venue first
```bash
python3 -c "from app.database import SessionLocal; from app.models import Venue; db = SessionLocal(); v = Venue(name='Test Venue', address='123 Main St'); db.add(v); db.commit()"
```

---

## 📚 Additional Resources

### Setup Guides
- `META_ADS_SETUP_GUIDE.md` - Meta Ads credentials
- `GOOGLE_ADS_SETUP_GUIDE.md` - Google Ads credentials
- `AD_EDITOR_CODE_SUMMARY.md` - Code documentation

### API References
- `META_ADS_API_REFERENCE.md` - Meta Ads API examples
- `ADS_INTEGRATION_SUMMARY.md` - Complete overview

### Code Files
- `app/services/meta_ads_integration.py` - Meta Ads API
- `app/services/google_ads_integration.py` - Google Ads API
- `app/services/campaign_generator.py` - Campaign generator
- `app/routers/ad_campaigns.py` - API endpoints

---

## 🎯 Next Steps

1. **Run the demo**
   ```bash
   python3 test_complete_ad_flow.py
   ```

2. **Review the output**
   - See how campaigns are generated
   - Understand the customization flow
   - Check performance metrics

3. **Set up real credentials**
   - Follow `META_ADS_SETUP_GUIDE.md`
   - Follow `GOOGLE_ADS_SETUP_GUIDE.md`

4. **Test real publishing**
   ```bash
   python3 test_meta_ads.py
   python3 test_google_ads.py
   ```

5. **Start using in production**
   - Create events via admin UI
   - Generate campaigns
   - Customize ads
   - Publish to Meta/Google
   - Track performance

---

**Happy Testing!** 🚀
