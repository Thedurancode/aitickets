# Event Media Management System

**Complete guide to managing event media assets and auto-generating flyers**

## Overview

The Event Media Management System allows you to:
1. **Upload/manage multiple media assets** per event (artists, logos, sponsors, venue photos)
2. **Categorize media** by type (artist_photo, logo, venue_photo, sponsor_logo, etc.)
3. **Auto-generate professional flyers** using all collected media assets
4. **Store media metadata** (labels, display order, custom metadata)

## Architecture

### Database Model

**EventMedia Table:**
- `id`: Primary key
- `event_id`: Foreign key to events
- `media_type`: ENUM (artist_photo, logo, venue_photo, sponsor_logo, background, graphic, other)
- `media_url`: URL to the media asset
- `label`: Optional label (e.g., "Main Artist", "Sponsor: Coca-Cola")
- `display_order`: Integer order for prioritization
- `media_metadata`: JSON metadata (dimensions, credits, etc.)
- `created_at`, `updated_at`: Timestamps

### Media Types

| Type | Description | Usage in Flyer |
|------|-------------|----------------|
| `artist_photo` | Artist/performer headshot | Prominently featured in flyer |
| `logo` | Event/brand logo | Top or bottom placement |
| `venue_photo` | Venue interior/exterior | Background or context |
| `sponsor_logo` | Sponsor logo | Bottom placement with other sponsors |
| `background` | Background image/texture | Flyer background |
| `graphic` | Generic graphic element | Decorative elements |
| `other` | Other media type | Additional context for AI |

## API Endpoints (8 total)

### 1. Add Media to Event
```http
POST /api/event-media/events/{event_id}/media
```

**Request:**
```json
{
  "media_type": "artist_photo",
  "media_url": "https://example.com/artist1.jpg",
  "label": "Main Artist",
  "display_order": 0,
  "metadata": {
    "dimensions": "1200x1600",
    "credit": "Photo by John Doe"
  }
}
```

**Response:**
```json
{
  "success": true,
  "media": {
    "id": 1,
    "event_id": 123,
    "media_type": "artist_photo",
    "media_url": "https://example.com/artist1.jpg",
    "label": "Main Artist",
    "display_order": 0,
    "metadata": {
      "dimensions": "1200x1600",
      "credit": "Photo by John Doe"
    },
    "created_at": "2026-03-26T10:00:00Z"
  },
  "message": "Added artist_photo to event"
}
```

### 2. Upload Media File
```http
POST /api/event-media/events/{event_id}/media/upload
Content-Type: multipart/form-data
```

**Form Fields:**
- `media_type`: Type of media (artist_photo, logo, etc.)
- `label`: Optional label
- `file`: The file to upload

**Response:**
```json
{
  "success": true,
  "uploaded_file": "event_123_media_a1b2c3d4.jpg",
  "media_url": "http://localhost:8000/uploads/event_123_media_a1b2c3d4.jpg",
  "media": {
    "id": 2,
    "event_id": 123,
    "media_type": "artist_photo",
    "media_url": "http://localhost:8000/uploads/event_123_media_a1b2c3d4.jpg",
    "label": "Supporting Artist"
  }
}
```

### 3. Get Event Media
```http
GET /api/event-media/events/{event_id}/media
GET /api/event-media/events/{event_id}/media?media_type=artist_photo
```

**Response:**
```json
{
  "event_id": 123,
  "event_name": "Concert Night",
  "total_media_count": 5,
  "media_by_type": {
    "artist_photo": [
      {
        "id": 1,
        "media_url": "https://example.com/artist1.jpg",
        "label": "Main Artist",
        "display_order": 0,
        "metadata": null,
        "created_at": "2026-03-26T10:00:00Z"
      },
      {
        "id": 2,
        "media_url": "https://example.com/artist2.jpg",
        "label": "Supporting Artist",
        "display_order": 1,
        "metadata": null,
        "created_at": "2026-03-26T10:05:00Z"
      }
    ],
    "logo": [
      {
        "id": 3,
        "media_url": "https://example.com/event-logo.png",
        "label": "Event Logo",
        "display_order": 0,
        "metadata": null,
        "created_at": "2026-03-26T10:10:00Z"
      }
    ],
    "sponsor_logo": [
      {
        "id": 4,
        "media_url": "https://example.com/sponsor1.png",
        "label": "Sponsor: Coca-Cola",
        "display_order": 0,
        "metadata": null,
        "created_at": "2026-03-26T10:15:00Z"
      },
      {
        "id": 5,
        "media_url": "https://example.com/sponsor2.png",
        "label": "Sponsor: RedBull",
        "display_order": 1,
        "metadata": null,
        "created_at": "2026-03-26T10:20:00Z"
      }
    ]
  },
  "all_media": [...]
}
```

