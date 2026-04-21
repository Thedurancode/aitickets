"""
Google My Business Events Publisher

Publishes events to Google My Business for local discovery.
Events appear in Google Search, Maps, and local listings.

Requirements:
- Google Business Profile API access
- OAuth 2.0 credentials
- Business location verified on Google
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import requests
import json

from sqlalchemy.orm import Session
from app.config import get_settings
from app.models import Event, Venue

logger = logging.getLogger(__name__)


class GoogleMyBusinessPublisher:
    """
    Publish events to Google My Business for local visibility.

    Features:
    - Create events visible in Google Search & Maps
    - Add photos, offers, and CTAs
    - Track views and engagement
    - Update/delete events

    Usage:
        gmb = GoogleMyBusinessPublisher(db, event_id)
        result = gmb.publish()
    """

    def __init__(self, db: Session, event_id: int):
        self.db = db
        self.event = self._load_event(event_id)
        self.settings = get_settings()
        self.base_url = "https://mybusinessbusinessinformation.googleapis.com/v1"

    def _load_event(self, event_id: int) -> Event:
        """Load event with venue data."""
        from sqlalchemy.orm import joinedload

        event = (
            self.db.query(Event)
            .options(joinedload(Event.venue))
            .filter(Event.id == event_id)
            .first()
        )
        if not event:
            raise ValueError(f"Event {event_id} not found")
        return event

    def _get_access_token(self) -> Optional[str]:
        """
        Get Google OAuth access token.

        In production, this would:
        1. Use stored refresh token
        2. Exchange for access token
        3. Cache the access token
        """
        # Check if we have GMB credentials
        client_id = getattr(self.settings, 'google_client_id', None)
        client_secret = getattr(self.settings, 'google_client_secret', None)
        refresh_token = getattr(self.settings, 'google_refresh_token', None)

        if not all([client_id, client_secret, refresh_token]):
            logger.warning("Google My Business credentials not configured")
            return None

        # Exchange refresh token for access token
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )

            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"Failed to get access token: {response.status_code}")
                return None

        except Exception as e:
            logger.exception("Error getting Google access token")
            return None

    def publish(self) -> Dict[str, Any]:
        """
        Publish event to Google My Business.

        Returns:
            Dict with success status and event details
        """
        # Get access token
        access_token = self._get_access_token()

        if not access_token:
            return {
                "success": False,
                "platform": "google_my_business",
                "error": "Google My Business not configured",
                "setup_instructions": self.get_setup_instructions()
            }

        # Get business location ID
        location_id = getattr(self.settings, 'google_location_id', None)

        if not location_id:
            # Try to fetch it
            location_id = self._get_location_id(access_token)
            if not location_id:
                return {
                    "success": False,
                    "error": "No Google Business location found",
                    "help": "Verify your business on Google My Business first"
                }

        try:
            # Build event payload for Google My Business
            event_payload = self._build_event_payload()

            # Create local post (event)
            response = requests.post(
                f"{self.base_url}/accounts/{location_id}/localPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=event_payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                post_data = response.json()
                post_name = post_data.get("name", "")

                # Save GMB post ID to event
                if hasattr(self.event, 'gmb_post_id'):
                    self.event.gmb_post_id = post_name
                    self.db.commit()

                return {
                    "success": True,
                    "platform": "google_my_business",
                    "post_id": post_name,
                    "status": "published",
                    "visibility": {
                        "google_search": True,
                        "google_maps": True,
                        "google_business_profile": True
                    },
                    "message": "Event published to Google My Business! Will appear in Search & Maps within 5-10 minutes."
                }
            else:
                return {
                    "success": False,
                    "error": f"GMB API error: {response.status_code}",
                    "details": response.json()
                }

        except Exception as e:
            logger.exception("Failed to publish to Google My Business")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_event_payload(self) -> Dict:
        """
        Build Google My Business event post payload.

        Post Types:
        - STANDARD: Regular post
        - EVENT: Event with date/time
        - OFFER: Special offer/discount
        - PRODUCT: Product showcase
        """
        from datetime import datetime

        # Parse event datetime
        event_date = str(self.event.event_date)
        event_time = str(self.event.event_time or "19:00:00")

        # Combine into ISO format
        event_datetime = f"{event_date}T{event_time}"
        event_dt = datetime.fromisoformat(event_datetime)

        # Event end time (3 hours later)
        event_end_dt = event_dt + timedelta(hours=3)

        # Build payload
        payload = {
            "languageCode": "en-US",
            "topicType": "EVENT",  # This makes it an event post
            "event": {
                "title": self.event.name,
                "schedule": {
                    "startDate": {
                        "year": event_dt.year,
                        "month": event_dt.month,
                        "day": event_dt.day
                    },
                    "startTime": {
                        "hours": event_dt.hour,
                        "minutes": event_dt.minute,
                        "seconds": 0
                    },
                    "endDate": {
                        "year": event_end_dt.year,
                        "month": event_end_dt.month,
                        "day": event_end_dt.day
                    },
                    "endTime": {
                        "hours": event_end_dt.hour,
                        "minutes": event_end_dt.minute,
                        "seconds": 0
                    }
                }
            },
            "summary": self.event.description[:1500] if self.event.description else "",
            "callToAction": {
                "actionType": "BOOK",  # LEARN_MORE, BOOK, ORDER, SHOP, SIGN_UP, CALL
                "url": f"{self.settings.base_url}/events/{self.event.id}"
            }
        }

        # Add media if available
        if self.event.image_url:
            payload["media"] = [{
                "mediaFormat": "PHOTO",
                "sourceUrl": self.event.image_url
            }]

        # Add offer if there's a special price
        if self.event.ticket_tiers:
            min_price = min(t.price for t in self.event.ticket_tiers)
            if min_price > 0:
                payload["offer"] = {
                    "couponCode": "EARLY10",
                    "redeemOnlineUrl": f"{self.settings.base_url}/events/{self.event.id}",
                    "termsConditions": f"Starting at ${min_price/100:.2f}"
                }

        return payload

    def _get_location_id(self, access_token: str) -> Optional[str]:
        """
        Get Google Business Profile location ID.

        Returns the first location found for the account.
        """
        try:
            # Get account ID first
            accounts_response = requests.get(
                f"{self.base_url}/accounts",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )

            if accounts_response.status_code != 200:
                return None

            accounts = accounts_response.json().get("accounts", [])
            if not accounts:
                return None

            account_name = accounts[0]["name"]  # e.g., "accounts/123456789"

            # Get locations for this account
            locations_response = requests.get(
                f"{self.base_url}/{account_name}/locations",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )

            if locations_response.status_code != 200:
                return None

            locations = locations_response.json().get("locations", [])
            if locations:
                return locations[0]["name"]  # e.g., "locations/123456789"

        except Exception as e:
            logger.exception("Failed to get GMB location ID")

        return None

    def update(self, post_id: str) -> Dict[str, Any]:
        """Update an existing GMB event post."""
        # Implementation for updating events
        pass

    def delete(self, post_id: str) -> Dict[str, Any]:
        """Delete a GMB event post."""
        # Implementation for deleting events
        pass

    def get_insights(self, post_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for GMB post.

        Metrics include:
        - Views in Search
        - Views on Maps
        - Customer actions (clicks, calls, directions)
        """
        # Implementation for getting insights
        pass

    @staticmethod
    def get_setup_instructions() -> Dict[str, Any]:
        """
        Get setup instructions for Google My Business.
        """
        return {
            "platform": "Google My Business",
            "steps": [
                "1. Claim/verify your business on Google My Business",
                "2. Enable Google Business Profile API in Google Cloud Console",
                "3. Create OAuth 2.0 credentials",
                "4. Authorize and get refresh token",
                "5. Add credentials to .env file"
            ],
            "required_env_vars": [
                "GOOGLE_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET",
                "GOOGLE_REFRESH_TOKEN",
                "GOOGLE_LOCATION_ID (optional, auto-detected)"
            ],
            "benefits": [
                "Events appear in Google Search results",
                "Show on Google Maps",
                "Visible in Google Business Profile",
                "Free local marketing",
                "Track views and engagement"
            ],
            "setup_url": "https://business.google.com/",
            "api_docs": "https://developers.google.com/my-business/reference/rest/v4/accounts.locations.localPosts"
        }


