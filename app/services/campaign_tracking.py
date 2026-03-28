"""
Campaign Performance Tracking Service

Tracks email/SMS campaign performance including:
- Opens (email pixel tracking)
- Clicks (link redirect tracking)
- Conversions (purchases after clicking)
- Revenue attribution
"""

import secrets
import logging
from typing import Optional, Dict
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Campaign, CampaignDelivery, CampaignType, Ticket

logger = logging.getLogger(__name__)


def create_campaign(
    name: str,
    campaign_type: CampaignType,
    subject: Optional[str] = None,
    event_id: Optional[int] = None,
) -> Campaign:
    """
    Create a new marketing campaign for tracking.

    Args:
        name: Campaign name (e.g., "Summer Sale Email Blast")
        campaign_type: email, sms, or notification
        subject: Email subject line or SMS preview
        event_id: Related event (if applicable)

    Returns:
        Created campaign object
    """
    db = SessionLocal()
    try:
        campaign = Campaign(
            name=name,
            campaign_type=campaign_type,
            subject=subject,
            event_id=event_id,
            sent_count=0,
            delivered_count=0,
            failed_count=0,
            opened_count=0,
            clicked_count=0,
            converted_count=0,
            revenue_cents=0,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        logger.info(f"Created campaign: {name} (ID: {campaign.id})")
        return campaign
    finally:
        db.close()


def track_delivery(
    campaign_id: int,
    recipient_email: Optional[str] = None,
    recipient_phone: Optional[str] = None,
    event_goer_id: Optional[int] = None,
) -> CampaignDelivery:
    """
    Track an individual email/SMS delivery.

    Generates a unique tracking token for pixel/link tracking.

    Args:
        campaign_id: Campaign this delivery belongs to
        recipient_email: Recipient email (for email campaigns)
        recipient_phone: Recipient phone (for SMS campaigns)
        event_goer_id: Event goer ID (for attribution)

    Returns:
        Created delivery object with tracking_token
    """
    db = SessionLocal()
    try:
        # Generate unique tracking token
        tracking_token = secrets.token_urlsafe(32)

        delivery = CampaignDelivery(
            campaign_id=campaign_id,
            recipient_email=recipient_email,
            recipient_phone=recipient_phone,
            event_goer_id=event_goer_id,
            tracking_token=tracking_token,
        )
        db.add(delivery)

        # Increment campaign sent count
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.sent_count += 1

        db.commit()
        db.refresh(delivery)

        logger.info(f"Tracked delivery: campaign={campaign_id}, token={tracking_token}")
        return delivery
    finally:
        db.close()


def track_delivery_status(
    tracking_token: str,
    delivered: bool = True,
    failure_reason: Optional[str] = None,
):
    """
    Update delivery status (delivered or failed).

    Args:
        tracking_token: Unique tracking token for this delivery
        delivered: Whether delivery succeeded
        failure_reason: Failure reason if delivery failed
    """
    db = SessionLocal()
    try:
        delivery = db.query(CampaignDelivery).filter(
            CampaignDelivery.tracking_token == tracking_token
        ).first()

        if not delivery:
            logger.warning(f"Delivery not found for token: {tracking_token}")
            return

        campaign = db.query(Campaign).filter(Campaign.id == delivery.campaign_id).first()

        if delivered:
            delivery.delivered_at = datetime.now(timezone.utc)
            if campaign:
                campaign.delivered_count += 1
        else:
            delivery.failed_at = datetime.now(timezone.utc)
            delivery.failure_reason = failure_reason
            if campaign:
                campaign.failed_count += 1

        db.commit()
        logger.info(f"Updated delivery status: token={tracking_token}, delivered={delivered}")
    finally:
        db.close()


def track_open(tracking_token: str):
    """
    Track email open (pixel loaded).

    Args:
        tracking_token: Unique tracking token for this delivery
    """
    db = SessionLocal()
    try:
        delivery = db.query(CampaignDelivery).filter(
            CampaignDelivery.tracking_token == tracking_token
        ).first()

        if not delivery:
            logger.warning(f"Delivery not found for token: {tracking_token}")
            return

        # Only track first open
        if not delivery.opened_at:
            delivery.opened_at = datetime.now(timezone.utc)

            # Increment campaign opened count
            campaign = db.query(Campaign).filter(Campaign.id == delivery.campaign_id).first()
            if campaign:
                campaign.opened_count += 1

            db.commit()
            logger.info(f"Tracked email open: token={tracking_token}")
    finally:
        db.close()


def track_click(tracking_token: str) -> Optional[str]:
    """
    Track link click in email/SMS.

    Args:
        tracking_token: Unique tracking token for this delivery

    Returns:
        Original URL to redirect to (if delivery found)
    """
    db = SessionLocal()
    try:
        delivery = db.query(CampaignDelivery).filter(
            CampaignDelivery.tracking_token == tracking_token
        ).first()

        if not delivery:
            logger.warning(f"Delivery not found for token: {tracking_token}")
            return None

        # Only track first click
        if not delivery.clicked_at:
            delivery.clicked_at = datetime.now(timezone.utc)

            # Increment campaign clicked count
            campaign = db.query(Campaign).filter(Campaign.id == delivery.campaign_id).first()
            if campaign:
                campaign.clicked_count += 1

            db.commit()
            logger.info(f"Tracked link click: token={tracking_token}")

        return tracking_token  # Return token for redirect logic
    finally:
        db.close()


def track_conversion(
    tracking_token: str,
    ticket_id: int,
    revenue_cents: int,
):
    """
    Track conversion (purchase after clicking).

    Links ticket purchase to campaign for revenue attribution.

    Args:
        tracking_token: Unique tracking token for this delivery
        ticket_id: Ticket purchased
        revenue_cents: Revenue from this ticket
    """
    db = SessionLocal()
    try:
        delivery = db.query(CampaignDelivery).filter(
            CampaignDelivery.tracking_token == tracking_token
        ).first()

        if not delivery:
            logger.warning(f"Delivery not found for token: {tracking_token}")
            return

        # Only track first conversion
        if not delivery.converted_at:
            delivery.converted_at = datetime.now(timezone.utc)
            delivery.ticket_id = ticket_id
            delivery.revenue_cents = revenue_cents

            # Increment campaign conversion count and revenue
            campaign = db.query(Campaign).filter(Campaign.id == delivery.campaign_id).first()
            if campaign:
                campaign.converted_count += 1
                campaign.revenue_cents += revenue_cents

            db.commit()
            logger.info(f"Tracked conversion: token={tracking_token}, revenue=${revenue_cents/100:.2f}")
    finally:
        db.close()


def get_campaign_stats(campaign_id: int) -> Dict:
    """
    Get performance stats for a campaign.

    Returns:
        Dictionary with campaign performance metrics
    """
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            return {"error": "Campaign not found"}

        delivery_rate = (campaign.delivered_count / campaign.sent_count * 100) if campaign.sent_count > 0 else 0
        open_rate = (campaign.opened_count / campaign.delivered_count * 100) if campaign.delivered_count > 0 else 0
        click_rate = (campaign.clicked_count / campaign.opened_count * 100) if campaign.opened_count > 0 else 0
        conversion_rate = (campaign.converted_count / campaign.clicked_count * 100) if campaign.clicked_count > 0 else 0
        roi = (campaign.revenue_cents / 100.0) if campaign.converted_count > 0 else 0

        return {
            "campaign_id": campaign.id,
            "name": campaign.name,
            "type": campaign.campaign_type.value,
            "subject": campaign.subject,
            "stats": {
                "sent": campaign.sent_count,
                "delivered": campaign.delivered_count,
                "failed": campaign.failed_count,
                "opened": campaign.opened_count,
                "clicked": campaign.clicked_count,
                "converted": campaign.converted_count,
            },
            "rates": {
                "delivery_rate": round(delivery_rate, 2),
                "open_rate": round(open_rate, 2),
                "click_rate": round(click_rate, 2),
                "conversion_rate": round(conversion_rate, 2),
            },
            "revenue": {
                "total_cents": campaign.revenue_cents,
                "total_dollars": round(campaign.revenue_cents / 100.0, 2),
                "revenue_per_conversion": round(roi, 2) if campaign.converted_count > 0 else 0,
            },
            "created_at": campaign.created_at.isoformat(),
        }
    finally:
        db.close()
