# Event Images Status Report

**Generated**: 2026-03-26

## Summary

Yes, events **can** have images, but most currently don't. Your platform supports multiple image types per event.

## Image Fields Available

Each event in the database has **6 image/media fields**:

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `image_url` | VARCHAR(500) | **Main event flyer/poster** | ❌ Optional |
| `artist_image_url` | VARCHAR(500) | Primary artist/performer photo | ❌ Optional |
| `additional_images` | TEXT (JSON) | Array of additional image URLs (venue, artists, etc.) | ❌ Optional |
| `performer_names` | TEXT (JSON) | Array of performer/artist names | ❌ Optional |
| `promo_video_url` | VARCHAR(500) | YouTube/promotional video URL | ❌ Optional |
| `post_event_video_url` | VARCHAR(500) | Post-event recap/highlight video | ❌ Optional |

## Current Database Statistics

**Total Events**: 22

### Main Event Images (`image_url`)
- ✅ **With images**: 2 events (9%)
- ❌ **Without images**: 20 events (91%)

### Artist Images (`artist_image_url`)
- ✅ **With artist images**: 0 events
- ❌ **Without artist images**: 22 events (100%)

### Additional Images (`additional_images`)
- All events currently have no additional images

## Events with Images

### Event #6: "Updated Notif Event"
- Date: 2025-12-01
- Image: `/uploads/event_6_139d7d2488724848bf61bb6362a2416c.jpg`
- Type: **Uploaded file** (stored in uploads directory)

### Event #1: "x"
- Date: 2026-03-15
- Image: `https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=1200&h=800&fit=crop`
- Type: **External URL** (Unsplash)

## How Images Work

### 1. Main Event Image (`image_url`)
The primary flyer/poster for the event. Can be:
- **Uploaded file**: Stored in `/uploads/` directory
- **External URL**: Any publicly accessible image URL
- **AI-generated**: Created via flyer templates system

**Used for:**
- Event listing cards
- Event detail pages
- Social media posts (via Postiz)
- Meta Ads campaigns
- Email notifications
- SMS/text messages

### 2. Artist Images (New Feature)
The enhanced flyer generation system can use multiple artist/venue images:

```python
# Update artist images via API
PUT /api/flyer-templates-enhanced/events/{event_id}/images
{
  "artist_image_url": "https://example.com/main-artist.jpg",
  "additional_images": [
    "https://example.com/artist2.jpg",
    "https://example.com/venue.jpg"
  ],
  "performer_names": ["Main Artist", "Supporting Act"]
}
```

### 3. AI Flyer Generation with Multi-Image Context
Generate flyers using template + artist photos + venue images:

```python
POST /api/flyer-templates-enhanced/events/{event_id}/generate
{
  "template_id": 5,
  "artist_images": ["https://example.com/artist1.jpg"],
  "additional_images": ["https://example.com/venue.jpg"],
  "prompt_overrides": "Make artist photos prominent, vibrant colors"
}
```

The AI will:
1. Analyze the template for style/layout
2. Incorporate artist images into the design
3. Use venue/context images for atmosphere
4. Generate a cohesive flyer that becomes the event's main `image_url`

## Image Upload Methods

### Method 1: Direct Upload via API
```bash
# Upload directly when creating/updating event
POST /api/events
{
  "name": "Concert Night",
  "image_url": "https://example.com/flyer.jpg",
  ...
}
```

### Method 2: Magic Link Upload (Token-Based)
Promoters can upload images via SMS magic link without logging in:

```python
# 1. Generate token and send SMS
POST /api/event-image-update/generate-token
{
  "event_id": 123,
  "phone": "+1234567890",
  "expires_hours": 24
}

# 2. Promoter receives SMS with link
# 3. Opens link: /update-event-image/{token}
# 4. Uploads new image via web form
# 5. Event image_url automatically updated
```

