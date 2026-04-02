"""
Meta Ads API Integration
Publish ads to Facebook & Instagram via Meta Marketing API
"""

import json
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AdCampaign, AdCreative


class MetaAdsAPI:
    """
    Meta Marketing API Integration

    Requirements:
    1. Meta Business Account
    2. Facebook App with Marketing API access
    3. Access Token with ads_management permission
    4. Ad Account ID

    Setup Guide: https://developers.facebook.com/docs/marketing-api/get-started
    """

    def __init__(self, access_token: str, ad_account_id: str):
        """
        Initialize Meta Ads API client

        Args:
            access_token: Facebook App access token (long-lived)
            ad_account_id: Format: "act_123456789"
        """
        self.access_token = access_token
        self.ad_account_id = ad_account_id
        self.base_url = "https://graph.facebook.com/v18.0"

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request to Meta"""
        url = f"{self.base_url}/{endpoint}"
        params = {"access_token": self.access_token}

        if method == "GET":
            response = requests.get(url, params={**params, **(data or {})})
        elif method == "POST":
            response = requests.post(url, params=params, json=data)
        elif method == "DELETE":
            response = requests.delete(url, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    # ========================================================================
    # CAMPAIGN CREATION
    # ========================================================================

    def create_campaign(
        self,
        name: str,
        objective: str,
        status: str = "PAUSED",
        special_ad_categories: List[str] = None
    ) -> str:
        """
        Create Meta Ad Campaign

        Args:
            name: Campaign name
            objective: REACH, LINK_CLICKS, CONVERSIONS, VIDEO_VIEWS, etc.
            status: ACTIVE or PAUSED (start paused for safety)
            special_ad_categories: ['NONE'] or ['HOUSING', 'EMPLOYMENT', 'CREDIT']

        Returns:
            campaign_id (str)
        """
        data = {
            "name": name,
            "objective": objective,
            "status": status,
            "special_ad_categories": special_ad_categories or ["NONE"]
        }

        result = self._make_request("POST", f"{self.ad_account_id}/campaigns", data)
        return result["id"]

    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        optimization_goal: str,
        billing_event: str,
        bid_amount: int,
        daily_budget: int,
        targeting: Dict,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> str:
        """
        Create Ad Set (targeting + budget + schedule)

        Args:
            campaign_id: Parent campaign ID
            name: Ad set name
            optimization_goal: REACH, LINK_CLICKS, IMPRESSIONS, CONVERSIONS
            billing_event: IMPRESSIONS, LINK_CLICKS
            bid_amount: Max bid in cents (e.g., 100 = $1.00)
            daily_budget: Daily budget in cents (e.g., 5000 = $50.00)
            targeting: Meta targeting spec (see create_targeting_spec)
            start_time: When to start running ads
            end_time: When to stop (optional)

        Returns:
            ad_set_id (str)
        """
        data = {
            "name": name,
            "campaign_id": campaign_id,
            "optimization_goal": optimization_goal,
            "billing_event": billing_event,
            "bid_amount": bid_amount,
            "daily_budget": daily_budget,
            "targeting": targeting,
            "start_time": start_time.isoformat(),
            "status": "PAUSED"
        }

        if end_time:
            data["end_time"] = end_time.isoformat()

        result = self._make_request("POST", f"{self.ad_account_id}/adsets", data)
        return result["id"]

    def create_ad_creative(
        self,
        name: str,
        image_hash: str,
        message: str,
        link: str,
        call_to_action_type: str = "LEARN_MORE",
        page_id: Optional[str] = None,
        instagram_account_id: Optional[str] = None
    ) -> str:
        """
        Create Ad Creative (the actual ad content)

        Args:
            name: Creative name
            image_hash: Hash from upload_image()
            message: Ad body text
            link: Destination URL (event page)
            call_to_action_type: LEARN_MORE, SHOP_NOW, SIGN_UP, etc.
            page_id: Facebook Page ID (required for Facebook)
            instagram_account_id: Instagram Business Account ID

        Returns:
            creative_id (str)
        """
        object_story_spec = {
            "link_data": {
                "image_hash": image_hash,
                "link": link,
                "message": message,
                "call_to_action": {
                    "type": call_to_action_type,
                    "value": {"link": link}
                }
            }
        }

        if page_id:
            object_story_spec["page_id"] = page_id

        if instagram_account_id:
            object_story_spec["instagram_actor_id"] = instagram_account_id

        data = {
            "name": name,
            "object_story_spec": object_story_spec
        }

        result = self._make_request("POST", f"{self.ad_account_id}/adcreatives", data)
        return result["id"]

    def create_ad(
        self,
        ad_set_id: str,
        creative_id: str,
        name: str,
        status: str = "PAUSED"
    ) -> str:
        """
        Create Ad (links ad set + creative)

        Args:
            ad_set_id: Parent ad set ID
            creative_id: Ad creative ID
            name: Ad name
            status: ACTIVE or PAUSED

        Returns:
            ad_id (str)
        """
        data = {
            "name": name,
            "adset_id": ad_set_id,
            "creative": {"creative_id": creative_id},
            "status": status
        }

        result = self._make_request("POST", f"{self.ad_account_id}/ads", data)
        return result["id"]

    # ========================================================================
    # IMAGE UPLOAD
    # ========================================================================

    def upload_image(self, image_url: str) -> str:
        """
        Upload image to Meta Ad Account

        Args:
            image_url: URL of image (from Spotify, YouTube, Wikipedia)

        Returns:
            image_hash (str) - Use this in create_ad_creative()
        """
        # Download image
        image_response = requests.get(image_url)
        image_response.raise_for_status()

        # Upload to Meta
        files = {"filename": ("image.jpg", image_response.content, "image/jpeg")}
        params = {"access_token": self.access_token}

        url = f"{self.base_url}/{self.ad_account_id}/adimages"
        response = requests.post(url, params=params, files=files)
        response.raise_for_status()

        result = response.json()
        # Returns: {"images": {"image.jpg": {"hash": "abc123..."}}}
        return list(result["images"].values())[0]["hash"]

    # ========================================================================
    # TARGETING
    # ========================================================================

    def create_targeting_spec(
        self,
        age_min: int = 18,
        age_max: int = 65,
        genders: List[int] = None,  # [1] = men, [2] = women, [1,2] = all
        geo_locations: Dict = None,
        interests: List[Dict] = None,
        behaviors: List[Dict] = None,
        locales: List[int] = None,  # Language codes
        device_platforms: List[str] = None
    ) -> Dict:
        """
        Create Meta Ads targeting specification

        Args:
            age_min: Minimum age (18-65)
            age_max: Maximum age (18-65)
            genders: [1, 2] for all, [1] men, [2] women
            geo_locations: {"countries": ["US"], "cities": [...]}
            interests: [{"id": "6003139266461", "name": "Live music"}]
            behaviors: [{"id": "6002714895372", "name": "Concert goers"}]
            locales: [6] for Spanish, [24] for English (US)
            device_platforms: ["mobile", "desktop"]

        Returns:
            targeting dict for Meta API
        """
        targeting = {
            "age_min": age_min,
            "age_max": age_max,
            "genders": genders or [1, 2],
        }

        if geo_locations:
            targeting["geo_locations"] = geo_locations

        if interests:
            targeting["interests"] = interests

        if behaviors:
            targeting["behaviors"] = behaviors

        if locales:
            targeting["locales"] = locales

        if device_platforms:
            targeting["device_platforms"] = device_platforms
        else:
            targeting["device_platforms"] = ["mobile", "desktop"]

        # Facebook requires publisher_platforms
        targeting["publisher_platforms"] = ["facebook", "instagram"]
        targeting["facebook_positions"] = ["feed", "story"]
        targeting["instagram_positions"] = ["stream", "story"]

        return targeting

    # ========================================================================
    # PERFORMANCE INSIGHTS
    # ========================================================================

    def get_ad_insights(
        self,
        ad_id: str,
        date_preset: str = "last_7d",
        fields: List[str] = None
    ) -> Dict:
        """
        Get performance metrics for an ad

        Args:
            ad_id: Meta ad ID
            date_preset: today, yesterday, last_7d, last_30d, lifetime
            fields: impressions, clicks, spend, reach, ctr, cpc, conversions

        Returns:
            Insights data
        """
        if fields is None:
            fields = [
                "impressions",
                "clicks",
                "spend",
                "reach",
                "ctr",
                "cpc",
                "cpp",
                "frequency",
                "actions",  # Includes conversions
                "cost_per_action_type"
            ]

        params = {
            "fields": ",".join(fields),
            "date_preset": date_preset
        }

        result = self._make_request("GET", f"{ad_id}/insights", params)
        return result.get("data", [{}])[0]

    # ========================================================================
    # AD MANAGEMENT
    # ========================================================================

    def update_ad_status(self, ad_id: str, status: str) -> Dict:
        """
        Update ad status

        Args:
            ad_id: Meta ad ID
            status: ACTIVE, PAUSED, DELETED

        Returns:
            Updated ad
        """
        data = {"status": status}
        return self._make_request("POST", ad_id, data)

    def delete_ad(self, ad_id: str) -> Dict:
        """Delete ad"""
        return self._make_request("DELETE", ad_id)


# ============================================================================
# HIGH-LEVEL INTEGRATION FUNCTIONS
# ============================================================================

async def publish_ad_to_meta(
    db: Session,
    ad_creative: AdCreative,
    meta_api: MetaAdsAPI,
    facebook_page_id: str,
    instagram_account_id: Optional[str] = None
) -> Dict:
    """
    Publish an AdCreative to Meta Ads

    Full workflow:
    1. Upload image to Meta
    2. Create campaign (if not exists)
    3. Create ad set (targeting + budget)
    4. Create ad creative (image + copy)
    5. Create ad (link everything together)
    6. Update database with Meta IDs

    Args:
        db: Database session
        ad_creative: AdCreative model instance
        meta_api: MetaAdsAPI instance
        facebook_page_id: Your Facebook Page ID
        instagram_account_id: Your Instagram Business Account ID

    Returns:
        {
            "success": True,
            "meta_ad_id": "...",
            "meta_campaign_id": "...",
            "meta_ad_set_id": "...",
            "meta_creative_id": "..."
        }
    """

    try:
        campaign = ad_creative.ad_campaign

        # Parse targeting
        target_audience = json.loads(ad_creative.target_audience or '{}')

        # Step 1: Create or get campaign
        if not campaign.platform_campaign_id:
            # Map objective
            objective_map = {
                "awareness": "REACH",
                "conversion": "CONVERSIONS",
                "engagement": "LINK_CLICKS",
                "retargeting": "CONVERSIONS"
            }
            objective = objective_map.get(campaign.campaign_type, "LINK_CLICKS")

            meta_campaign_id = meta_api.create_campaign(
                name=campaign.name,
                objective=objective,
                status="PAUSED"  # Start paused for safety
            )

            campaign.platform_campaign_id = meta_campaign_id
            db.commit()
        else:
            meta_campaign_id = campaign.platform_campaign_id

        # Step 2: Upload image
        image_hash = meta_api.upload_image(ad_creative.image_url)

        # Step 3: Create targeting spec
        targeting = meta_api.create_targeting_spec(
            age_min=target_audience.get('age_min', 18),
            age_max=target_audience.get('age_max', 65),
            genders=[1, 2],  # All genders
            geo_locations={
                "countries": ["US"],
                "cities": target_audience.get('locations', [])
            },
            locales=[6, 24] if 'Spanish' in target_audience.get('languages', []) else [24]
        )

        # Step 4: Create ad set
        meta_ad_set_id = meta_api.create_ad_set(
            campaign_id=meta_campaign_id,
            name=f"{ad_creative.name} - Ad Set",
            optimization_goal="LINK_CLICKS",
            billing_event="IMPRESSIONS",
            bid_amount=500,  # $5.00 max bid
            daily_budget=campaign.budget_daily,
            targeting=targeting,
            start_time=campaign.start_date,
            end_time=campaign.end_date
        )

        # Step 5: Map CTA
        cta_map = {
            "Buy Tickets": "SHOP_NOW",
            "Get Tickets": "SHOP_NOW",
            "Buy Now": "SHOP_NOW",
            "Learn More": "LEARN_MORE",
            "See Event": "LEARN_MORE",
            "Sign Up": "SIGN_UP"
        }
        cta_type = cta_map.get(ad_creative.cta, "LEARN_MORE")

        # Step 6: Create ad creative
        meta_creative_id = meta_api.create_ad_creative(
            name=ad_creative.name or ad_creative.headline,
            image_hash=image_hash,
            message=f"{ad_creative.headline}\n\n{ad_creative.body}",
            link=ad_creative.link_url,
            call_to_action_type=cta_type,
            page_id=facebook_page_id,
            instagram_account_id=instagram_account_id
        )

        # Step 7: Create ad
        meta_ad_id = meta_api.create_ad(
            ad_set_id=meta_ad_set_id,
            creative_id=meta_creative_id,
            name=ad_creative.name or ad_creative.headline,
            status="PAUSED"  # Start paused, user must activate
        )

        # Step 8: Update database
        ad_creative.platform_ad_id = meta_ad_id
        ad_creative.status = "active"
        ad_creative.published_at = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "meta_ad_id": meta_ad_id,
            "meta_campaign_id": meta_campaign_id,
            "meta_ad_set_id": meta_ad_set_id,
            "meta_creative_id": meta_creative_id,
            "message": "Ad published to Meta! (Status: PAUSED - activate in Meta Ads Manager)"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def sync_meta_performance(
    db: Session,
    ad_creative: AdCreative,
    meta_api: MetaAdsAPI
) -> Dict:
    """
    Sync performance data from Meta Ads to database

    Args:
        db: Database session
        ad_creative: AdCreative with platform_ad_id
        meta_api: MetaAdsAPI instance

    Returns:
        Performance metrics
    """
    from app.models import AdPerformance
    from datetime import date

    if not ad_creative.platform_ad_id:
        return {"error": "Ad not published to Meta"}

    # Fetch insights from Meta
    insights = meta_api.get_ad_insights(
        ad_id=ad_creative.platform_ad_id,
        date_preset="yesterday"
    )

    # Parse insights
    impressions = int(insights.get('impressions', 0))
    clicks = int(insights.get('clicks', 0))
    spend = int(float(insights.get('spend', 0)) * 100)  # Convert to cents

    # Extract conversions (purchases)
    conversions = 0
    actions = insights.get('actions', [])
    for action in actions:
        if action.get('action_type') == 'purchase':
            conversions = int(action.get('value', 0))

    # Calculate metrics
    ctr = float(insights.get('ctr', 0))
    cpc = float(insights.get('cpc', 0))

    # Save to database
    perf = AdPerformance(
        ad_creative_id=ad_creative.id,
        date=date.today() - timedelta(days=1),
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        spend=spend,
        ctr=ctr,
        cpc=cpc
    )
    db.add(perf)
    db.commit()

    return {
        "success": True,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend": f"${spend/100:.2f}",
        "ctr": f"{ctr}%",
        "cpc": f"${cpc:.2f}"
    }


# ============================================================================
# HELPER: Get Meta API Instance
# ============================================================================

def get_meta_api() -> MetaAdsAPI:
    """
    Get configured Meta API instance

    Required in app/config.py:
        meta_access_token: str
        meta_ad_account_id: str  # Format: "act_123456789"
    """
    return MetaAdsAPI(
        access_token=settings.meta_access_token,
        ad_account_id=settings.meta_ad_account_id
    )