### 4. Update Media
```http
PUT /api/event-media/media/{media_id}
```

**Request:**
```json
{
  "label": "Headlining Artist",
  "display_order": 0
}
```

### 5. Delete Media
```http
DELETE /api/event-media/media/{media_id}
```

### 6. Bulk Add Media
```http
POST /api/event-media/events/{event_id}/media/bulk
```

**Request:**
```json
{
  "media_items": [
    {
      "media_type": "artist_photo",
      "media_url": "https://example.com/artist1.jpg",
      "label": "Main Artist"
    },
    {
      "media_type": "artist_photo",
      "media_url": "https://example.com/artist2.jpg",
      "label": "Supporting Artist"
    },
    {
      "media_type": "logo",
      "media_url": "https://example.com/logo.png",
      "label": "Event Logo"
    },
    {
      "media_type": "sponsor_logo",
      "media_url": "https://example.com/sponsor1.png",
      "label": "Sponsor: Coca-Cola"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "created_count": 4,
  "error_count": 0,
  "created_media": [...]
}
```

### 7. 🎨 Auto-Generate Flyer from Media (THE MAGIC ENDPOINT!)
```http
POST /api/event-media/events/{event_id}/generate-flyer
```

**Request:**
```json
{
  "template_id": 5,
  "prompt_overrides": "Make the artist photos prominent, use vibrant colors, include all sponsor logos at the bottom",
  "include_types": ["artist_photo", "logo", "sponsor_logo"]
}
```

**Response:**
```json
{
  "success": true,
  "event_id": 123,
  "event_name": "Concert Night",
  "template_id": 5,
  "template_name": "Neon Nights",
  "image_url": "http://localhost:8000/uploads/event_123_flyer_xyz.png",
  "reference_images_used": 5,
  "artist_images_count": 2,
  "message": "Flyer generated successfully and saved to event",
  "media_used": {
    "artist_photos": 2,
    "other_images": 3,
    "total_media_assets": 5,
    "media_breakdown": {
      "artist_photo": 2,
      "logo": 1,
      "sponsor_logo": 2,
      "venue_photo": 0,
      "background": 0,
      "graphic": 0,
      "other": 0
    }
  }
}
```

### 8. List Media Types
```http
GET /api/event-media/media-types
```

## Complete Workflow Example

### Step 1: Create an Event
```bash
curl -X POST "http://localhost:8000/api/events" \
  -H "Content-Type: application/json" \
  -H "x-admin-key: your_key" \
  -d '{
    "venue_id": 1,
    "name": "Summer Music Festival 2026",
    "description": "Three amazing artists, one unforgettable night",
    "event_date": "2026-07-15",
    "event_time": "19:00"
  }'
```

### Step 2: Add Media Assets

**Option A: Upload Files**
```bash
# Artist 1
curl -X POST "http://localhost:8000/api/event-media/events/123/media/upload" \
  -H "x-admin-key: your_key" \
  -F "media_type=artist_photo" \
  -F "label=Main Artist - DJ Shadow" \
  -F "file=@artist1.jpg"

# Artist 2
curl -X POST "http://localhost:8000/api/event-media/events/123/media/upload" \
  -H "x-admin-key: your_key" \
  -F "media_type=artist_photo" \
  -F "label=Supporting - The Glitch Mob" \
  -F "file=@artist2.jpg"

# Event Logo
curl -X POST "http://localhost:8000/api/event-media/events/123/media/upload" \
  -H "x-admin-key: your_key" \
  -F "media_type=logo" \
  -F "label=Festival Logo" \
  -F "file=@event-logo.png"
```

