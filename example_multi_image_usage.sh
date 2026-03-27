#!/bin/bash
# Example usage scripts for multi-image flyer generation

BASE_URL="http://localhost:8000"

echo "🎨 Multi-Image Flyer Generation Examples"
echo "========================================"
echo ""

# Example 1: Hip Hop Concert with 2 Artists
echo "1️⃣  Hip Hop Concert - 2 Artists Side-by-Side"
echo "--------------------------------------------"
curl -X POST "$BASE_URL/api/flyer-templates-enhanced/events/1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 6,
    "artist_images": [
      "https://images.unsplash.com/photo-1571609166008-e6c0e5e4db49?w=800",
      "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800"
    ],
    "prompt_overrides": "Urban street style. Place both artists side-by-side with bold graffiti-style typography."
  }'
echo -e "\n\n"

# Example 2: Jazz Night with Venue Atmosphere
echo "2️⃣  Jazz Night - Artist + Venue Atmosphere"
echo "--------------------------------------------"
curl -X POST "$BASE_URL/api/flyer-templates-enhanced/events/2/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 2,
    "artist_images": [
      "https://images.unsplash.com/photo-1415201364774-f6f0bb35f28f?w=800"
    ],
    "additional_images": [
      "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800"
    ],
    "prompt_overrides": "Blend the intimate jazz club atmosphere from venue photo with elegant art deco styling."
  }'
echo -e "\n\n"

# Example 3: Set artist images on event, then auto-generate
echo "3️⃣  Electronic Festival - Auto-Detect Mode"
echo "--------------------------------------------"
echo "Step 1: Add artist images to event..."
curl -X PUT "$BASE_URL/api/flyer-templates-enhanced/events/3/images" \
  -H "Content-Type: application/json" \
  -d '{
    "artist_image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800",
    "additional_images": [
      "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=800"
    ],
    "performer_names": ["DJ Headliner", "Live Band"]
  }'
echo -e "\n"

echo "Step 2: Auto-generate flyer..."
curl -X POST "$BASE_URL/api/flyer-templates-enhanced/events/3/generate-auto?template_id=1&prompt_overrides=Futuristic+neon+aesthetic+with+prominent+DJ+photo"
echo -e "\n\n"

# Example 4: Get all images for an event
echo "4️⃣  Retrieve All Event Images"
echo "--------------------------------------------"
curl -X GET "$BASE_URL/api/flyer-templates-enhanced/events/1/images"
echo -e "\n\n"

echo "✨ Examples complete!"
echo ""
echo "💡 Tips:"
echo "   - Replace event IDs (1, 2, 3) with your actual event IDs"
echo "   - Replace template IDs with templates that match your event style"
echo "   - Experiment with different prompt_overrides for different effects"
echo "   - Use high-quality images (at least 800x800px)"