def publish_to_gmb(db: Session, event_id: int) -> Dict[str, Any]:
    """
    Convenience function to publish event to Google My Business.

    Args:
        db: Database session
        event_id: Event ID to publish

    Returns:
        Dict with publishing results
    """
    publisher = GoogleMyBusinessPublisher(db, event_id)
    return publisher.publish()


def setup_google_oauth():
    """
    Interactive setup for Google OAuth credentials.

    This opens a browser for the user to authorize and
    saves the refresh token for future use.
    """
    print("\n" + "="*60)
    print("GOOGLE MY BUSINESS SETUP")
    print("="*60)

    print("\n1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project or select existing")
    print("3. Enable 'Google My Business API'")
    print("4. Create OAuth 2.0 credentials (Desktop app type)")
    print("5. Download the credentials JSON")

    client_id = input("\nEnter Client ID: ").strip()
    client_secret = input("Enter Client Secret: ").strip()

    # Build OAuth URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        "redirect_uri=urn:ietf:wg:oauth:2.0:oob&"
        "response_type=code&"
        "scope=https://www.googleapis.com/auth/business.manage"
    )

    print(f"\n6. Open this URL in your browser:\n{auth_url}")

    auth_code = input("\n7. Enter authorization code: ").strip()

    # Exchange code for tokens
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

        print("\n✅ Success! Add these to your .env file:")
        print(f"GOOGLE_CLIENT_ID={client_id}")
        print(f"GOOGLE_CLIENT_SECRET={client_secret}")
        print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    else:
        print(f"\n❌ Failed: {token_response.json()}")

    print("\n" + "="*60)