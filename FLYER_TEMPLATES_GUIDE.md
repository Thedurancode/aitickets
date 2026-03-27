# Flyer Templates Guide

Complete guide for managing flyer templates in the AI Tickets platform.

## Overview

The flyer templates system allows you to:
- **Store reusable design templates** with AI-analyzed styles
- **Generate event flyers** that match template aesthetics
- **Send SMS magic links** for template selection
- **Track template usage** and popularity

## Database Status

✅ **Database is connected and ready!**

```bash
# Check templates in database
sqlite3 tickets.db "SELECT id, name, times_used FROM flyer_templates;"

# Current count: 12 templates installed
```

---

## Quick Start

### 1. View Existing Templates

**Via Database:**
```bash
sqlite3 tickets.db "SELECT * FROM flyer_templates;"
```

**Via API:**
```bash
curl http://localhost:8000/api/flyer-templates/
```

**Via Browser:**
```
http://localhost:8000/api/flyer-templates/
```

---

### 2. Add Templates (3 Methods)

#### Method A: Bulk Import Script (Fastest)

```bash
# Edit bulk_add_templates.py and add your templates to the TEMPLATES list
python bulk_add_templates.py
```

#### Method B: Interactive CLI

```bash
# Interactive prompts for each field
python add_custom_template.py

# Add example templates
python add_custom_template.py --example
```

#### Method C: Direct API Call

```bash
curl -X POST http://localhost:8000/api/flyer-templates/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cyberpunk Future",
    "description": "Futuristic design with neon accents and tech elements",
    "image_url": "https://example.com/template.png",
    "thumbnail_url": "https://example.com/thumb.png",
    "prompt_instructions": "Cyberpunk aesthetic with neon blue and purple. Futuristic fonts. Tech grid backgrounds."
  }'
```

#### Method D: Direct Database Insert

```bash
sqlite3 tickets.db <<EOF
INSERT INTO flyer_templates (name, description, image_url, thumbnail_url, prompt_instructions, created_by, times_used, created_at, updated_at)
VALUES (
  'Custom Template',
  'My custom flyer template',
  'https://example.com/template.png',
  'https://example.com/thumb.png',
  'AI generation instructions here',
  'Admin',
  0,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);
EOF
```

---

## Template Schema

### Required Fields
- `name` (string, 255 chars) - Unique template name
- `description` (text) - What the template is for
- `image_url` (string, 500 chars) - Full-size template image URL

### Optional Fields
- `thumbnail_url` (string, 500 chars) - Smaller preview image
- `prompt_instructions` (text) - AI generation guidance
- `created_by` (string, 255 chars) - Creator name/org

### Auto-Generated Fields
- `id` - Auto-increment primary key
- `times_used` - Usage counter (starts at 0)
- `last_used_at` - Timestamp of last use
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

---

## Using Templates

### Generate Flyer for Event

```bash
# Method 1: Direct API call
curl -X POST http://localhost:8000/api/flyer-templates/events/123/generate/5

# Method 2: Magic link flow (via SMS)
curl -X POST http://localhost:8000/api/flyer-templates/magic-link \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 123,
    "phone": "+14155551234",
    "expires_hours": 24
  }'
# → Sends SMS with template selection link
```

### Magic Link Workflow

1. **Send magic link** to promoter's phone
2. Promoter clicks link → opens mobile-friendly template gallery
3. Sees current event image + all available templates
4. Selects template → AI generates new flyer
5. Event image auto-updates with generated flyer

---

## Template Management

### Update Template

```bash
curl -X PUT http://localhost:8000/api/flyer-templates/5 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "description": "New description",
    "prompt_instructions": "Updated AI instructions"
  }'
```

### Delete Template

```bash
curl -X DELETE http://localhost:8000/api/flyer-templates/5
```

### Get Featured Templates (Most Used)

```bash
curl http://localhost:8000/api/flyer-templates/featured?limit=6
```

---

## Pre-Installed Templates (12)

The system comes with 12 curated templates:

1. **Neon Nights** - Electronic music, nightclubs
2. **Vintage Jazz** - Jazz nights, sophisticated events
3. **Summer Festival** - Outdoor festivals, daytime events
4. **Minimal Modern** - Corporate, galleries, upscale
5. **Rock Concert** - Rock shows, high-energy events
6. **Hip Hop Block Party** - Hip hop, street festivals
7. **Sports Championship** - Sports events, tournaments
8. **Comedy Night** - Comedy shows, open mics
9. **Elegant Gala** - Galas, fundraisers, formal events
10. **Food & Wine** - Food festivals, wine tastings
11. **Halloween Horror** - Halloween parties, horror themes
12. **Holiday Celebration** - Christmas, New Year's, holidays

