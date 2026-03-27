# Multi-Image Flyer Generation Guide

Generate event flyers using **template style + artist photos + venue images** for richer, more contextual designs.

## Overview

The enhanced flyer generation system allows you to combine multiple visual inputs:

1. **Template Image** - Defines the layout, style, and design aesthetic
2. **Artist Images** - Photos of performers/artists to feature in the flyer
3. **Additional Images** - Venue photos, mood images, past event photos, etc.

The AI analyzes all images and creates a cohesive flyer that:
- Matches the template's style and layout
- Prominently features the artist/performer
- Incorporates contextual elements from additional images
- Maintains professional design standards

---

## Setup

### 1. Run Migration

Add artist image support to the events table:

```bash
source .venv/bin/activate
python app/migrations/add_artist_images.py
```

This adds three new columns to `events`:
- `artist_image_url` - Primary artist/performer image
- `additional_images` - JSON array of additional image URLs
- `performer_names` - JSON array of performer names

### 2. Add Enhanced Router

Edit `app/main.py` and add:

```python
from app.routers import flyer_templates_enhanced

# Add after other routers
app.include_router(flyer_templates_enhanced.router)
```

### 3. Restart Server

```bash
make api
# or
uvicorn app.main:app --reload
```

---

## Usage Methods

### Method 1: Manual Multi-Image Generation

**Best for:** Full control over all image inputs

```bash
curl -X POST http://localhost:8000/api/flyer-templates-enhanced/events/123/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 5,
    "artist_images": [
      "https://i.imgur.com/artist1.jpg",
      "https://i.imgur.com/artist2.jpg"
    ],
    "additional_images": [
      "https://i.imgur.com/venue.jpg"
    ],
    "prompt_overrides": "Make the artist photos prominent with a spotlight effect"
  }'
```

**Parameters:**
- `template_id` (required) - Which template to use for style
- `artist_images` (optional) - Array of artist/performer image URLs (up to 3)
- `additional_images` (optional) - Array of context image URLs (up to 2)
- `prompt_overrides` (optional) - Additional AI instructions

### Method 2: Auto-Detect from Event Fields

**Best for:** Simplified workflow when images are already stored on the event

First, add images to the event:

```bash
# Set artist images on event
curl -X PUT http://localhost:8000/api/flyer-templates-enhanced/events/123/images \
  -H "Content-Type: application/json" \
  -d '{
    "artist_image_url": "https://i.imgur.com/main-artist.jpg",
    "additional_images": [
      "https://i.imgur.com/supporting-artist.jpg",
      "https://i.imgur.com/venue-photo.jpg"
    ],
    "performer_names": ["Main Artist", "Supporting Act"]
  }'
```

Then generate flyer (auto-detects images):

```bash
curl -X POST "http://localhost:8000/api/flyer-templates-enhanced/events/123/generate-auto?template_id=5"
```

### Method 3: Direct Database Update

```bash
sqlite3 tickets.db <<EOF
UPDATE events
SET
  artist_image_url = 'https://example.com/artist.jpg',
  additional_images = '["https://example.com/img1.jpg", "https://example.com/img2.jpg"]',
  performer_names = '["Artist Name", "DJ Name"]'
WHERE id = 123;
EOF
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/flyer-templates-enhanced/events/{id}/generate` | Generate with explicit image URLs |
| `POST` | `/api/flyer-templates-enhanced/events/{id}/generate-auto` | Auto-detect images from event fields |
| `PUT` | `/api/flyer-templates-enhanced/events/{id}/images` | Update event artist images |
| `GET` | `/api/flyer-templates-enhanced/events/{id}/images` | Get all event images |

---

## Examples

### Example 1: Hip Hop Concert with 2 Artists

```bash
curl -X POST http://localhost:8000/api/flyer-templates-enhanced/events/45/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 6,
    "artist_images": [
      "https://images.unsplash.com/photo-1571609166008-e6c0e5e4db49",
      "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f"
    ],
    "prompt_overrides": "Urban street style. Put both artists side-by-side with bold typography overlay."
  }'
```

### Example 2: Jazz Night with Venue Atmosphere

```bash
curl -X POST http://localhost:8000/api/flyer-templates-enhanced/events/67/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 2,
    "artist_images": [
      "https://images.unsplash.com/photo-1415201364774-f6f0bb35f28f"
    ],
    "additional_images": [
      "https://images.unsplash.com/photo-1514525253161-7a46d19cd819"
    ],
    "prompt_overrides": "Incorporate the intimate jazz club atmosphere from the venue photo. Warm, moody lighting."
  }'
```

### Example 3: Electronic Music Festival

```bash
# First set the images on the event
curl -X PUT http://localhost:8000/api/flyer-templates-enhanced/events/89/images \
  -H "Content-Type: application/json" \
  -d '{
    "artist_image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745",
    "additional_images": [
      "https://images.unsplash.com/photo-1492684223066-81342ee5ff30",
      "https://images.unsplash.com/photo-1459749411175-04bf5292ceea"
    ],
    "performer_names": ["DJ Headliner", "Supporting DJ", "Live Band"]
  }'

# Then generate
curl -X POST "http://localhost:8000/api/flyer-templates-enhanced/events/89/generate-auto?template_id=1&prompt_overrides=Futuristic+neon+aesthetic"
```

---

## How It Works