**Option B: Bulk Add URLs**
```bash
curl -X POST "http://localhost:8000/api/event-media/events/123/media/bulk" \
  -H "Content-Type: application/json" \
  -H "x-admin-key: your_key" \
  -d '{
    "media_items": [
      {
        "media_type": "artist_photo",
        "media_url": "https://example.com/dj-shadow.jpg",
        "label": "Main Artist - DJ Shadow"
      },
      {
        "media_type": "artist_photo",
        "media_url": "https://example.com/glitch-mob.jpg",
        "label": "Supporting - The Glitch Mob"
      },
      {
        "media_type": "logo",
        "media_url": "https://example.com/festival-logo.png",
        "label": "Festival Logo"
      },
      {
        "media_type": "venue_photo",
        "media_url": "https://example.com/outdoor-venue.jpg",
        "label": "Main Stage"
      },
      {
        "media_type": "sponsor_logo",
        "media_url": "https://example.com/redbull-logo.png",
        "label": "Sponsor: RedBull"
      },
      {
        "media_type": "sponsor_logo",
        "media_url": "https://example.com/spotify-logo.png",
        "label": "Sponsor: Spotify"
      }
    ]
  }'
```

### Step 3: Review Media
```bash
curl "http://localhost:8000/api/event-media/events/123/media" \
  -H "x-admin-key: your_key"
```

### Step 4: Generate Flyer 🎨
```bash
curl -X POST "http://localhost:8000/api/event-media/events/123/generate-flyer" \
  -H "Content-Type: application/json" \
  -H "x-admin-key: your_key" \
  -d '{
    "template_id": 1,
    "prompt_overrides": "Make this festival poster vibrant and energetic. Feature both artists prominently. Include the venue atmosphere. Place sponsor logos tastefully at the bottom."
  }'
```

**Response:**
```json
{
  "success": true,
  "event_id": 123,
  "event_name": "Summer Music Festival 2026",
  "template_id": 1,
  "template_name": "Neon Nights",
  "image_url": "http://localhost:8000/uploads/event_123_flyer_a1b2c3d4.png",
  "reference_images_used": 6,
  "artist_images_count": 2,
  "message": "Flyer generated successfully and saved to event",
  "media_used": {
    "artist_photos": 2,
    "other_images": 4,
    "total_media_assets": 6,
    "media_breakdown": {
      "artist_photo": 2,
      "logo": 1,
      "venue_photo": 1,
      "sponsor_logo": 2,
      "background": 0,
      "graphic": 0,
      "other": 0
    }
  }
}
```

### Step 5: Event Now Has Professional Flyer!
The event's `image_url` is automatically updated with the generated flyer. It now shows up in:
- Event listings
- Event detail pages
- Social media posts (via Postiz)
- Meta Ads campaigns
- Email notifications
- QR code tickets
- Wallet passes

## How the AI Flyer Generation Works

1. **Media Collection**: System fetches all media assets attached to the event
2. **Categorization**:
   - `artist_photo` → Goes to prominent positions in flyer
   - `venue_photo`, `logo`, `sponsor_logo`, `background`, `graphic` → Goes to supporting positions
3. **Template Analysis**: AI analyzes the selected template for style/layout reference
4. **Prompt Construction**: Builds comprehensive prompt including:
   - Event information (name, date, time, venue)
   - Template style instructions
   - Media asset descriptions with labels
   - Your custom prompt overrides
5. **Image Generation**: Sends all reference images + prompt to NanoBanana AI (Flux Pro 1.1)
6. **Save & Update**: Downloads generated flyer, saves to uploads/, updates event.image_url

## Advanced Features

### Display Order
Control which media is prioritized:
```json
{
  "media_type": "artist_photo",
  "media_url": "https://example.com/headliner.jpg",
  "label": "Headliner",
  "display_order": 0  // Highest priority
}
```

### Selective Media Inclusion
Generate flyer with specific media types only:
```json
{
  "template_id": 5,
  "include_types": ["artist_photo", "logo"],
  "prompt_overrides": "Focus on the artists, minimal design"
}
```

### Media Metadata
Store additional information:
```json
{
  "media_type": "artist_photo",
  "media_url": "https://example.com/artist.jpg",
  "label": "DJ Shadow",
  "metadata": {
    "dimensions": "1600x2400",
    "photographer": "Jane Smith",
    "license": "CC BY-NC",
    "instagram": "@djshadow_official"
  }
}
```

## Use Cases

### 1. Multi-Artist Concert
```
Media Assets:
- 3x artist_photo (headliner + 2 supporting)
- 1x logo (event brand)
- 1x venue_photo (concert hall)
- 2x sponsor_logo (sponsors)

Result: Professional concert poster with all artists featured, sponsor recognition
```

### 2. Festival with Multiple Stages
```
Media Assets:
- 10x artist_photo (lineup)
- 1x logo (festival logo)
- 3x venue_photo (different stages)
- 5x sponsor_logo (major sponsors)
- 2x background (festival atmosphere)

Result: Comprehensive festival poster with full lineup and sponsors
```

