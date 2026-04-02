"""
Ad Campaign Management API Endpoints
CRUD operations for ad campaigns and creatives
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models import Event, AdCampaign, AdCreative, AdPerformance
from app.services.campaign_generator import generate_all_campaigns


router = APIRouter(prefix="/api/ad-campaigns", tags=["Ad Campaigns"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class TargetAudienceSchema(BaseModel):
    age_min: Optional[int] = 18
    age_max: Optional[int] = 65
    genders: Optional[List[str]] = ["all"]
    locations: Optional[List[dict]] = []
    languages: Optional[List[str]] = ["English"]
    interests: Optional[List[str]] = []
    behaviors: Optional[List[str]] = []
    keywords: Optional[List[str]] = []


class AdCreativeUpdate(BaseModel):
    headline: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    link_url: Optional[str] = None
    target_audience: Optional[dict] = None
    placements: Optional[List[str]] = None
    status: Optional[str] = None


class AdCreativeResponse(BaseModel):
    id: int
    ad_campaign_id: int
    platform: str
    format: str
    name: Optional[str]
    headline: Optional[str]
    body: Optional[str]
    cta: Optional[str]
    image_url: Optional[str]
    video_url: Optional[str]
    link_url: Optional[str]
    target_audience: Optional[dict]
    placements: Optional[List[str]]
    status: str
    is_test_variant: bool
    test_group: Optional[str]
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    budget_total: Optional[int] = None
    budget_daily: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    event_id: int
    platform: str
    campaign_type: str
    name: str
    objective: Optional[str]
    status: str
    budget_total: int
    budget_daily: int
    spend_total: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    created_at: datetime
    ad_count: int

    class Config:
        from_attributes = True


# ============================================================================
# CAMPAIGN GENERATION
# ============================================================================

@router.post("/generate/{event_id}")
async def auto_generate_campaigns(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Auto-generate ALL ad campaigns for an event
    Uses research report to create Meta, Google, Email campaigns
    """

    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if already has campaigns
    existing = db.query(AdCampaign).filter(AdCampaign.event_id == event_id).count()
    if existing > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Event already has {existing} campaigns. Delete them first or use update endpoints."
        )

    # Get research report (would come from event_research_agent)
    # For now, use basic data from event
    research_report = {
        "artist_research": {
            "name": event.name.split('-')[0].strip(),
            "genre": "music",
            "genre_label": "artist"
        },
        "marketing_plan": {
            "target_audience": {
                "age_range": {"min": 18, "max": 45},
                "primary": "Music fans"
            }
        },
        "spotify_research": {},
        "youtube_research": {},
        "wikipedia_research": {}
    }

    # Generate campaigns
    result = generate_all_campaigns(db, event_id, research_report)

    return result


# ============================================================================
# CAMPAIGN CRUD
# ============================================================================

@router.get("/event/{event_id}", response_model=List[CampaignResponse])
async def get_event_campaigns(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all campaigns for an event
    """

    campaigns = db.query(AdCampaign).filter(AdCampaign.event_id == event_id).all()

    return [
        CampaignResponse(
            **{**campaign.__dict__, "ad_count": len(campaign.ad_creatives)}
        )
        for campaign in campaigns
    ]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Get single campaign details
    """

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignResponse(
        **{**campaign.__dict__, "ad_count": len(campaign.ad_creatives)}
    )


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    updates: CampaignUpdate,
    db: Session = Depends(get_db)
):
    """
    Update campaign details
    """

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Update fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(campaign, field, value)

    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)

    return {"success": True, "campaign": CampaignResponse(**{**campaign.__dict__, "ad_count": len(campaign.ad_creatives)})}


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete campaign and all its ads
    """

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    db.delete(campaign)
    db.commit()

    return {"success": True, "message": "Campaign deleted"}


# ============================================================================
# AD CREATIVE CRUD
# ============================================================================

@router.get("/campaign/{campaign_id}/ads", response_model=List[AdCreativeResponse])
async def get_campaign_ads(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all ad creatives for a campaign
    """

    ads = db.query(AdCreative).filter(AdCreative.ad_campaign_id == campaign_id).all()

    return [AdCreativeResponse(**ad.__dict__) for ad in ads]