### Method 3: AI Flyer Generation
```python
# Using template only
POST /api/flyer-templates/events/{event_id}/generate
{
  "template_id": 5
}

# Using template + multiple reference images
POST /api/flyer-templates-enhanced/events/{event_id}/generate
{
  "template_id": 5,
  "artist_images": ["url1", "url2"],
  "additional_images": ["url3"]
}
```

### Method 4: File Upload Form
```python
POST /api/event-image-update/upload
Content-Type: multipart/form-data

token: {magic_link_token}
file: {uploaded_file}
```

## Related Features

### Event Photos System
Beyond the main event image, there's a separate system for user-uploaded event photos:

- **EventPhoto** model (app/models.py:139)
- Users/attendees can upload photos during/after event
- Content moderation with NSFW detection
- Moderation statuses: pending, approved, rejected, flagged
- Each photo linked to specific event and optionally to event_goer

### Image Usage in Features

**Where event images appear:**
1. **Public event listing** - `/events` page
2. **Event detail page** - `/events/{id}`
3. **Ticket checkout** - Stripe checkout session
4. **Email notifications** - Purchase confirmations, reminders
5. **SMS messages** - Event updates (image URL included)
6. **Social media posts** - Postiz multi-platform posting
7. **Meta Ads** - Facebook/Instagram ad creatives
8. **Wallet passes** - Apple Wallet / Google Wallet thumbnails
9. **QR code tickets** - Embedded in ticket emails
10. **Webhooks** - Sent to external systems

## Recommendations

### For Better Event Discoverability

Since only 9% of events currently have images, consider:

1. **Auto-generate flyers for imageless events**
   - Run bulk flyer generation for events without `image_url`
   - Use default templates based on event category
   - Add to event creation workflow

2. **Make images required in event creation**
   - Update validation to require `image_url`
   - Or auto-generate placeholder if not provided

3. **Bulk import from existing sources**
   - If you have event images elsewhere, bulk import them
   - Use CSV upload with image URLs

4. **Prompt promoters for images**
   - Send SMS magic link when event created without image
   - Reminder notifications for events missing images

### Example: Bulk Generate Flyers for Imageless Events

```python
# Script to auto-generate flyers for events without images
from app.database import SessionLocal
from app.models import Event
from app.services.flyer_template import generate_flyer

db = SessionLocal()

# Get events without images
events_no_images = db.query(Event).filter(Event.image_url == None).all()

print(f"Found {len(events_no_images)} events without images")

# Generate flyers using default template
for event in events_no_images:
    result = generate_flyer(
        db=db,
        event_id=event.id,
        template_id=1  # Use first template as default
    )
    if result.get('success'):
        print(f"✅ Generated flyer for Event #{event.id}: {event.name}")
    else:
        print(f"❌ Failed for Event #{event.id}: {result.get('error')}")

db.commit()
db.close()
```

## API Endpoints for Image Management

### Main Event Image
- `POST /api/events` - Create event with image
- `PUT /api/events/{id}` - Update event image
- `POST /api/event-image-update/generate-token` - Send SMS magic link
- `POST /api/event-image-update/upload` - Upload via magic link
- `GET /update-event-image/{token}` - Public upload page

### Artist Images
- `PUT /api/flyer-templates-enhanced/events/{id}/images` - Update artist images
- `GET /api/flyer-templates-enhanced/events/{id}/images` - Get all images

### AI Flyer Generation
- `POST /api/flyer-templates/events/{id}/generate` - Basic template generation
- `POST /api/flyer-templates-enhanced/events/{id}/generate` - Multi-image generation
- `POST /api/flyer-templates-enhanced/events/{id}/generate-auto` - Auto-detect artist images

## Summary

**Answer**: Yes, each event **can** have an image (multiple types actually), but it's **optional**. Currently:
- 2 out of 22 events (9%) have main event images
- 0 events have artist images
- All image fields are optional, not required

**Best Practice**: Events should have at least a main `image_url` for better presentation in listings, social media, and marketing. Use the AI flyer generation system if you don't have pre-made images.
