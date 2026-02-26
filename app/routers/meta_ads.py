"""
Meta Ads Router - REST API endpoints for Meta (Facebook/Instagram) ad management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.meta_ads import (
    create_campaign_for_event,
    pause_campaign,
    resume_campaign,
    update_campaign_budget,
    get_campaign_insights,
    get_event_ads,
    suggest_targeting_for_event,
)
from app.services.meta_ads_strategist import (
    generate_ad_strategy,
    create_strategy_and_campaign,
)
from app.models import MetaAdStatus, MetaAdObjective


router = APIRouter(prefix="/api/meta-ads", tags=["meta-ads"])


# ============== Schemas ==============


class CreateCampaignRequest(BaseModel):
    """Request to create a Meta ad campaign."""
    event_id: int = Field(..., description="Event to create ad for")
    budget_cents: int = Field(..., ge=100, description="Budget in cents (min $1)")
    budget_type: str = Field("daily", description="Budget type: 'daily' or 'lifetime'")
    objective: str = Field("traffic", description="Campaign objective")
    radius_miles: int = Field(10, ge=1, le=50, description="Targeting radius from venue")
    age_min: Optional[int] = Field(None, ge=18, le=65, description="Minimum age")
    age_max: Optional[int] = Field(None, ge=18, le=65, description="Maximum age")
    genders: Optional[str] = Field(None, description="Gender: 'male', 'female', or None for all")
    interests: Optional[List[str]] = Field(None, description="Meta interest IDs")
    primary_text: Optional[str] = Field(None, description="Ad primary text")
    headline: Optional[str] = Field(None, description="Ad headline")
    description: Optional[str] = Field(None, description="Ad description")
    call_to_action: str = Field("GET_TICKETS", description="CTA button type")


class UpdateBudgetRequest(BaseModel):
    """Request to update campaign budget."""
    budget_cents: int = Field(..., ge=100, description="New budget in cents")


# ============== Endpoints ==============


@router.post("/campaigns")
async def create_campaign(
    request: CreateCampaignRequest,
    db: Session = Depends(get_db)
):
    """
    Create a Meta ad campaign for an event with geo-targeting.

    The campaign will target users within the specified radius of the event venue.
    """
    result = create_campaign_for_event(
        db=db,
        event_id=request.event_id,
        budget_cents=request.budget_cents,
        budget_type=request.budget_type,
        objective=request.objective,
        radius_miles=request.radius_miles,
        age_min=request.age_min,
        age_max=request.age_max,
        genders=request.genders,
        interests=request.interests,
        primary_text=request.primary_text,
        headline=request.headline,
        description=request.description,
        call_to_action=request.call_to_action,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.post("/campaigns/{campaign_id}/pause")
async def pause_ad_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Pause a Meta ad campaign."""
    result = pause_campaign(db, campaign_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.post("/campaigns/{campaign_id}/resume")
async def resume_ad_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Resume a paused Meta ad campaign."""
    result = resume_campaign(db, campaign_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.put("/campaigns/{campaign_id}/budget")
async def update_budget(
    campaign_id: int,
    request: UpdateBudgetRequest,
    db: Session = Depends(get_db)
):
    """Update the budget for a campaign."""
    result = update_campaign_budget(db, campaign_id, request.budget_cents)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.get("/campaigns/{campaign_id}/insights")
async def get_insights(
    campaign_id: int,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get performance insights for a campaign.

    Parameters:
    - days: Number of days to look back (default: 7, max: 90)
    """
    if days > 90:
        days = 90
    if days < 1:
        days = 1

    result = get_campaign_insights(db, campaign_id, days)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.get("/events/{event_id}/ads")
async def list_event_ads(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get all Meta ad campaigns for an event."""
    return get_event_ads(db, event_id)


@router.get("/events/{event_id}/targeting-suggestions")
async def get_targeting_suggestions(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get targeting suggestions for an event based on its characteristics.

    Returns recommended radius, age ranges, and other targeting parameters.
    """
    result = suggest_targeting_for_event(db, event_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    return result


@router.get("/campaigns")
async def list_campaigns(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all Meta ad campaigns.

    Parameters:
    - status: Filter by status (active, paused, draft, archived, failed)
    - limit: Maximum results to return
    - offset: Results offset for pagination
    """
    from app.models import MetaAdCampaign
    from sqlalchemy.orm import joinedload

    query = db.query(MetaAdCampaign).options(joinedload(MetaAdCampaign.event))

    if status:
        try:
            status_enum = MetaAdStatus(status)
            query = query.filter(MetaAdCampaign.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    campaigns = (
        query.order_by(MetaAdCampaign.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
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
                "event": {
                    "id": c.event.id,
                    "name": c.event.name,
                    "date": c.event.event_date,
                } if c.event else None
            }
            for c in campaigns
        ],
        "count": len(campaigns),
        "limit": limit,
        "offset": offset
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific campaign."""
    from app.models import MetaAdCampaign
    from sqlalchemy.orm import joinedload

    campaign = (
        db.query(MetaAdCampaign)
        .options(joinedload(MetaAdCampaign.event))
        .filter(MetaAdCampaign.id == campaign_id)
        .first()
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status.value,
        "objective": campaign.objective.value,
        "budget_cents": campaign.budget_cents,
        "budget_type": campaign.budget_type,
        "targeting_radius_miles": campaign.targeting_radius_miles,
        "age_min": campaign.age_min,
        "age_max": campaign.age_max,
        "genders": campaign.genders,
        "primary_text": campaign.primary_text,
        "headline": campaign.headline,
        "description": campaign.description,
        "call_to_action": campaign.call_to_action,
        "image_url": campaign.image_url,
        "impressions": campaign.impressions,
        "clicks": campaign.clicks,
        "spend_cents": campaign.spend_cents,
        "conversions": campaign.conversions,
        "meta_campaign_id": campaign.meta_campaign_id,
        "meta_ad_set_id": campaign.meta_ad_set_id,
        "meta_ad_id": campaign.meta_ad_id,
        "meta_creative_id": campaign.meta_creative_id,
        "error_message": campaign.error_message,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "last_synced_at": campaign.last_synced_at.isoformat() if campaign.last_synced_at else None,
        "event": {
            "id": campaign.event.id,
            "name": campaign.event.name,
            "date": campaign.event.event_date,
            "venue": campaign.event.venue.name if campaign.event.venue else None,
        } if campaign.event else None
    }


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a Meta ad campaign from our database.
    Note: This does NOT delete the campaign from Meta - use pause first.
    """
    from app.models import MetaAdCampaign

    campaign = db.query(MetaAdCampaign).filter(MetaAdCampaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    db.delete(campaign)
    db.commit()

    return {"message": "Campaign deleted from database"}


# ============== AI-Powered Strategy Endpoints ==============


@router.post("/ai/strategy/{event_id}")
async def generate_ai_strategy(
    event_id: int,
    budget_cents: Optional[int] = None,
    radius_miles: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered ad campaign strategy for an event.

    Analyzes event context (venue, category, ticket price, date) and returns:
    - Optimal target audience (age, gender, radius, interests)
    - Budget recommendation
    - Campaign objective with reasoning
    - 3 ad creative variations (urgency, social proof, value)
    - Optimization recommendations

    Parameters:
    - budget_cents: Optional budget override in cents
    - radius_miles: Optional targeting radius override
    """
    result = await generate_ad_strategy(
        db=db,
        event_id=event_id,
        budget_override_cents=budget_cents,
        radius_override_miles=radius_miles,
    )

    if "error" in result and "fallback_strategy" not in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result


@router.post("/ai/create-campaign/{event_id}")
async def ai_create_campaign(
    event_id: int,
    budget_cents: Optional[int] = None,
    radius_miles: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Generate AI strategy AND automatically create the Meta ad campaign.

    One-click campaign creation with AI-optimized targeting and creative.
    The AI will analyze the event and create a complete campaign with:
    - Smart geo-targeting based on venue location
    - Audience demographics based on event type
    - Compelling ad copy with emojis and urgency
    - Proper budget allocation

    Parameters:
    - budget_cents: Optional budget override (default: AI recommendation)
    - radius_miles: Optional targeting radius override (default: AI recommendation)
    """
    result = await create_strategy_and_campaign(
        db=db,
        event_id=event_id,
        budget_cents=budget_cents,
        radius_miles=radius_miles,
        auto_create=True,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return result
