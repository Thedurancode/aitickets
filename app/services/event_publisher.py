"""
Multi-Platform Event Publisher

Publishes events to multiple ticketing and discovery platforms at once:
- Eventbrite
- Bandsintown
- Social media (via Postiz)
- Meta Ads
- Webhooks
- Calendar exports
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests

from sqlalchemy.orm import Session, joinedload
from app.config import get_settings
from app.models import Event, Venue, TicketTier

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Centralized event publishing to multiple platforms.

    Usage:
        publisher = EventPublisher(db, event_id=123)
        result = publisher.publish_to_all(platforms=["eventbrite", "bandsintown", "social"])
    """

    def __init__(self, db: Session, event_id: int):
        self.db = db
        self.event = self._load_event(event_id)
        self.settings = get_settings()

    def _load_event(self, event_id: int) -> Event:
        """Load event with related data."""
        event = (
            self.db.query(Event)
            .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
            .filter(Event.id == event_id)
            .first()
        )
        if not event:
            raise ValueError(f"Event {event_id} not found")
        return event

    def publish_to_all(
        self,
        platforms: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish to multiple platforms at once.

        Args:
            platforms: List of platforms to publish to (None = all configured)
            exclude: List of platforms to skip

        Returns:
            Dict with results per platform
        """
        if platforms is None:
            platforms = [
                "eventbrite",
                "bandsintown",
                "social_media",
                "meta_ads",
                "webhooks",
                "calendar"
            ]

        if exclude:
            platforms = [p for p in platforms if p not in exclude]

        results = {}

        for platform in platforms:
            try:
                if platform == "eventbrite":
                    results["eventbrite"] = self.publish_to_eventbrite()
                elif platform == "bandsintown":
                    results["bandsintown"] = self.publish_to_bandsintown()
                elif platform == "social_media":
                    results["social_media"] = self.publish_to_social_media()
                elif platform == "meta_ads":
                    results["meta_ads"] = self.publish_to_meta_ads()
                elif platform == "webhooks":
                    results["webhooks"] = self.trigger_webhooks()
                elif platform == "calendar":
                    results["calendar"] = self.generate_calendar_links()
                else:
                    results[platform] = {"success": False, "error": "Unknown platform"}
            except Exception as e:
                logger.exception(f"Failed to publish to {platform}")
                results[platform] = {"success": False, "error": str(e)}

        return results

    # ==================== Eventbrite ====================

    def publish_to_eventbrite(self) -> Dict[str, Any]:
        """
        Publish event to Eventbrite.

        Requires:
        - EVENTBRITE_API_KEY in config
        - EVENTBRITE_ORGANIZATION_ID in config

        Returns event URL and ID on success.
        """
        api_key = getattr(self.settings, 'eventbrite_api_key', None)
        org_id = getattr(self.settings, 'eventbrite_organization_id', None)

        if not api_key or not org_id:
            return {
                "success": False,
                "error": "Eventbrite not configured (missing API key or org ID)",
                "setup_url": "https://www.eventbrite.com/platform/api"
            }

        try:
            # Parse event datetime
            event_datetime = f"{self.event.event_date}T{self.event.event_time or '19:00'}:00"

            # Build Eventbrite event payload
            payload = {
                "event": {
                    "name": {"html": self.event.name},
                    "description": {"html": self.event.description or ""},
                    "start": {
                        "timezone": "America/New_York",  # Make this configurable
                        "utc": event_datetime + "Z"
                    },
                    "end": {
                        "timezone": "America/New_York",
                        "utc": event_datetime + "Z"  # Add duration
                    },
                    "currency": "USD",
                    "online_event": False,
                    "listed": True,
                    "shareable": True,
                    "invite_only": False,
                    "show_remaining": True,
                    "capacity": sum(t.capacity for t in self.event.ticket_tiers) if self.event.ticket_tiers else 100,
                }
            }

            # Add venue if available
            if self.event.venue:
                payload["event"]["venue_id"] = None  # Need to create venue first

            # Create event on Eventbrite
            response = requests.post(
                f"https://www.eventbriteapi.com/v3/organizations/{org_id}/events/",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"Eventbrite API error: {response.status_code}",
                    "details": response.json()
                }

            data = response.json()
            eventbrite_id = data.get("id")
            eventbrite_url = data.get("url")

            # Save eventbrite_id to event record
            if not hasattr(self.event, 'eventbrite_id'):
                # Column doesn't exist yet, skip saving (backward compatibility)
                pass
            else:
                self.event.eventbrite_id = eventbrite_id
                self.event.eventbrite_url = eventbrite_url
                self.db.commit()

            # Create ticket classes on Eventbrite for each tier
            ticket_tiers_created = []
            for tier in self.event.ticket_tiers:
                ticket_class_payload = {
                    "ticket_class": {
                        "name": tier.name,
                        "description": tier.description or "",
                        "quantity_total": tier.quantity_available,
                        "cost": f"USD,{tier.price / 100:.2f}" if tier.price > 0 else "free",
                        "free": tier.price == 0,
                        "sales_start": self.event.sale_start_date.isoformat() if self.event.sale_start_date else None,
                        "sales_end": self.event.event_date.isoformat() if self.event.event_date else None,
                    }
                }

                tier_response = requests.post(
                    f"https://www.eventbriteapi.com/v3/events/{eventbrite_id}/ticket_classes/",
                    headers={"Authorization": f"Bearer {eventbrite_token}"},
                    json=ticket_class_payload,
                    timeout=30
                )

                if tier_response.status_code in [200, 201]:
                    tier_data = tier_response.json()
                    ticket_tiers_created.append({
                        "tier_name": tier.name,
                        "eventbrite_ticket_class_id": tier_data.get("id"),
                    })

            return {
                "success": True,
                "platform": "eventbrite",
                "event_id": eventbrite_id,
                "event_url": eventbrite_url,
                "ticket_tiers_created": len(ticket_tiers_created),
                "tiers": ticket_tiers_created,
                "message": f"Published to Eventbrite with {len(ticket_tiers_created)} ticket tiers: {eventbrite_url}"
            }

        except Exception as e:
            logger.exception("Eventbrite publish failed")
            return {"success": False, "error": str(e)}

    # ==================== Bandsintown ====================

    def publish_to_bandsintown(self) -> Dict[str, Any]:
        """
        Publish event to Bandsintown.

        Requires:
        - BANDSINTOWN_APP_ID in config
        - Artist/performer name

        Returns event URL on success.
        """
        app_id = getattr(self.settings, 'bandsintown_app_id', None)

        if not app_id:
            return {
                "success": False,
                "error": "Bandsintown not configured (missing app ID)",
                "setup_url": "https://artists.bandsintown.com/support/api"
            }

        try:
            # Extract artist name from event or performer_names field
            artist_name = "Unknown Artist"  # Extract from event.performer_names if exists

            # Build Bandsintown event payload
            payload = {
                "datetime": f"{self.event.event_date}T{self.event.event_time or '19:00'}:00",
                "venue": {
                    "name": self.event.venue.name if self.event.venue else "TBD",
                    "city": "",  # Parse from venue.address
                    "region": "",
                    "country": "US",
                },
                "on_sale_datetime": datetime.now().isoformat(),
                "url": f"{self.settings.base_url}/events/{self.event.id}",
            }

            # Create event on Bandsintown
            response = requests.post(
                f"https://rest.bandsintown.com/artists/{artist_name}/events",
                json=payload,
                params={"app_id": app_id},
                timeout=30
            )

            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"Bandsintown API error: {response.status_code}",
                    "details": response.text
                }

            return {
                "success": True,
                "platform": "bandsintown",
                "message": f"Published to Bandsintown for {artist_name}"
            }

        except Exception as e:
            logger.exception("Bandsintown publish failed")
            return {"success": False, "error": str(e)}

    # ==================== Social Media ====================

    def publish_to_social_media(
        self,
        integration_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish event announcement to social media via Postiz.

        Args:
            integration_ids: List of Postiz integration IDs (None = all connected)
        """
        try:
            from app.services.social_media import post_to_social, get_integrations

            # Get connected integrations if not specified
            if not integration_ids:
                integrations_result = get_integrations()
                if not integrations_result.get("success"):
                    return integrations_result

                integrations = integrations_result.get("data", [])
                integration_ids = [i["id"] for i in integrations]

            if not integration_ids:
                return {
                    "success": False,
                    "error": "No social media integrations connected"
                }

            # Build post text
            post_text = f"""🎉 {self.event.name}

📅 {self.event.event_date} at {self.event.event_time or 'TBD'}
📍 {self.event.venue.name if self.event.venue else 'TBD'}

{self.event.description[:200] if self.event.description else ''}

🎫 Get tickets: {self.settings.base_url}/events/{self.event.id}"""

            # Add event image
            image_urls = [self.event.image_url] if self.event.image_url else []

            # Post to all integrations
            result = post_to_social(
                text=post_text,
                integration_ids=integration_ids,
                image_urls=image_urls,
                post_type="now"
            )

            return {
                "success": result.get("success", False),
                "platform": "social_media",
                "platforms_posted": len(integration_ids),
                "message": f"Posted to {len(integration_ids)} social channels",
                "details": result
            }

        except Exception as e:
            logger.exception("Social media publish failed")
            return {"success": False, "error": str(e)}

    # ==================== Meta Ads ====================

    def publish_to_meta_ads(
        self,
        daily_budget_cents: int = 1000,  # $10/day default
        radius_miles: int = 25
    ) -> Dict[str, Any]:
        """
        Create Facebook/Instagram ad campaign for event.

        Args:
            daily_budget_cents: Daily budget in cents
            radius_miles: Geo-targeting radius around venue
        """
        try:
            from app.services.meta_ads import create_event_campaign

            result = create_event_campaign(
                db=self.db,
                event_id=self.event.id,
                daily_budget_cents=daily_budget_cents,
                radius_miles=radius_miles,
                objective="OUTCOME_TRAFFIC"  # Drive traffic to ticket page
            )

            return {
                "success": result.get("success", False),
                "platform": "meta_ads",
                "campaign_id": result.get("campaign_id"),
                "message": f"Created Meta Ads campaign with ${daily_budget_cents/100}/day budget",
                "details": result
            }

        except Exception as e:
            logger.exception("Meta Ads publish failed")
            return {"success": False, "error": str(e)}

    # ==================== Webhooks ====================

    def trigger_webhooks(self) -> Dict[str, Any]:
        """Trigger outbound webhooks for event.created."""
        try:
            from app.services.webhooks import fire_webhook_event

            fire_webhook_event(
                db=self.db,
                event_type="event.created",
                payload={
                    "event_id": self.event.id,
                    "event_name": self.event.name,
                    "event_date": self.event.event_date,
                    "event_time": self.event.event_time,
                    "venue_name": self.event.venue.name if self.event.venue else None,
                    "image_url": self.event.image_url,
                    "ticket_url": f"{self.settings.base_url}/events/{self.event.id}",
                }
            )

            return {
                "success": True,
                "platform": "webhooks",
                "message": "Triggered outbound webhooks for event.created"
            }

        except Exception as e:
            logger.exception("Webhook trigger failed")
            return {"success": False, "error": str(e)}

    # ==================== Calendar ====================

    def generate_calendar_links(self) -> Dict[str, Any]:
        """Generate calendar export links."""
        try:
            from app.services.calendar import generate_google_calendar_url, generate_event_ics

            google_url = generate_google_calendar_url(self.event)
            ics_content, ics_filename = generate_event_ics(self.event)

            return {
                "success": True,
                "platform": "calendar",
                "google_calendar_url": google_url,
                "ics_filename": ics_filename,
                "ics_download_url": f"{self.settings.base_url}/events/{self.event.id}/calendar.ics",
                "message": "Calendar links generated"
            }

        except Exception as e:
            logger.exception("Calendar generation failed")
            return {"success": False, "error": str(e)}


# ==================== Helper Functions ====================


def publish_event(
    db: Session,
    event_id: int,
    platforms: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to publish event to multiple platforms.

    Args:
        db: Database session
        event_id: Event ID to publish
        platforms: List of platforms (None = all)
        exclude: Platforms to skip

    Returns:
        Dict with results per platform

    Example:
        result = publish_event(db, event_id=123, platforms=["eventbrite", "social_media"])

        # Result:
        {
            "eventbrite": {"success": True, "event_url": "https://..."},
            "social_media": {"success": True, "platforms_posted": 3}
        }
    """
    publisher = EventPublisher(db, event_id)
    return publisher.publish_to_all(platforms=platforms, exclude=exclude)


def get_available_platforms() -> List[Dict[str, Any]]:
    """
    Get list of available publishing platforms and their configuration status.

    Returns:
        List of platforms with status info
    """
    settings = get_settings()

    platforms = [
        {
            "id": "eventbrite",
            "name": "Eventbrite",
            "configured": bool(getattr(settings, 'eventbrite_api_key', None)),
            "requires": ["EVENTBRITE_API_KEY", "EVENTBRITE_ORGANIZATION_ID"],
            "docs_url": "https://www.eventbrite.com/platform/api"
        },
        {
            "id": "bandsintown",
            "name": "Bandsintown",
            "configured": bool(getattr(settings, 'bandsintown_app_id', None)),
            "requires": ["BANDSINTOWN_APP_ID"],
            "docs_url": "https://artists.bandsintown.com/support/api"
        },
        {
            "id": "social_media",
            "name": "Social Media (Postiz)",
            "configured": bool(settings.postiz_api_key),
            "requires": ["POSTIZ_API_KEY", "POSTIZ_URL"],
            "docs_url": "https://postiz.com/docs"
        },
        {
            "id": "meta_ads",
            "name": "Meta Ads (Facebook/Instagram)",
            "configured": bool(settings.meta_access_token and settings.meta_ad_account_id),
            "requires": ["META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"],
            "docs_url": "https://developers.facebook.com/docs/marketing-apis"
        },
        {
            "id": "webhooks",
            "name": "Custom Webhooks",
            "configured": True,  # Always available
            "requires": [],
            "docs_url": None
        },
        {
            "id": "calendar",
            "name": "Calendar (iCal/Google)",
            "configured": True,  # Always available
            "requires": [],
            "docs_url": None
        }
    ]

    return platforms
