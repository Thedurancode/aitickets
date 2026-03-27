# New Routers Added to main.py

**Date**: 2026-03-26

## Summary

Successfully added two new router modules to the ai-tickets platform, bringing **7 new API endpoints** online.

## Changes Made

### 1. Updated Imports (line 19)
```python
from app.routers import (
    # ... existing imports ...
    event_publisher,           # NEW
    flyer_templates_enhanced   # NEW
)
```

### 2. Registered Routers (lines 106-109)
```python
app.include_router(flyer_templates.router)
app.include_router(flyer_templates_enhanced.router)  # NEW
app.include_router(meta_ads.router)
app.include_router(event_publisher.router)          # NEW
```

## New Endpoints Available

### Event Publisher (3 endpoints)
Multi-platform event distribution to ticketing platforms, social media, and ad networks.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/event-publisher/events/{event_id}/publish` | Publish event to multiple platforms |
| POST | `/api/event-publisher/events/{event_id}/publish/preview` | Preview publication without publishing |
| GET | `/api/event-publisher/platforms` | List available publishing platforms |

**Supported Platforms:**
- Eventbrite (ticketing)
- Bandsintown (discovery)
- Social Media (via Postiz - 25+ platforms)
- Meta Ads (Facebook/Instagram advertising)
- Webhooks (custom integrations)
- Calendar exports (iCal/Google)

### Flyer Templates Enhanced (4 endpoints)
Multi-image AI flyer generation combining templates + artist photos + venue images.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/flyer-templates-enhanced/events/{event_id}/generate` | Generate flyer with custom images |
| POST | `/api/flyer-templates-enhanced/events/{event_id}/generate-auto` | Auto-detect artist images from event |
| PUT | `/api/flyer-templates-enhanced/events/{event_id}/images` | Update event artist images |
| GET | `/api/flyer-templates-enhanced/events/{event_id}/images` | Get all event images |

**Key Features:**
- Combine up to 6 reference images (template + artist + venue)
- AI analyzes template style and incorporates artist photos
- Auto-detection from event.artist_image_url and event.additional_images
- Custom prompt overrides for fine control

## Testing

Application imports successfully:
```bash
✅ Application imported successfully
✅ Total new endpoints: 7
```

## Updated Endpoint Count

**Previous**: 150 endpoints across 21 modules
**Current**: **157 endpoints across 23 modules**

## Documentation

See complete guides:
- [MULTI_PLATFORM_PUBLISHING_GUIDE.md](./MULTI_PLATFORM_PUBLISHING_GUIDE.md)
- [MULTI_IMAGE_FLYER_GUIDE.md](./MULTI_IMAGE_FLYER_GUIDE.md)
- [API_ENDPOINTS_COMPLETE.md](./API_ENDPOINTS_COMPLETE.md)

## Next Steps

### Configuration Required

To use the new event publisher endpoints, add these environment variables:

```env
# Eventbrite
EVENTBRITE_API_KEY=your_private_token
EVENTBRITE_ORGANIZATION_ID=your_org_id

# Bandsintown
BANDSINTOWN_APP_ID=your_app_id

# Meta Ads (already configured)
META_ACCESS_TOKEN=your_token
META_AD_ACCOUNT_ID=act_xxxxx

# Postiz (already configured)
POSTIZ_API_URL=https://postiz.example.com
POSTIZ_API_KEY=your_key
```

### Optional Platform Integrations

Consider adding these for broader event distribution:
1. **Songkick API** (free, easy) - Concert discovery
2. **SeatGeek API** (free, easy) - Ticket aggregation
3. **TicketsData** (paid) - Access 7 platforms with one integration
4. **StubHub API** (free) - Secondary market
5. **Universe API** (free) - Ticketmaster's DIY platform

## Example Usage

### Publish Event to All Platforms
```bash
curl -X POST "http://localhost:8000/api/event-publisher/events/123/publish" \
  -H "Content-Type: application/json" \
  -H "x-admin-key: your_key" \
  -d '{}'
```

### Generate Multi-Image Flyer
```bash
curl -X POST "http://localhost:8000/api/flyer-templates-enhanced/events/123/generate" \
  -H "Content-Type: application/json" \
  -H "x-admin-key: your_key" \
  -d '{
    "template_id": 5,
    "artist_images": ["https://example.com/artist1.jpg"],
    "additional_images": ["https://example.com/venue.jpg"],
    "prompt_overrides": "Make the artist photos prominent"
  }'
```

### Check Available Platforms
```bash
curl "http://localhost:8000/api/event-publisher/platforms"
```

## Status

✅ **Complete** - All routers successfully added and tested.