### 3. Corporate Event
```
Media Assets:
- 1x logo (company logo)
- 2x background (corporate branding)
- 3x sponsor_logo (partners)
- 1x venue_photo (conference center)

Result: Professional corporate event flyer with branding
```

### 4. Comedy Show
```
Media Assets:
- 2x artist_photo (comedians)
- 1x logo (comedy club logo)
- 1x venue_photo (club interior)

Result: Fun, engaging comedy show poster
```

## Best Practices

### Image Quality
- **Resolution**: 1200px minimum on shortest side
- **Formats**: JPG, PNG, WebP
- **Aspect Ratios**:
  - Artist photos: Portrait (2:3 or 3:4)
  - Logos: Square or landscape with transparency (PNG)
  - Venue photos: Landscape (16:9 or 4:3)

### Labeling
Always provide descriptive labels:
- ✅ Good: "Main Artist - Daft Punk"
- ✅ Good: "Sponsor: Coca-Cola"
- ❌ Bad: "image1"
- ❌ Bad: null

### Display Order
Use display_order to prioritize:
- 0 = Highest priority (headliner, main logo)
- 1+ = Supporting elements

### Prompt Overrides
Be specific in your instructions:
- ✅ Good: "Feature both artists equally, vibrant neon colors, venue in background, sponsor logos subtle at bottom"
- ❌ Bad: "make it cool"

## Integration with Existing Features

### Works With
- ✅ **Flyer Templates**: Uses template as style reference
- ✅ **Enhanced Flyer Generation**: Powered by same AI engine
- ✅ **Event Image Update**: Can update via magic link SMS
- ✅ **Social Media Publishing**: Generated flyer auto-posted via Postiz
- ✅ **Meta Ads**: Generated flyer used in ad creative
- ✅ **Email Notifications**: Flyer included in emails
- ✅ **Multi-Platform Publishing**: Flyer distributed to all platforms

### Differences from Enhanced Flyer Generation

| Feature | Event Media System | Enhanced Flyer |
|---------|-------------------|----------------|
| Media Storage | ✅ Persistent in database | ❌ Temporary, passed in request |
| Reusability | ✅ Reuse same media for regeneration | ❌ Must pass images again |
| Organization | ✅ Categorized by type | ❌ Just URLs |
| Bulk Upload | ✅ Yes | ❌ No |
| Metadata | ✅ Labels, order, custom metadata | ❌ No |
| Best For | Multiple iterations, professional workflow | Quick one-off generation |

## Troubleshooting

### "No media assets found for this event"
- Add media first using POST /events/{id}/media or /media/upload
- Check that media was successfully created with GET /events/{id}/media

### "Event not found"
- Verify event_id is correct
- Ensure event exists in database

### "Invalid media_type"
- Use one of: artist_photo, logo, venue_photo, sponsor_logo, background, graphic, other
- Check spelling and lowercase

### Generated flyer doesn't include all media
- Check media was actually added (GET /events/{id}/media)
- Verify media_type is correct
- Try specifying include_types explicitly
- Check display_order (higher order might be deprioritized)

### Flyer quality is poor
- Use higher resolution source images (1200px minimum)
- Provide descriptive labels for better AI understanding
- Use detailed prompt_overrides
- Try different templates

## Database Schema

```sql
CREATE TABLE event_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    media_type VARCHAR(50) NOT NULL,
    media_url VARCHAR(500) NOT NULL,
    label VARCHAR(255),
    display_order INTEGER DEFAULT 0,
    media_metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
);

CREATE INDEX ix_event_media_event_id ON event_media (event_id);
CREATE INDEX ix_event_media_media_type ON event_media (media_type);
```

## API Reference Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/events/{id}/media` | POST | Add single media asset |
| `/events/{id}/media/upload` | POST | Upload and add media file |
| `/events/{id}/media` | GET | Get all event media |
| `/media/{id}` | PUT | Update media asset |
| `/media/{id}` | DELETE | Delete media asset |
| `/events/{id}/media/bulk` | POST | Bulk add media assets |
| `/events/{id}/generate-flyer` | POST | 🎨 Auto-generate flyer from media |
| `/media-types` | GET | List available media types |

## Next Steps

1. ✅ System is ready to use!
2. 📸 Start uploading media assets for your events
3. 🎨 Generate professional flyers with one API call
4. 🚀 Distribute flyers via social media and ads
5. 🔄 Iterate and refine your flyer designs

For support or questions, refer to the main API documentation or test with the example scripts.