### The AI Process

1. **Template Analysis**
   - AI examines the template image
   - Identifies layout structure, typography, color palette
   - Understands the design system

2. **Content Integration**
   - AI receives artist/performer photos
   - Analyzes facial features, composition, backgrounds
   - Plans how to integrate photos into template layout

3. **Context Enhancement**
   - Additional images provide atmosphere/mood
   - AI extracts relevant visual elements
   - Blends contextual elements with template style

4. **Generation**
   - Creates new flyer matching template style
   - Features artist photos prominently
   - Incorporates contextual elements
   - Replaces text with event details
   - Maintains design cohesion

### Image Limits

To maintain quality and processing speed:
- **Artist images:** Up to 3
- **Additional images:** Up to 2
- **Total reference images:** Up to 6 (template + 3 artists + 2 context)

---

## Best Practices

### Image Selection

**Artist Images:**
- ✅ High resolution (at least 800x800px)
- ✅ Good lighting and clear faces
- ✅ Clean backgrounds or studio shots
- ✅ Consistent style across multiple artists
- ❌ Avoid blurry, dark, or low-quality photos
- ❌ Don't use images with heavy text overlays

**Additional Images:**
- ✅ Venue interior/exterior shots
- ✅ Crowd atmosphere from past events
- ✅ Mood/aesthetic references
- ❌ Avoid images that clash with template style

### Prompt Instructions

Be specific about how to integrate images:

**Good examples:**
- "Make the artist photo the focal point with template colors as overlay"
- "Use the venue photo as a subtle background, keep artist in foreground"
- "Create a split-screen layout with both artists side-by-side"
- "Blend the artist photo with the neon colors from the template"

**Poor examples:**
- "Make it look cool" (too vague)
- "Use all the images" (no direction)

### Template Selection

Choose templates that complement your artist images:

- **Bold artist photos** → Minimal templates (gives photos room to shine)
- **Moody/atmospheric artists** → Dark, dramatic templates
- **Multiple artists** → Templates with multi-column layouts
- **Solo artist** → Templates with strong focal point

---

## Troubleshooting

### "No artist images provided"

Make sure you're passing `artist_images` array:
```json
{
  "template_id": 5,
  "artist_images": ["https://..."]  // ← Don't forget this
}
```

### "Image download failed"

- Verify URLs are publicly accessible
- Check for HTTPS (some APIs require it)
- Test URL in browser first
- Ensure images are < 10MB each

### "Generated flyer doesn't include artist"

Try adding explicit instructions:
```json
{
  "prompt_overrides": "The artist photo MUST be the main focal point. Use a large portrait orientation with the artist's face clearly visible."
}
```

### "Colors don't match template"

Some image generation models need stronger guidance:
```json
{
  "prompt_overrides": "STRICTLY follow the template's exact color palette: [list specific hex codes from template]"
}
```

---

## Voice Agent Integration

You can use this via voice commands:

```
User: "Generate a flyer for the Jazz Night event using template 2, and include the artist photo from imgur.com/artist.jpg"

Agent: "I'll generate a flyer for Jazz Night using the Vintage Jazz template and incorporate that artist photo..."
[Calls generate_flyer_with_context]

Agent: "Done! Your new flyer features the artist in an elegant art deco style. Check the event page."
```

---

## Schema Updates

### Events Table (New Columns)

```sql
-- Primary artist/performer image
artist_image_url VARCHAR(500)

-- JSON array of additional images
-- Example: '["url1.jpg", "url2.jpg", "url3.jpg"]'
additional_images TEXT

-- JSON array of performer names
-- Example: '["Main Act", "Supporting Act"]'
performer_names TEXT
```

---

## Advanced Usage

### Python Script Example

```python
from app.database import SessionLocal
from app.services.flyer_template_enhanced import generate_flyer_with_context

db = SessionLocal()

result = generate_flyer_with_context(
    db=db,
    event_id=123,
    template_id=5,
    artist_images=[
        "https://example.com/artist1.jpg",
        "https://example.com/artist2.jpg"
    ],
    additional_images=[
        "https://example.com/venue.jpg"
    ],
    prompt_overrides="Emphasize the artist photos with a spotlight effect"
)

print(result)
# {
#   "success": True,
#   "image_url": "https://...",
#   "reference_images_used": 4,
#   "artist_images_count": 2,
#   "message": "Flyer generated using 'Neon Nights' template + 4 reference images!"
# }
```

---

## Comparison

### Before (Single Reference)
```bash
# Only template for style
POST /api/flyer-templates/events/123/generate/5
```
Result: Generic flyer in template style, no artist photos

### After (Multi-Image Context)
```bash
# Template + artist photos + venue
POST /api/flyer-templates-enhanced/events/123/generate
{
  "template_id": 5,
  "artist_images": ["artist.jpg"],
  "additional_images": ["venue.jpg"]
}
```
Result: Rich, contextual flyer featuring the actual artist in template style

---

## Next Steps

1. ✅ Run migration (`add_artist_images.py`)
2. ✅ Add enhanced router to `main.py`
3. 🎨 Add artist images to your events
4. 🚀 Generate flyers with multi-image context
5. 📊 Compare results with single-image generation

---

**Questions?** Check the API docs at `http://localhost:8000/docs` or explore the code in `app/services/flyer_template_enhanced.py`.