All templates use Unsplash images and include detailed AI prompt instructions.

---

## Adding Your Own Templates

### Best Practices

**Image URLs:**
- Use **high-quality images** (at least 800x800px)
- Recommended: 1200x1600px for full-size, 400x533px for thumbnails
- Supported hosts: Unsplash, Imgur, Cloudinary, S3, your own CDN
- Ensure images are **publicly accessible**

**Prompt Instructions:**
- Describe **colors** (e.g., "vibrant neon pink and blue")
- Specify **typography** (e.g., "bold sans-serif fonts")
- Include **visual elements** (e.g., "geometric shapes, gradients")
- Mention **mood** (e.g., "energetic and modern")

**Template Names:**
- Use clear, descriptive names
- Avoid special characters
- Keep under 50 characters for best UI display

### Example Template Data

```python
{
    "name": "Cyberpunk Night",
    "description": "Futuristic cyberpunk aesthetic with neon accents. Perfect for electronic music events and tech conferences.",
    "image_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1200",
    "thumbnail_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=400",
    "prompt_instructions": "Cyberpunk aesthetic with neon blue, purple, and pink. Futuristic fonts with glitch effects. Dark backgrounds with tech grid patterns. Include holographic or circuit board elements.",
    "created_by": "Your Organization"
}
```

---

## API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/flyer-templates/` | List all templates (paginated, sortable) |
| `GET` | `/api/flyer-templates/featured` | Get most-used templates |
| `GET` | `/api/flyer-templates/{id}` | Get specific template |
| `POST` | `/api/flyer-templates/` | Create new template |
| `PUT` | `/api/flyer-templates/{id}` | Update template |
| `DELETE` | `/api/flyer-templates/{id}` | Delete template |
| `POST` | `/api/flyer-templates/magic-link` | Send SMS magic link |
| `GET` | `/api/flyer-templates/select/{token}` | Get templates for magic link |
| `POST` | `/api/flyer-templates/generate` | Generate flyer from template |
| `POST` | `/api/flyer-templates/events/{eventId}/generate/{templateId}` | Quick generate |
| `POST` | `/api/flyer-templates/select/{token}/generate/{templateId}` | Generate via magic link |

**Public Pages:**
- `GET /flyer-templates/select/{token}` - Mobile template picker UI

---

## Voice Agent Integration

Templates are fully integrated with the MCP voice agent. You can:

```
User: "Send me a link to pick a flyer template for the Jazz Night event"
Agent: "I've sent an SMS to your phone with a link to choose from 12 templates"

User: "Which templates are most popular?"
Agent: "The top templates are Neon Nights (used 47 times) and Vintage Jazz (used 32 times)"

User: "Generate a flyer using the Minimal Modern template for event 5"
Agent: "Generated! The event now has a clean, modern flyer matching that style"
```

---

## Troubleshooting

### "Table doesn't exist"

Run the migration:
```bash
source .venv/bin/activate
python app/migrations/add_flyer_templates.py
python app/migrations/add_flyer_template_tokens.py
```

### "Template already exists"

Check existing templates:
```bash
sqlite3 tickets.db "SELECT id, name FROM flyer_templates WHERE name LIKE '%keyword%';"
```

Update or delete the existing one first.

### "Image URL not loading"

- Verify URL is publicly accessible
- Check for HTTPS (some browsers block HTTP images)
- Try opening the URL directly in a browser
- Consider using Unsplash or Imgur for reliable hosting

---

## Next Steps

1. ✅ **Database is ready** - flyer_templates table exists
2. ✅ **12 templates installed** - curated starter collection
3. ⏭️  **Add your custom templates** - Use scripts above
4. 🎨 **Start generating flyers** - Use API or voice agent
5. 📊 **Track usage** - See which templates are most popular

---

## Files Created

- `bulk_add_templates.py` - Bulk import script
- `add_custom_template.py` - Interactive/direct template addition
- `test_templates_api.py` - API testing script
- `FLYER_TEMPLATES_GUIDE.md` - This guide

---

**Questions?** Check the API docs at `http://localhost:8000/docs` or search for "flyer_templates" in the codebase.
