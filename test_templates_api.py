"""Quick test to verify the flyer templates API is working."""
import requests

BASE_URL = "http://localhost:8000"

def test_list_templates():
    """Test listing all templates."""
    response = requests.get(f"{BASE_URL}/api/flyer-templates/")

    if response.status_code == 200:
        templates = response.json()
        print(f"✅ Found {len(templates)} templates:\n")
        for t in templates[:5]:  # Show first 5
            print(f"   {t['id']:2d}. {t['name']}")
            print(f"       {t['description'][:70]}...")
            print(f"       Used {t['times_used']} times\n")
        return True
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return False

def test_get_featured():
    """Test getting featured templates."""
    response = requests.get(f"{BASE_URL}/api/flyer-templates/featured?limit=3")

    if response.status_code == 200:
        templates = response.json()
        print(f"✅ Featured templates: {len(templates)}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_get_single_template():
    """Test getting a specific template."""
    response = requests.get(f"{BASE_URL}/api/flyer-templates/1")

    if response.status_code == 200:
        template = response.json()
        print(f"✅ Retrieved template: {template['name']}")
        print(f"   Description: {template['description']}")
        print(f"   Image URL: {template['image_url']}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Flyer Templates API...\n")
    print("=" * 70)

    print("\n1️⃣  List All Templates")
    print("-" * 70)
    test_list_templates()

    print("\n2️⃣  Get Featured Templates")
    print("-" * 70)
    test_get_featured()

    print("\n3️⃣  Get Single Template")
    print("-" * 70)
    test_get_single_template()

    print("\n" + "=" * 70)
    print("✨ API Tests Complete!")
    print("\n💡 Next steps:")
    print("   - Start the server: make api")
    print("   - View templates: http://localhost:8000/api/flyer-templates/")
    print("   - Generate flyer: POST /api/flyer-templates/events/{id}/generate/{templateId}")
