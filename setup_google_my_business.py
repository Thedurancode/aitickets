#!/usr/bin/env python3
"""
Google My Business Setup Guide & Helper

This script helps you set up Google My Business Events integration
for your AI Tickets platform.
"""

import sys
import os
import webbrowser
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')


def main():
    """Interactive setup for Google My Business"""

    print("\n" + "="*70)
    print("🌟 GOOGLE MY BUSINESS EVENTS SETUP")
    print("="*70)

    print("""
📍 What is Google My Business Events?

Google My Business Events lets you publish events that appear in:
• Google Search results (when people search for your business)
• Google Maps (on your business listing)
• Google Business Profile
• Local pack results (e.g., "restaurants near me")

For Peru Chicken in Hillsborough, NJ, this means your Mother's Day
brunch will show up when people search for:
- "Peru Chicken Hillsborough"
- "Brunch near me"
- "Mother's Day restaurants Somerset County"
- "Peruvian food New Jersey"
    """)

    print("\n" + "-"*70)
    print("📋 SETUP STEPS")
    print("-"*70)

    print("""
STEP 1: VERIFY YOUR BUSINESS ON GOOGLE
---------------------------------------
1. Go to: https://business.google.com/
2. Search for "Peru Chicken Hillsborough NJ"
3. Claim or verify your business listing
4. Complete verification (postcard, phone, or instant)

Status: Have you verified your business? (y/n)
    """)

    verified = input("Answer: ").lower().strip() == 'y'

    if not verified:
        print("""
⚠️  You must verify your business first!

Quick verification tips:
• Use instant verification if available
• Phone verification is fastest
• Postcard takes 5-14 days

Come back after verification is complete.
        """)
        return

    print("""
STEP 2: ENABLE GOOGLE BUSINESS PROFILE API
-------------------------------------------
1. Go to: https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Search for "Google My Business API"
4. Click "Enable API"
5. Also enable "Google Business Profile API" (newer version)
    """)

    input("\nPress Enter when you've enabled the APIs...")

    print("""
STEP 3: CREATE OAUTH 2.0 CREDENTIALS
-------------------------------------
1. In Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click "+ CREATE CREDENTIALS" > "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "AI Tickets GMB Integration"
5. Click "Create"
6. Download the JSON file
    """)

    input("\nPress Enter when you have the credentials JSON...")

    print("""
STEP 4: GET YOUR CREDENTIALS
-----------------------------
Open the downloaded JSON file and find:
    """)

    client_id = input("Enter Client ID: ").strip()
    client_secret = input("Enter Client Secret: ").strip()

    if not client_id or not client_secret:
        print("❌ Credentials required!")
        return

    print("""
STEP 5: AUTHORIZE & GET REFRESH TOKEN
--------------------------------------
We'll now open a browser to authorize access...
    """)

    # Build OAuth URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        "redirect_uri=urn:ietf:wg:oauth:2.0:oob&"
        "response_type=code&"
        "scope=https://www.googleapis.com/auth/business.manage"
    )

    print(f"\nOpening browser to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("""
In the browser:
1. Sign in with the Google account that manages your business
2. Grant all requested permissions
3. Copy the authorization code shown
    """)

    auth_code = input("\nPaste authorization code here: ").strip()

    if not auth_code:
        print("❌ Authorization code required!")
        return

    # Exchange code for tokens
    import requests

    print("\nExchanging code for tokens...")

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "authorization_code"
        }
    )

    if token_response.status_code == 200:
        tokens = token_response.json()
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")

        if not refresh_token:
            print("❌ No refresh token received. Try again with a new auth code.")
            return

        print("\n" + "="*70)
        print("✅ SUCCESS! Google My Business is ready!")
        print("="*70)

        print("\n📝 Add these to your .env file:")
        print("-"*40)
        print(f"# Google My Business")
        print(f"GOOGLE_CLIENT_ID={client_id}")
        print(f"GOOGLE_CLIENT_SECRET={client_secret}")
        print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")

        # Try to get location ID
        print("\n🔍 Finding your business location ID...")

        try:
            # Get accounts
            accounts_response = requests.get(
                "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )

            if accounts_response.status_code == 200:
                accounts = accounts_response.json().get("accounts", [])
                if accounts:
                    account_name = accounts[0]["name"]
                    print(f"✅ Found account: {accounts[0].get('accountName', 'Your Business')}")

                    # Get locations
                    locations_response = requests.get(
                        f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10
                    )

                    if locations_response.status_code == 200:
                        locations = locations_response.json().get("locations", [])
                        if locations:
                            location = locations[0]
                            location_id = location["name"]
                            location_title = location.get("title", "Your Location")
                            location_address = location.get("address", {}).get("addressLines", [""])[0]

                            print(f"✅ Found location: {location_title}")
                            print(f"   Address: {location_address}")
                            print(f"\n# Optional - will auto-detect if not set")
                            print(f"GOOGLE_LOCATION_ID={location_id}")
                        else:
                            print("⚠️  No locations found. Will auto-detect when publishing.")
                else:
                    print("⚠️  No accounts found. Check your Google Business setup.")

        except Exception as e:
            print(f"⚠️  Could not fetch location (will auto-detect): {str(e)}")

        # Test the integration
        print("\n" + "="*70)
        print("🎯 WHAT'S NEXT?")
        print("="*70)

        print("""
1. Add the credentials to your .env file
2. Restart your AI Tickets backend
3. Test publishing an event:

   python3 -c "
   from app.services.event_publisher import publish_event
   from app.database import SessionLocal
   db = SessionLocal()
   result = publish_event(db, event_id=30, platforms=['google_my_business'])
   print(result)
   "

4. Your event will appear in:
   • Google Search (within 5-10 minutes)
   • Google Maps (within 30 minutes)
   • Google Business Profile (immediately)

🎉 Peru Chicken events will now show up in local Google searches!
        """)

    else:
        print(f"\n❌ Token exchange failed: {token_response.status_code}")
        print(token_response.json())
        print("\nPlease try again with a new authorization code.")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()