@router.get("/ads/{ad_id}", response_model=AdCreativeResponse)
async def get_ad(
    ad_id: int,
    db: Session = Depends(get_db)
):
    """
    Get single ad creative
    """

    ad = db.query(AdCreative).filter(AdCreative.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    return AdCreativeResponse(**ad.__dict__)


@router.patch("/ads/{ad_id}")
async def update_ad(
    ad_id: int,
    updates: AdCreativeUpdate,
    db: Session = Depends(get_db)
):
    """
    Update ad creative
    This is the main editor endpoint - allows customizing ads before publishing
    """

    ad = db.query(AdCreative).filter(AdCreative.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    # Update fields
    for field, value in updates.dict(exclude_unset=True).items():
        if field == "target_audience" and value:
            import json
            setattr(ad, field, json.dumps(value))
        elif field == "placements" and value:
            import json
            setattr(ad, field, json.dumps(value))
        else:
            setattr(ad, field, value)

    ad.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ad)

    return {"success": True, "ad": AdCreativeResponse(**ad.__dict__)}


@router.post("/ads/{ad_id}/approve")
async def approve_ad(
    ad_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve an ad for publishing
    """

    ad = db.query(AdCreative).filter(AdCreative.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    ad.status = "approved"
    ad.approved_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Ad approved"}


@router.post("/ads/{ad_id}/publish")
async def publish_ad(
    ad_id: int,
    db: Session = Depends(get_db)
):
    """
    Publish ad to platform (Meta/Google API)
    """

    ad = db.query(AdCreative).filter(AdCreative.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    if ad.status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Ad must be approved before publishing"
        )

    # Publish to Meta Ads API
    if ad.platform in ['facebook', 'instagram']:
        from app.services.meta_ads_integration import publish_ad_to_meta, get_meta_api
        from app.config import settings

        meta_api = get_meta_api()
        result = await publish_ad_to_meta(
            db=db,
            ad_creative=ad,
            meta_api=meta_api,
            facebook_page_id=settings.facebook_page_id,
            instagram_account_id=settings.instagram_account_id
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to publish to Meta: {result.get('error')}"
            )

        return result

    # Publish to Google Ads API
    elif ad.platform in ['google_search', 'google_display', 'youtube']:
        from app.services.google_ads_integration import publish_search_ad_to_google, get_google_ads_api

        google_api = get_google_ads_api()
        result = await publish_search_ad_to_google(
            db=db,
            ad_creative=ad,
            google_api=google_api
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to publish to Google: {result.get('error')}"
            )

        return result

    # Email / Social organic (no external API needed)
    else:
        ad.status = "active"
        ad.published_at = datetime.utcnow()
        db.commit()
        return {"success": True, "message": "Ad published successfully"}


@router.delete("/ads/{ad_id}")
async def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete ad creative
    """

    ad = db.query(AdCreative).filter(AdCreative.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    db.delete(ad)
    db.commit()

    return {"success": True, "message": "Ad deleted"}


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/campaign/{campaign_id}/approve-all")
async def approve_all_campaign_ads(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve all ads in a campaign at once
    """

    ads = db.query(AdCreative).filter(AdCreative.ad_campaign_id == campaign_id).all()
    if not ads:
        raise HTTPException(status_code=404, detail="No ads found for campaign")

    count = 0
    for ad in ads:
        if ad.status == "draft":
            ad.status = "approved"
            ad.approved_at = datetime.utcnow()
            count += 1

    db.commit()

    return {"success": True, "approved_count": count}


@router.post("/campaign/{campaign_id}/publish-all")
async def publish_all_campaign_ads(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Publish all approved ads in a campaign
    """

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    ads = db.query(AdCreative).filter(
        AdCreative.ad_campaign_id == campaign_id,
        AdCreative.status == "approved"
    ).all()

    if not ads:
        raise HTTPException(
            status_code=400,
            detail="No approved ads found. Approve ads first."
        )

    # TODO: Publish to Meta/Google API
    count = 0
    for ad in ads:
        ad.status = "active"
        ad.published_at = datetime.utcnow()
        count += 1

    campaign.status = "active"
    campaign.published_at = datetime.utcnow()

    db.commit()

    return {"success": True, "published_count": count}


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

@router.get("/ads/{ad_id}/performance")
async def get_ad_performance(
    ad_id: int,
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for an ad
    """

    ad = db.query(AdCreative).filter(AdCreative.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    performance = db.query(AdPerformance).filter(
        AdPerformance.ad_creative_id == ad_id
    ).all()

    total_impressions = sum(p.impressions for p in performance)
    total_clicks = sum(p.clicks for p in performance)
    total_conversions = sum(p.conversions for p in performance)
    total_spend = sum(p.spend for p in performance)
    total_revenue = sum(p.revenue for p in performance)

    return {
        "ad_id": ad_id,
        "ad_name": ad.name,
        "status": ad.status,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "total_spend": total_spend,
        "total_spend_formatted": f"${total_spend/100:.2f}",
        "total_revenue": total_revenue,
        "total_revenue_formatted": f"${total_revenue/100:.2f}",
        "ctr": round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0,
        "cpc": round((total_spend / total_clicks), 2) if total_clicks > 0 else 0,
        "roas": round((total_revenue / total_spend), 2) if total_spend > 0 else 0,
        "daily_performance": [
            {
                "date": p.date.isoformat(),
                "impressions": p.impressions,
                "clicks": p.clicks,
                "conversions": p.conversions,
                "spend": p.spend / 100,
                "revenue": p.revenue / 100
            }
            for p in performance
        ]
    }
