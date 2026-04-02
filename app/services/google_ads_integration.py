"""
Google Ads API Integration
Publish ads to Google Search, Display, and YouTube via Google Ads API
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from app.config import settings
from app.models import AdCampaign, AdCreative


class GoogleAdsAPI:
    """
    Google Ads API Integration

    Requirements:
    1. Google Ads Account
    2. Google Cloud Project with Google Ads API enabled
    3. OAuth2 credentials (client_id, client_secret, refresh_token)
    4. Developer token
    5. Customer ID (Google Ads account ID)

    Setup Guide: https://developers.google.com/google-ads/api/docs/first-call/overview
    """

    def __init__(
        self,
        developer_token: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        customer_id: str,
        login_customer_id: Optional[str] = None
    ):
        """
        Initialize Google Ads API client

        Args:
            developer_token: Google Ads API developer token
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            refresh_token: OAuth2 refresh token
            customer_id: Google Ads customer ID (without hyphens)
            login_customer_id: Manager account ID (if using MCC)
        """
        self.customer_id = customer_id.replace("-", "")
        self.login_customer_id = login_customer_id.replace("-", "") if login_customer_id else None

        # Create credentials dict
        credentials = {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True
        }

        if self.login_customer_id:
            credentials["login_customer_id"] = self.login_customer_id

        # Initialize client
        self.client = GoogleAdsClient.load_from_dict(credentials)
        self.ga_service = self.client.get_service("GoogleAdsService")

    # ========================================================================
    # CAMPAIGN CREATION
    # ========================================================================

    def create_campaign(
        self,
        name: str,
        advertising_channel_type: str,
        budget_amount_micros: int,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Create Google Ads Campaign

        Args:
            name: Campaign name
            advertising_channel_type: SEARCH, DISPLAY, VIDEO
            budget_amount_micros: Daily budget in micros (1,000,000 = $1)
            start_date: Campaign start date
            end_date: Campaign end date (optional)

        Returns:
            campaign_resource_name (str)
        """
        campaign_service = self.client.get_service("CampaignService")
        campaign_budget_service = self.client.get_service("CampaignBudgetService")

        # Create campaign budget
        budget_operation = self.client.get_type("CampaignBudgetOperation")
        budget = budget_operation.create
        budget.name = f"{name} - Budget"
        budget.amount_micros = budget_amount_micros
        budget.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD

        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=self.customer_id,
            operations=[budget_operation]
        )
        budget_resource_name = budget_response.results[0].resource_name

        # Create campaign
        campaign_operation = self.client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        campaign.name = name
        campaign.advertising_channel_type = getattr(
            self.client.enums.AdvertisingChannelTypeEnum,
            advertising_channel_type
        )
        campaign.status = self.client.enums.CampaignStatusEnum.PAUSED
        campaign.campaign_budget = budget_resource_name
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign.network_settings.target_content_network = False

        # Set dates
        campaign.start_date = start_date.strftime("%Y%m%d")
        if end_date:
            campaign.end_date = end_date.strftime("%Y%m%d")

        # Create campaign
        campaign_response = campaign_service.mutate_campaigns(
            customer_id=self.customer_id,
            operations=[campaign_operation]
        )

        return campaign_response.results[0].resource_name

    def create_ad_group(
        self,
        campaign_resource_name: str,
        name: str,
        cpc_bid_micros: int
    ) -> str:
        """
        Create Ad Group

        Args:
            campaign_resource_name: Parent campaign resource name
            name: Ad group name
            cpc_bid_micros: Max CPC bid in micros (1,000,000 = $1)

        Returns:
            ad_group_resource_name (str)
        """
        ad_group_service = self.client.get_service("AdGroupService")

        ad_group_operation = self.client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        ad_group.name = name
        ad_group.campaign = campaign_resource_name
        ad_group.type_ = self.client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ad_group.status = self.client.enums.AdGroupStatusEnum.ENABLED
        ad_group.cpc_bid_micros = cpc_bid_micros

        response = ad_group_service.mutate_ad_groups(
            customer_id=self.customer_id,
            operations=[ad_group_operation]
        )

        return response.results[0].resource_name

    # ========================================================================
    # SEARCH ADS
    # ========================================================================

    def create_responsive_search_ad(
        self,
        ad_group_resource_name: str,
        headlines: List[str],
        descriptions: List[str],
        final_urls: List[str],
        path1: Optional[str] = None,
        path2: Optional[str] = None
    ) -> str:
        """
        Create Responsive Search Ad

        Args:
            ad_group_resource_name: Parent ad group
            headlines: 3-15 headlines (max 30 chars each)
            descriptions: 2-4 descriptions (max 90 chars each)
            final_urls: Landing page URLs
            path1: Display path 1 (e.g., "tickets")
            path2: Display path 2 (e.g., "anuel-aa")

        Returns:
            ad_resource_name (str)
        """
        ad_group_ad_service = self.client.get_service("AdGroupAdService")

        ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_operation.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum.PAUSED

        # Create responsive search ad
        ad = ad_group_ad.ad
        ad.final_urls.extend(final_urls)

        if path1:
            ad.final_url_suffix = f"path1={path1}"
        if path2:
            ad.final_url_suffix += f"&path2={path2}"

        # Add headlines
        for headline_text in headlines[:15]:  # Max 15
            headline = self.client.get_type("AdTextAsset")
            headline.text = headline_text[:30]  # Max 30 chars
            ad.responsive_search_ad.headlines.append(headline)

        # Add descriptions
        for description_text in descriptions[:4]:  # Max 4
            description = self.client.get_type("AdTextAsset")
            description.text = description_text[:90]  # Max 90 chars
            ad.responsive_search_ad.descriptions.append(description)

        # Create ad
        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=self.customer_id,
            operations=[ad_group_ad_operation]
        )

        return response.results[0].resource_name

    def add_keywords(
        self,
        ad_group_resource_name: str,
        keywords: List[Dict[str, str]]
    ) -> List[str]:
        """
        Add keywords to ad group

        Args:
            ad_group_resource_name: Parent ad group
            keywords: [{"text": "concert tickets", "match_type": "EXACT"}]

        Returns:
            List of keyword resource names
        """
        ad_group_criterion_service = self.client.get_service("AdGroupCriterionService")

        operations = []
        for kw in keywords:
            operation = self.client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = ad_group_resource_name
            criterion.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.keyword.text = kw["text"]
            criterion.keyword.match_type = getattr(
                self.client.enums.KeywordMatchTypeEnum,
                kw.get("match_type", "BROAD")
            )
            operations.append(operation)

        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=self.customer_id,
            operations=operations
        )

        return [result.resource_name for result in response.results]

    # ========================================================================
    # DISPLAY ADS
    # ========================================================================

    def upload_image(self, image_url: str, image_name: str) -> str:
        """
        Upload image to Google Ads

        Args:
            image_url: URL of image
            image_name: Name for the image

        Returns:
            asset_resource_name (str)
        """
        import requests

        asset_service = self.client.get_service("AssetService")

        # Download image
        response = requests.get(image_url)
        response.raise_for_status()
        image_data = response.content

        # Create asset
        asset_operation = self.client.get_type("AssetOperation")
        asset = asset_operation.create
        asset.name = image_name
        asset.type_ = self.client.enums.AssetTypeEnum.IMAGE
        asset.image_asset.data = image_data

        asset_response = asset_service.mutate_assets(
            customer_id=self.customer_id,
            operations=[asset_operation]
        )

        return asset_response.results[0].resource_name

    def create_responsive_display_ad(
        self,
        ad_group_resource_name: str,
        headlines: List[str],
        descriptions: List[str],
        business_name: str,
        marketing_image_resource_name: str,
        final_urls: List[str]
    ) -> str:
        """
        Create Responsive Display Ad

        Args:
            ad_group_resource_name: Parent ad group
            headlines: 1-5 short headlines (max 30 chars)
            descriptions: 1-5 descriptions (max 90 chars)
            business_name: Business name (max 25 chars)
            marketing_image_resource_name: Image asset resource name
            final_urls: Landing page URLs

        Returns:
            ad_resource_name (str)
        """
        ad_group_ad_service = self.client.get_service("AdGroupAdService")

        ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_operation.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum.PAUSED

        ad = ad_group_ad.ad
        ad.final_urls.extend(final_urls)

        # Responsive display ad
        rda = ad.responsive_display_ad
        rda.business_name = business_name[:25]

        # Headlines
        for headline_text in headlines[:5]:
            headline = self.client.get_type("AdTextAsset")
            headline.text = headline_text[:30]
            rda.headlines.append(headline)

        # Descriptions
        for desc_text in descriptions[:5]:
            description = self.client.get_type("AdTextAsset")
            description.text = desc_text[:90]
            rda.descriptions.append(description)

        # Marketing image
        marketing_image = self.client.get_type("AdImageAsset")
        marketing_image.asset = marketing_image_resource_name
        rda.marketing_images.append(marketing_image)

        # Create ad
        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=self.customer_id,
            operations=[ad_group_ad_operation]
        )

        return response.results[0].resource_name

    # ========================================================================
    # TARGETING
    # ========================================================================

    def add_location_targeting(
        self,
        campaign_resource_name: str,
        location_ids: List[str]
    ) -> List[str]:
        """
        Add location targeting to campaign

        Args:
            campaign_resource_name: Campaign resource name
            location_ids: ["1023191"] = New York, ["2840"] = United States

        Returns:
            List of criterion resource names
        """
        campaign_criterion_service = self.client.get_service("CampaignCriterionService")

        operations = []
        for location_id in location_ids:
            operation = self.client.get_type("CampaignCriterionOperation")
            criterion = operation.create
            criterion.campaign = campaign_resource_name
            criterion.location.geo_target_constant = f"geoTargetConstants/{location_id}"
            operations.append(operation)

        response = campaign_criterion_service.mutate_campaign_criteria(
            customer_id=self.customer_id,
            operations=operations
        )

        return [result.resource_name for result in response.results]

    # ========================================================================
    # PERFORMANCE REPORTING
    # ========================================================================

    def get_campaign_performance(
        self,
        campaign_resource_name: str,
        date_range: str = "LAST_7_DAYS"
    ) -> Dict:
        """
        Get campaign performance metrics

        Args:
            campaign_resource_name: Campaign to report on
            date_range: TODAY, YESTERDAY, LAST_7_DAYS, LAST_30_DAYS

        Returns:
            Performance metrics dict
        """
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            WHERE campaign.resource_name = '{campaign_resource_name}'
            AND segments.date DURING {date_range}
        """

        response = self.ga_service.search(
            customer_id=self.customer_id,
            query=query
        )

        results = list(response)
        if not results:
            return {}

        row = results[0]
        return {
            "campaign_id": row.campaign.id,
            "campaign_name": row.campaign.name,
            "impressions": row.metrics.impressions,
            "clicks": row.metrics.clicks,
            "cost_micros": row.metrics.cost_micros,
            "cost": row.metrics.cost_micros / 1_000_000,
            "conversions": row.metrics.conversions,
            "conversions_value": row.metrics.conversions_value,
            "ctr": row.metrics.ctr,
            "average_cpc": row.metrics.average_cpc / 1_000_000
        }

    def get_ad_performance(
        self,
        ad_group_ad_resource_name: str,
        date_range: str = "LAST_7_DAYS"
    ) -> Dict:
        """
        Get ad performance metrics

        Args:
            ad_group_ad_resource_name: Ad to report on
            date_range: TODAY, YESTERDAY, LAST_7_DAYS, LAST_30_DAYS

        Returns:
            Performance metrics dict
        """
        query = f"""
            SELECT
                ad_group_ad.ad.id,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM ad_group_ad
            WHERE ad_group_ad.resource_name = '{ad_group_ad_resource_name}'
            AND segments.date DURING {date_range}
        """

        response = self.ga_service.search(
            customer_id=self.customer_id,
            query=query
        )

        results = list(response)
        if not results:
            return {}

        row = results[0]
        return {
            "ad_id": row.ad_group_ad.ad.id,
            "impressions": row.metrics.impressions,
            "clicks": row.metrics.clicks,
            "cost_micros": row.metrics.cost_micros,
            "cost": row.metrics.cost_micros / 1_000_000,
            "conversions": row.metrics.conversions,
            "ctr": row.metrics.ctr,
            "average_cpc": row.metrics.average_cpc / 1_000_000
        }

    # ========================================================================
    # AD MANAGEMENT
    # ========================================================================

    def update_ad_status(
        self,
        ad_group_ad_resource_name: str,
        status: str
    ) -> str:
        """
        Update ad status

        Args:
            ad_group_ad_resource_name: Ad resource name
            status: ENABLED, PAUSED, REMOVED

        Returns:
            Updated resource name
        """
        ad_group_ad_service = self.client.get_service("AdGroupAdService")

        ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_operation.update
        ad_group_ad.resource_name = ad_group_ad_resource_name
        ad_group_ad.status = getattr(self.client.enums.AdGroupAdStatusEnum, status)

        # Set update mask
        self.client.copy_from(
            ad_group_ad_operation.update_mask,
            self.client.get_type("FieldMask")(paths=["status"])
        )

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=self.customer_id,
            operations=[ad_group_ad_operation]
        )

        return response.results[0].resource_name


# ============================================================================
# HIGH-LEVEL INTEGRATION FUNCTIONS
# ============================================================================

async def publish_search_ad_to_google(
    db: Session,
    ad_creative: AdCreative,
    google_api: GoogleAdsAPI
) -> Dict:
    """
    Publish Search Ad to Google Ads

    Workflow:
    1. Create campaign (if not exists)
    2. Create ad group
    3. Add keywords
    4. Create responsive search ad
    5. Update database

    Args:
        db: Database session
        ad_creative: AdCreative instance
        google_api: GoogleAdsAPI instance

    Returns:
        Success dict with Google resource names
    """
    try:
        campaign = ad_creative.ad_campaign

        # Parse targeting for keywords
        target_audience = json.loads(ad_creative.target_audience or '{}')
        keywords = target_audience.get('keywords', [])

        # Step 1: Create campaign (if not exists)
        if not campaign.platform_campaign_id:
            campaign_resource_name = google_api.create_campaign(
                name=campaign.name,
                advertising_channel_type="SEARCH",
                budget_amount_micros=campaign.budget_daily * 10,  # cents to micros
                start_date=campaign.start_date,
                end_date=campaign.end_date
            )
            campaign.platform_campaign_id = campaign_resource_name
            db.commit()
        else:
            campaign_resource_name = campaign.platform_campaign_id

        # Step 2: Create ad group
        ad_group_resource_name = google_api.create_ad_group(
            campaign_resource_name=campaign_resource_name,
            name=f"{ad_creative.name} - Ad Group",
            cpc_bid_micros=5_000_000  # $5 max CPC
        )

        # Step 3: Add keywords
        keyword_list = [
            {"text": kw, "match_type": "PHRASE"}
            for kw in keywords[:20]  # Max 20 keywords
        ]
        google_api.add_keywords(ad_group_resource_name, keyword_list)

        # Step 4: Create responsive search ad
        headlines = [
            ad_creative.headline,
            f"{ad_creative.headline} - Get Tickets",
            "Buy Tickets Now"
        ]
        descriptions = [
            ad_creative.body[:90],
            f"Tickets available now for {ad_creative.headline[:40]}"
        ]

        ad_resource_name = google_api.create_responsive_search_ad(
            ad_group_resource_name=ad_group_resource_name,
            headlines=headlines,
            descriptions=descriptions,
            final_urls=[ad_creative.link_url]
        )

        # Step 5: Update database
        ad_creative.platform_ad_id = ad_resource_name
        ad_creative.status = "active"
        ad_creative.published_at = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "google_ad_id": ad_resource_name,
            "google_campaign_id": campaign_resource_name,
            "google_ad_group_id": ad_group_resource_name,
            "message": "Search ad published to Google! (Status: PAUSED - activate in Google Ads)"
        }

    except GoogleAdsException as ex:
        error_msg = f"Google Ads error: {ex.error.code().name}"
        for error in ex.failure.errors:
            error_msg += f" - {error.message}"

        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def sync_google_performance(
    db: Session,
    ad_creative: AdCreative,
    google_api: GoogleAdsAPI
) -> Dict:
    """
    Sync performance from Google Ads to database

    Args:
        db: Database session
        ad_creative: AdCreative with platform_ad_id
        google_api: GoogleAdsAPI instance

    Returns:
        Performance metrics
    """
    from app.models import AdPerformance
    from datetime import date

    if not ad_creative.platform_ad_id:
        return {"error": "Ad not published to Google"}

    # Fetch performance
    perf = google_api.get_ad_performance(
        ad_group_ad_resource_name=ad_creative.platform_ad_id,
        date_range="YESTERDAY"
    )

    if not perf:
        return {"error": "No performance data available"}

    # Save to database
    ad_perf = AdPerformance(
        ad_creative_id=ad_creative.id,
        date=date.today() - timedelta(days=1),
        impressions=perf['impressions'],
        clicks=perf['clicks'],
        conversions=int(perf['conversions']),
        spend=int(perf['cost'] * 100),  # Dollars to cents
        ctr=perf['ctr'],
        cpc=perf['average_cpc']
    )
    db.add(ad_perf)
    db.commit()

    return {
        "success": True,
        "impressions": perf['impressions'],
        "clicks": perf['clicks'],
        "conversions": int(perf['conversions']),
        "spend": f"${perf['cost']:.2f}",
        "ctr": f"{perf['ctr']:.2%}",
        "cpc": f"${perf['average_cpc']:.2f}"
    }


# ============================================================================
# HELPER: Get Google API Instance
# ============================================================================

def get_google_ads_api() -> GoogleAdsAPI:
    """
    Get configured Google Ads API instance

    Required in app/config.py:
        google_ads_developer_token: str
        google_ads_client_id: str
        google_ads_client_secret: str
        google_ads_refresh_token: str
        google_ads_customer_id: str
        google_ads_login_customer_id: str (optional, for MCC)
    """
    return GoogleAdsAPI(
        developer_token=settings.google_ads_developer_token,
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
        refresh_token=settings.google_ads_refresh_token,
        customer_id=settings.google_ads_customer_id,
        login_customer_id=settings.google_ads_login_customer_id
    )
