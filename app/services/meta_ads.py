"""
Meta Ads (Facebook/Instagram) Integration Service

Handles:
- Campaign creation
- Ad set with geo-targeting (radius from venue)
- Ad creative creation
- Performance insights
- Geo-coordinate calculations
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session, joinedload
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from app.config import get_settings
from app.models import (
    Event, Venue, MetaAdCampaign, MetaAdStatus,
    MetaAdObjective, TicketTier, Ticket,
)

logger = logging.getLogger(__name__)


# ============== Meta API Client ==============


def get_meta_api_client():
    """Get configured Meta Marketing API client."""
    settings = get_settings()

    if not settings.meta_access_token or not settings.meta_ad_account_id:
        logger.warning("Meta Ads API credentials not configured")
        return None

    try:
        from facebook_business.api import FacebookAdsApi
        FacebookAdsApi.init(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            access_token=settings.meta_access_token,
        )
        return FacebookAdsApi
    except ImportError:
        logger.error("facebook-business package not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Meta API: {e}")
        return None


def get_ad_account():
    """Get the Meta ad account."""
    try:
        from facebook_business.adobjects.adaccount import AdAccount

        settings = get_settings()
        if not settings.meta_ad_account_id:
            return None

        return AdAccount(settings.meta_ad_account_id)
    except Exception as e:
        logger.error(f"Failed to get ad account: {e}")
        return None


# ============== Geo-Location Utilities ==============


def get_venue_coordinates(venue: Venue) -> Optional[tuple[float, float]]:
    """Get latitude and longitude for a venue using geocoding."""
    try:
        geolocator = Nominatim(user_agent="ai_tickets_1.0")

        location = geolocator.geocode(venue.address)
        if location:
            return (location.latitude, location.longitude)

        logger.warning(f"Could not geocode venue address: {venue.address}")
        return None
    except Exception as e:
        logger.error(f"Geocoding error for venue {venue.id}: {e}")
        return None


def calculate_radius_bbox(
    center_lat: float,
    center_lng: float,
    radius_miles: int
) -> dict:
    """
    Calculate bounding box for a radius around a center point.
    Returns location targeting spec for Meta Ads.
    """
    # Meta uses custom location keys for radius targeting
    # Format: "{lat},{lng},{radius}mi"

    location_key = f"{center_lat},{center_lng},{radius_miles}mi"

    return {
        "location_types": ["home"],
        "geo_countries": ["US"],
        "custom_locations": [{
            "latitude": center_lat,
            "longitude": center_lng,
            "radius": radius_miles,
            "distance_unit": "mile"
        }],
        "location_key": location_key
    }


# ============== Campaign Creation ==============


def create_campaign_for_event(
    db: Session,
    event_id: int,
    budget_cents: int,
    budget_type: str = "daily",
    objective: str = "traffic",
    radius_miles: int = 10,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    genders: Optional[str] = None,
    interests: Optional[List[str]] = None,
    primary_text: Optional[str] = None,
    headline: Optional[str] = None,
    description: Optional[str] = None,
    call_to_action: str = "GET_TICKETS",
) -> dict:
    """
    Create a complete Meta ad campaign for an event with geo-targeting.

    Args:
        db: Database session
        event_id: Event to create ad for
        budget_cents: Budget in cents
        budget_type: 'daily' or 'lifetime'
        objective: Campaign objective (awareness, traffic, engagement, leads)
        radius_miles: Targeting radius from venue
        age_min: Minimum age (18-65+)
        age_max: Maximum age
        genders: 'male', 'female', or None (all)
        interests: List of interest IDs from Meta
        primary_text: Ad primary text
        headline: Ad headline
        description: Ad description
        call_to_action: CTA button type

    Returns:
        Dict with campaign creation results
    """
    settings = get_settings()

    # Load event with venue
    event = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    if not event.venue:
        return {"error": "Event must have a venue for geo-targeting"}

    # Log event image status
    if event.image_url:
        logger.info(f"Event {event.id} ({event.name}) has image: {event.image_url}")
    else:
        logger.warning(f"Event {event.id} ({event.name}) has NO image - ad will be text-only")

    # Get venue coordinates
    coords = get_venue_coordinates(event.venue)
    if not coords:
        return {"error": "Could not determine venue coordinates for geo-targeting"}

    center_lat, center_lng = coords

    # Initialize Meta API
    api_client = get_meta_api_client()
    ad_account = get_ad_account()

    if not api_client or not ad_account:
        return {"error": "Meta Ads API not configured. Check your credentials."}

    try:
        # Map objective to Meta's objective
        objective_map = {
            "awareness": "AWARENESS",
            "traffic": "OUTCOME_TRAFFIC",
            "engagement": "OUTCOME_ENGAGEMENT",
            "leads": "OUTCOME_LEADS",
            "app_promotion": "OUTCOME_APP_PROMOTION",
            "messages": "OUTCOME_MESSAGES",
        }
        meta_objective = objective_map.get(objective, "OUTCOME_TRAFFIC")

        # Create campaign
        from facebook_business.adobjects.campaign import Campaign

        campaign_params = {
            Campaign.Field.name: f"{event.name} - {event.event_date}",
            Campaign.Field.objective: meta_objective,
            Campaign.Field.status: "PAUSED" if budget_type == "lifetime" else "ACTIVE",
            Campaign.Field.special_ad_categories: [],
        }

        if budget_type == "daily":
            campaign_params[Campaign.Field.daily_budget] = budget_cents
        else:
            campaign_params[Campaign.Field.lifetime_budget] = budget_cents

        campaign = ad_account.create_campaign(params=campaign_params)

        # Create ad set with geo-targeting
        from facebook_business.adobjects.adset import AdSet

        # Calculate targeting radius
        targeting_spec = {
            "geo_locations": calculate_radius_bbox(center_lat, center_lng, radius_miles),
        }

        # Add age targeting
        if age_min:
            targeting_spec["age_min"] = age_min
        if age_max:
            targeting_spec["age_max"] = age_max

        # Add gender targeting
        if genders and genders.lower() in ["male", "female"]:
            targeting_spec["genders"] = [1 if genders.lower() == "male" else 2]

        # Add interest targeting
        if interests:
            targeting_spec["interests"] = [{"id": i, "type": "interest"} for i in interests]

        # Calculate end time
        try:
            event_datetime = datetime.strptime(f"{event.event_date} {event.event_time or '23:59'}", "%Y-%m-%d %H:%M")
            event_datetime = event_datetime.replace(tzinfo=timezone.utc)
            end_time = event_datetime + timedelta(hours=24)
        except ValueError:
            end_time = datetime.now(timezone.utc) + timedelta(days=30)

        ad_set_params = {
            AdSet.Field.name: f"{event.name} - {radius_miles} miles",
            AdSet.Field.campaign_id: campaign["id"],
            AdSet.Field.optimization_goal: "OFFSITE_CONVERSIONS",
            AdSet.Field.billing_event: "IMPRESSIONS",
            AdSet.Field.bid_strategy: "LOWEST_COST_WITHOUT_CAP",
            AdSet.Field.start_time: int(datetime.now(timezone.utc).timestamp()),
            AdSet.Field.end_time: int(end_time.timestamp()),
            AdSet.Field.targeting: targeting_spec,
            AdSet.Field.status: "PAUSED" if budget_type == "lifetime" else "ACTIVE",
        }

        if budget_type == "daily":
            ad_set_params[AdSet.Field.daily_budget] = budget_cents
        else:
            ad_set_params[AdSet.Field.lifetime_budget] = budget_cents

        ad_set = ad_account.create_ad_set(params=ad_set_params)

        # Generate default ad copy if not provided
        base_url = settings.base_url.rstrip("/")
        event_url = f"{base_url}/events/{event.id}"

        if not primary_text:
            # Get lowest price
            lowest_price = None
            if event.ticket_tiers:
                active_prices = [
                    t.price for t in event.ticket_tiers
                    if t.quantity_sold < t.quantity_available
                ]
                lowest_price = min(active_prices) if active_prices else None

            if lowest_price:
                primary_text = f"🎟️ {event.name}\n\nTickets starting at ${lowest_price / 100:.2f}\n\n{event.venue.name}\n{event.event_date} at {event.event_time}\n\nGet your tickets now!"
            else:
                primary_text = f"🎟️ {event.name}\n\n{event.venue.name}\n{event.event_date} at {event.event_time}\n\nGet your tickets now!"

        if not headline:
            headline = event.name

        if not description:
            description = f"{event.venue.name} • {event.event_date}"

        # Create creative
        from facebook_business.adobjects.adcreative import AdCreative

        creative_params = {
            AdCreative.Field.name: f"{event.name} - Creative",
            AdCreative.Field.object_story_spec: {
                "page_id": "",  # Will need to be configured
                "link_data": {
                    "call_to_action": {"type": call_to_action},
                    "link": event_url,
                    "message": primary_text,
                    "name": headline,
                    "description": description,
                }
            }
        }

        # Add image if available
        image_used = False
        if event.image_url:
            logger.info(f"Event has image: {event.image_url}. Attempting to upload to Meta...")

            # Upload image to Meta first
            image_hash = upload_image_to_meta(event.image_url, ad_account)
            if image_hash:
                creative_params[AdCreative.Field.object_story_spec]["link_data"]["image_hash"] = image_hash
                image_used = True
                logger.info(f"Successfully uploaded event image to Meta (hash: {image_hash})")
            else:
                # Fallback: try using the image URL directly
                logger.warning(f"Image upload failed, trying to use URL directly: {event.image_url}")
                creative_params[AdCreative.Field.object_story_spec]["link_data"]["picture"] = event.image_url
                image_used = True

        if not event.image_url:
            logger.info(f"Event {event.id} has no image URL - ad will be text-only")

        creative = ad_account.create_ad_creative(params=creative_params)

        # Create ad
        from facebook_business.adobjects.ad import Ad

        ad_params = {
            Ad.Field.name: f"{event.name} - Ad",
            Ad.Field.adset_id: ad_set["id"],
            Ad.Field.creative: {"creative_id": creative["id"]},
            Ad.Field.status: "ACTIVE",
        }

        ad = ad_account.create_ad(params=ad_params)

        # Save to database
        db_campaign = MetaAdCampaign(
            event_id=event.id,
            meta_campaign_id=campaign["id"],
            meta_ad_set_id=ad_set["id"],
            meta_ad_id=ad["id"],
            meta_creative_id=creative["id"],
            name=f"{event.name} - Meta Ad",
            status=MetaAdStatus.ACTIVE,
            objective=MetaAdObjective(objective),
            budget_type=budget_type,
            budget_cents=budget_cents,
            targeting_radius_miles=radius_miles,
            age_min=age_min,
            age_max=age_max,
            genders=genders,
            primary_text=primary_text,
            headline=headline,
            description=description,
            call_to_action=call_to_action,
            image_url=event.image_url,
        )

        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)

        return {
            "success": True,
            "campaign_id": db_campaign.id,
            "meta_campaign_id": campaign["id"],
            "meta_ad_set_id": ad_set["id"],
            "meta_ad_id": ad["id"],
            "meta_creative_id": creative["id"],
            "message": "Meta ad campaign created successfully",
            "event": {
                "id": event.id,
                "name": event.name,
                "date": event.event_date,
                "venue": event.venue.name,
                "coordinates": {"lat": center_lat, "lng": center_lng},
                "targeting": {
                    "radius_miles": radius_miles,
                    "age_min": age_min,
                    "age_max": age_max,
                    "genders": genders,
                }
            }
        }

    except Exception as e:
        logger.error(f"Error creating Meta ad campaign: {e}", exc_info=True)

        # Save failed attempt
        db_campaign = MetaAdCampaign(
            event_id=event.id,
            name=f"{event.name} - Failed Ad",
            status=MetaAdStatus.FAILED,
            error_message=str(e),
            budget_cents=budget_cents,
            targeting_radius_miles=radius_miles,
            age_min=age_min,
            age_max=age_max,
            primary_text=primary_text,
            headline=headline,
        )
        db.add(db_campaign)
        db.commit()

        return {"error": f"Failed to create campaign: {str(e)}"}


def upload_image_to_meta(image_url: str, ad_account) -> Optional[str]:
    """Upload an image to Meta Ads and return the hash."""
    try:
        import requests
        import io
        from pathlib import Path

        # Download image
        logger.info(f"Downloading image from {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        # Get file extension from URL or default to jpg
        url_path = Path(image_url)
        ext = url_path.suffix.lstrip('.') or 'jpg'

        # Create filename with timestamp
        timestamp = int(datetime.now().timestamp())
        filename = f"event_{timestamp}.{ext}"

        # Upload to Meta using AdImage API
        from facebook_business.adobjects.adimage import AdImage

        # Meta requires either a file path or bytes
        # Using bytes directly from the downloaded response
        image_data = {
            AdImage.Field.filename: filename,
        }

        # Create the image using the ad account
        # Meta API v19+ supports uploading via API
        image = AdImage(parent_id=ad_account.get_id()).create(params={
            AdImage.Field.filename: filename,
            AdImage.Field.bytes: response.content,
        })

        image_hash = image.get(AdImage.Field.hash)
        logger.info(f"Successfully uploaded image to Meta, hash: {image_hash}")

        return image_hash

    except Exception as e:
        logger.error(f"Error uploading image to Meta: {e}")
        return None


# ============== Campaign Management ==============


def pause_campaign(db: Session, campaign_id: int) -> dict:
    """Pause a Meta ad campaign."""
    db_campaign = db.query(MetaAdCampaign).filter(MetaAdCampaign.id == campaign_id).first()

    if not db_campaign:
        return {"error": "Campaign not found"}

    if not db_campaign.meta_campaign_id:
        return {"error": "Campaign not linked to Meta"}

    try:
        api_client = get_meta_api_client()
        if not api_client:
            return {"error": "Meta API not configured"}

        from facebook_business.adobjects.campaign import Campaign

        campaign = Campaign(db_campaign.meta_campaign_id)
        campaign.api_update(params={Campaign.Field.status: "PAUSED"})

        db_campaign.status = MetaAdStatus.PAUSED
        db.commit()

        return {"success": True, "message": "Campaign paused"}

    except Exception as e:
        logger.error(f"Error pausing campaign: {e}")
        return {"error": str(e)}


def resume_campaign(db: Session, campaign_id: int) -> dict:
    """Resume a paused Meta ad campaign."""
    db_campaign = db.query(MetaAdCampaign).filter(MetaAdCampaign.id == campaign_id).first()

    if not db_campaign:
        return {"error": "Campaign not found"}

    if not db_campaign.meta_campaign_id:
        return {"error": "Campaign not linked to Meta"}

    try:
        api_client = get_meta_api_client()
        if not api_client:
            return {"error": "Meta API not configured"}

        from facebook_business.adobjects.campaign import Campaign

        campaign = Campaign(db_campaign.meta_campaign_id)
        campaign.api_update(params={Campaign.Field.status: "ACTIVE"})

        db_campaign.status = MetaAdStatus.ACTIVE
        db.commit()

        return {"success": True, "message": "Campaign resumed"}

    except Exception as e:
        logger.error(f"Error resuming campaign: {e}")
        return {"error": str(e)}


def update_campaign_budget(db: Session, campaign_id: int, budget_cents: int) -> dict:
    """Update the budget for a campaign."""
    db_campaign = db.query(MetaAdCampaign).filter(MetaAdCampaign.id == campaign_id).first()

    if not db_campaign:
        return {"error": "Campaign not found"}

    if not db_campaign.meta_campaign_id:
        return {"error": "Campaign not linked to Meta"}

    try:
        api_client = get_meta_api_client()
        if not api_client:
            return {"error": "Meta API not configured"}

        from facebook_business.adobjects.campaign import Campaign

        campaign = Campaign(db_campaign.meta_campaign_id)

        if db_campaign.budget_type == "daily":
            campaign.api_update(params={Campaign.Field.daily_budget: budget_cents})
        else:
            campaign.api_update(params={Campaign.Field.lifetime_budget: budget_cents})

        db_campaign.budget_cents = budget_cents
        db.commit()

        return {
            "success": True,
            "message": "Budget updated",
            "new_budget_cents": budget_cents
        }

    except Exception as e:
        logger.error(f"Error updating budget: {e}")
        return {"error": str(e)}


# ============== Insights & Analytics ==============


def get_campaign_insights(db: Session, campaign_id: int, days: int = 7) -> dict:
    """Get performance insights for a campaign."""
    db_campaign = db.query(MetaAdCampaign).filter(MetaAdCampaign.id == campaign_id).first()

    if not db_campaign:
        return {"error": "Campaign not found"}

    if not db_campaign.meta_campaign_id:
        return {"error": "Campaign not linked to Meta"}

    try:
        api_client = get_meta_api_client()
        if not api_client:
            return {"error": "Meta API not configured"}

        from facebook_business.adobjects.campaign import Campaign

        campaign = Campaign(db_campaign.meta_campaign_id)

        # Get insights
        insights = campaign.get_insights(
            fields=[
                "impressions",
                "clicks",
                "spend",
                "actions",
                "action_values",
                "ctr",
                "cpc",
                "cpm",
                "reach",
            ],
            params={
                "date_preset": f"last_{days}d",
                "level": "campaign",
            }
        )

        if not insights:
            return {
                "campaign_id": campaign_id,
                "message": "No insights available yet",
                "impressions": 0,
                "clicks": 0,
                "spend_cents": 0,
            }

        # Parse first insight
        insight = insights[0]

        results = {
            "campaign_id": campaign_id,
            "period_days": days,
            "impressions": int(insight.get("impressions", 0)),
            "clicks": int(insight.get("clicks", 0)),
            "spend_cents": int(float(insight.get("spend", 0)) * 100),
            "reach": int(insight.get("reach", 0)),
            "ctr_percent": round(float(insight.get("ctr", 0)) * 100, 2),
            "cpc_cents": int(float(insight.get("cpc", 0)) * 100),
            "cpm_cents": int(float(insight.get("cpm", 0)) * 100),
        }

        # Update cached metrics in database
        db_campaign.impressions = results["impressions"]
        db_campaign.clicks = results["clicks"]
        db_campaign.spend_cents = results["spend_cents"]
        db_campaign.last_synced_at = datetime.now(timezone.utc)
        db.commit()

        return results

    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        return {"error": str(e)}


def get_event_ads(db: Session, event_id: int) -> dict:
    """Get all Meta ad campaigns for an event."""
    campaigns = (
        db.query(MetaAdCampaign)
        .filter(MetaAdCampaign.event_id == event_id)
        .order_by(MetaAdCampaign.created_at.desc())
        .all()
    )

    return {
        "event_id": event_id,
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status.value,
                "objective": c.objective.value,
                "budget_cents": c.budget_cents,
                "budget_type": c.budget_type,
                "targeting_radius_miles": c.targeting_radius_miles,
                "impressions": c.impressions,
                "clicks": c.clicks,
                "spend_cents": c.spend_cents,
                "conversions": c.conversions,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in campaigns
        ]
    }


# ============== Targeting Suggestions ==============


def suggest_targeting_for_event(db: Session, event_id: int) -> dict:
    """Suggest targeting parameters based on event characteristics."""
    event = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.categories))
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    suggestions = {
        "event_id": event_id,
        "event_name": event.name,
        "venue": event.venue.name if event.venue else None,
        "suggestions": {}
    }

    # Default radius
    suggestions["suggestions"]["radius_miles"] = 10

    # Category-based targeting
    if event.categories:
        category_names = [c.name.lower() for c in event.categories]

        # Music events tend to have broader appeal
        if any(cat in category_names for cat in ["concert", "music", "jazz", "rock", "pop"]):
            suggestions["suggestions"]["radius_miles"] = 25
            suggestions["suggestions"]["age_min"] = 18
            suggestions["suggestions"]["age_max"] = 65

        # Sports events
        elif any(cat in category_names for cat in ["sports", "basketball", "football", "hockey"]):
            suggestions["suggestions"]["radius_miles"] = 50
            suggestions["suggestions"]["age_min"] = 21

        # Family events
        elif any(cat in category_names for cat in ["family", "kids", "children"]):
            suggestions["suggestions"]["radius_miles"] = 15
            suggestions["suggestions"]["age_min"] = 25
            suggestions["suggestions"]["age_max"] = 55

        # Comedy/nightlife
        elif any(cat in category_names for cat in ["comedy", "nightlife"]):
            suggestions["suggestions"]["age_min"] = 21
            suggestions["suggestions"]["age_max"] = 45

    # Price-based targeting
    if event.ticket_tiers:
        avg_price = sum(t.price for t in event.ticket_tiers) / len(event.ticket_tiers)
        if avg_price > 10000:  # > $100
            suggestions["suggestions"]["age_min"] = suggestions["suggestions"].get("age_min", 25)
            suggestions["suggestions"]["income_targeting"] = "higher"
        elif avg_price < 2500:  # < $25
            suggestions["suggestions"]["income_targeting"] = "all"

    # Past attendees targeting
    from sqlalchemy import func

    past_attendee_ages = (
        db.query(func.count(Ticket.id))
        .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
        .filter(
            TicketTier.event_id != event_id,
            Ticket.status.in_(["paid", "checked_in"])
        )
        .scalar()
    )

    if past_attendee_ages > 100:
        suggestions["suggestions"]["consider_lookalike"] = True

    return suggestions
