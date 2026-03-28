"""
Campaign Tracking API

Provides endpoints for:
- Email open tracking (pixel)
- Link click tracking (redirect)
- Campaign analytics
- Campaign management
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import io

from app.database import get_db
from app.models import Campaign, CampaignDelivery, CampaignType
from app.services.campaign_tracking import (
    create_campaign,
    track_delivery,
    track_open,
    track_click,
    get_campaign_stats,
)
from app.rate_limit import limiter

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# Pydantic schemas
class CampaignCreate(BaseModel):
    name: str
    campaign_type: str  # email, sms, notification
    subject: Optional[str] = None
    event_id: Optional[int] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    campaign_type: str
    subject: Optional[str]
    event_id: Optional[int]
    sent_count: int
    delivered_count: int
    failed_count: int
    opened_count: int
    clicked_count: int
    converted_count: int
    revenue_cents: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Tracking Endpoints (Public - No Auth) ==============

@router.get("/track/open/{tracking_token}")
async def track_email_open(tracking_token: str):
    """
    Email open tracking pixel.

    Responds with a 1x1 transparent GIF.
    Embed in emails as: <img src="https://yourdomain.com/api/campaigns/track/open/{token}" />

    **No authentication required** - public endpoint for pixel tracking.
    """
    track_open(tracking_token)

    # Return 1x1 transparent GIF
    gif_data = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
        b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00'
        b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
        b'\x44\x01\x00\x3b'
    )

    return StreamingResponse(
        io.BytesIO(gif_data),
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/track/click/{tracking_token}")
async def track_link_click(
    tracking_token: str,
    url: str = Query(..., description="Original URL to redirect to"),
):
    """
    Link click tracking and redirect.

    Tracks the click then redirects to original URL.
    Wrap links in emails as: https://yourdomain.com/api/campaigns/track/click/{token}?url={encoded_original_url}

    **No authentication required** - public endpoint for link tracking.
    """
    track_click(tracking_token)

    # Redirect to original URL
    return RedirectResponse(url=url, status_code=302)


# ============== Campaign Management Endpoints ==============

@router.post("", response_model=CampaignResponse)
@limiter.limit("30/minute")
async def create_new_campaign(
    request: Request,
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new campaign for tracking.

    **Request Body:**
    ```json
    {
      "name": "Summer Sale Email Blast",
      "campaign_type": "email",
      "subject": "🔥 50% Off All Events This Weekend!",
      "event_id": 123
    }
    ```

    **Returns:** Created campaign with ID for tracking deliveries.
    """
    try:
        campaign_type = CampaignType[campaign.campaign_type.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid campaign_type: {campaign.campaign_type}. Valid: email, sms, notification",
        )

    created_campaign = create_campaign(
        name=campaign.name,
        campaign_type=campaign_type,
        subject=campaign.subject,
        event_id=campaign.event_id,
    )

    return CampaignResponse(
        id=created_campaign.id,
        name=created_campaign.name,
        campaign_type=created_campaign.campaign_type.value,
        subject=created_campaign.subject,
        event_id=created_campaign.event_id,
        sent_count=created_campaign.sent_count,
        delivered_count=created_campaign.delivered_count,
        failed_count=created_campaign.failed_count,
        opened_count=created_campaign.opened_count,
        clicked_count=created_campaign.clicked_count,
        converted_count=created_campaign.converted_count,
        revenue_cents=created_campaign.revenue_cents,
        created_at=created_campaign.created_at,
    )


@router.get("", response_model=List[CampaignResponse])
@limiter.limit("60/minute")
async def list_campaigns(
    request: Request,
    campaign_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    List all campaigns with optional filtering.

    **Query Parameters:**
    - `campaign_type`: Filter by type (email/sms/notification)
    - `limit`: Max campaigns to return (default 50, max 100)
    - `offset`: Pagination offset
    """
    query = db.query(Campaign)

    if campaign_type:
        try:
            type_enum = CampaignType[campaign_type.upper()]
            query = query.filter(Campaign.campaign_type == type_enum)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid campaign_type: {campaign_type}",
            )

    query = query.order_by(Campaign.created_at.desc())
    campaigns = query.offset(offset).limit(limit).all()

    return [
        CampaignResponse(
            id=c.id,
            name=c.name,
            campaign_type=c.campaign_type.value,
            subject=c.subject,
            event_id=c.event_id,
            sent_count=c.sent_count,
            delivered_count=c.delivered_count,
            failed_count=c.failed_count,
            opened_count=c.opened_count,
            clicked_count=c.clicked_count,
            converted_count=c.converted_count,
            revenue_cents=c.revenue_cents,
            created_at=c.created_at,
        )
        for c in campaigns
    ]


@router.get("/{campaign_id}")
@limiter.limit("60/minute")
async def get_campaign(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed campaign analytics.

    **Returns:**
    - Campaign info
    - Performance stats (sent, delivered, opened, clicked, converted)
    - Performance rates (delivery rate, open rate, click rate, conversion rate)
    - Revenue metrics
    """
    return get_campaign_stats(campaign_id)


@router.get("/{campaign_id}/deliveries")
@limiter.limit("60/minute")
async def get_campaign_deliveries(
    request: Request,
    campaign_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    Get individual delivery records for a campaign.

    **Query Parameters:**
    - `limit`: Max deliveries to return (default 50, max 100)
    - `offset`: Pagination offset

    **Returns:** List of individual email/SMS deliveries with engagement data.
    """
    deliveries = (
        db.query(CampaignDelivery)
        .filter(CampaignDelivery.campaign_id == campaign_id)
        .order_by(CampaignDelivery.sent_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": d.id,
            "recipient_email": d.recipient_email,
            "recipient_phone": d.recipient_phone,
            "event_goer_id": d.event_goer_id,
            "sent_at": d.sent_at.isoformat() if d.sent_at else None,
            "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            "opened_at": d.opened_at.isoformat() if d.opened_at else None,
            "clicked_at": d.clicked_at.isoformat() if d.clicked_at else None,
            "converted_at": d.converted_at.isoformat() if d.converted_at else None,
            "revenue_cents": d.revenue_cents,
            "ticket_id": d.ticket_id,
        }
        for d in deliveries
    ]


@router.delete("/{campaign_id}")
@limiter.limit("10/minute")
async def delete_campaign(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Delete a campaign and all its delivery records."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    db.delete(campaign)
    db.commit()

    return {"status": "deleted", "campaign_id": campaign_id}
