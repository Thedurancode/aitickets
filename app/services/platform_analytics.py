"""
Cross-Platform Page View Analytics Service

Aggregates page views and engagement metrics from multiple platforms:
- Internal platform (tickets.db)
- Eventbrite API
- Facebook Events API
- Ticketmaster API
- Generic webhook receiver for other platforms
"""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import PageView, Event
from app.config import get_settings

logger = logging.getLogger(__name__)


class PlatformAnalyticsService:
    """Service for aggregating page view analytics across multiple platforms."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def get_cross_platform_pageviews(
        self,
        event_id: int,
        days: int = 30
    ) -> Dict:
        """
        Get aggregated page views across all platforms for an event.

        Args:
            event_id: The event ID to get views for
            days: Number of days to look back (default: 30)

        Returns:
            Dictionary with total views and breakdown by platform
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Get views by platform
        platform_views = self.db.query(
            PageView.platform,
            func.count(PageView.id).label('count')
        ).filter(
            and_(
                PageView.event_id == event_id,
                PageView.created_at >= since
            )
        ).group_by(PageView.platform).all()

        by_platform = {pv.platform: pv.count for pv in platform_views}
        total_views = sum(by_platform.values())

        return {
            "event_id": event_id,
            "total_views": total_views,
            "by_platform": by_platform,
            "period_days": days,
            "last_updated": datetime.utcnow().isoformat()
        }

    def track_external_pageview(
        self,
        event_id: int,
        platform: str,
        external_platform_id: Optional[str] = None,
        platform_data: Optional[Dict] = None,
        ip_hash: str = "external",
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> PageView:
        """
        Track a page view from an external platform.

        Args:
            event_id: Internal event ID
            platform: Platform name (e.g., 'eventbrite', 'facebook', 'ticketmaster')
            external_platform_id: The event ID on the external platform
            platform_data: Additional metadata from the platform API
            ip_hash: IP hash (default: 'external' for API-sourced views)
            user_agent: User agent string if available
            referrer: Referrer URL if available

        Returns:
            Created PageView object
        """
        page_view = PageView(
            event_id=event_id,
            page="detail",
            ip_hash=ip_hash,
            platform=platform,
            external_platform_id=external_platform_id,
            platform_api_response=json.dumps(platform_data) if platform_data else None,
            user_agent=user_agent,
            referrer=referrer
        )

        self.db.add(page_view)
        self.db.commit()
        self.db.refresh(page_view)

        logger.info(f"Tracked external page view for event {event_id} from {platform}")
        return page_view

    def bulk_import_external_views(
        self,
        event_id: int,
        platform: str,
        view_count: int,
        external_platform_id: Optional[str] = None,
        platform_data: Optional[Dict] = None
    ) -> int:
        """
        Bulk import view counts from external platforms.

        Useful when platforms provide aggregate counts rather than individual views.

        Args:
            event_id: Internal event ID
            platform: Platform name
            view_count: Number of views to record
            external_platform_id: External event ID
            platform_data: Platform metadata

        Returns:
            Number of PageView records created
        """
        views_created = 0
        platform_data_str = json.dumps(platform_data) if platform_data else None

        for _ in range(view_count):
            page_view = PageView(
                event_id=event_id,
                page="detail",
                ip_hash=f"{platform}_bulk_import",
                platform=platform,
                external_platform_id=external_platform_id,
                platform_api_response=platform_data_str
            )
            self.db.add(page_view)
            views_created += 1

        self.db.commit()
        logger.info(f"Bulk imported {views_created} views for event {event_id} from {platform}")
        return views_created

    def get_platform_breakdown(
        self,
        event_id: int,
        days: int = 7
    ) -> List[Dict]:
        """
        Get detailed platform-by-platform breakdown with metadata.

        Args:
            event_id: Event ID
            days: Days to look back

        Returns:
            List of platform analytics with details
        """
        since = datetime.utcnow() - timedelta(days=days)

        platform_stats = self.db.query(
            PageView.platform,
            func.count(PageView.id).label('views'),
            func.count(func.distinct(PageView.ip_hash)).label('unique_visitors'),
            func.min(PageView.created_at).label('first_view'),
            func.max(PageView.created_at).label('last_view')
        ).filter(
            and_(
                PageView.event_id == event_id,
                PageView.created_at >= since
            )
        ).group_by(PageView.platform).all()

        return [
            {
                "platform": stat.platform,
                "views": stat.views,
                "unique_visitors": stat.unique_visitors,
                "first_view": stat.first_view.isoformat() if stat.first_view else None,
                "last_view": stat.last_view.isoformat() if stat.last_view else None,
                "avg_views_per_visitor": round(stat.views / stat.unique_visitors, 2) if stat.unique_visitors > 0 else 0
            }
            for stat in platform_stats
        ]

    def sync_eventbrite_views(
        self,
        event_id: int,
        eventbrite_event_id: str,
        api_key: Optional[str] = None
    ) -> Dict:
        """
        Sync page views from Eventbrite API.

        Note: This is a placeholder. Actual implementation requires Eventbrite API credentials.

        Args:
            event_id: Internal event ID
            eventbrite_event_id: Eventbrite event ID
            api_key: Eventbrite API key (optional, falls back to settings)

        Returns:
            Sync result with view counts
        """
        # TODO: Implement Eventbrite API integration
        # See: https://www.eventbrite.com/platform/api
        logger.warning("Eventbrite API integration not yet implemented")
        return {
            "platform": "eventbrite",
            "status": "not_implemented",
            "message": "Eventbrite API integration requires API credentials"
        }

    def sync_facebook_events(
        self,
        event_id: int,
        facebook_event_id: str,
        access_token: Optional[str] = None
    ) -> Dict:
        """
        Sync engagement metrics from Facebook Events API.

        Note: This is a placeholder. Actual implementation requires Facebook Graph API credentials.

        Args:
            event_id: Internal event ID
            facebook_event_id: Facebook event ID
            access_token: Facebook access token (optional, falls back to settings)

        Returns:
            Sync result with engagement metrics
        """
        # TODO: Implement Facebook Graph API integration
        # See: https://developers.facebook.com/docs/graph-api/reference/event/
        logger.warning("Facebook Events API integration not yet implemented")
        return {
            "platform": "facebook",
            "status": "not_implemented",
            "message": "Facebook Events API integration requires access token"
        }

    def sync_ticketmaster(
        self,
        event_id: int,
        ticketmaster_event_id: str,
        api_key: Optional[str] = None
    ) -> Dict:
        """
        Sync metrics from Ticketmaster Discovery API.

        Note: This is a placeholder. Actual implementation requires Ticketmaster API credentials.

        Args:
            event_id: Internal event ID
            ticketmaster_event_id: Ticketmaster event ID
            api_key: Ticketmaster API key (optional, falls back to settings)

        Returns:
            Sync result with metrics
        """
        # TODO: Implement Ticketmaster Discovery API integration
        # See: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
        logger.warning("Ticketmaster API integration not yet implemented")
        return {
            "platform": "ticketmaster",
            "status": "not_implemented",
            "message": "Ticketmaster API integration requires API credentials"
        }

    def get_all_platforms_summary(
        self,
        days: int = 30
    ) -> Dict:
        """
        Get summary of all events' views across all platforms.

        Args:
            days: Days to look back

        Returns:
            Platform-wide analytics summary
        """
        since = datetime.utcnow() - timedelta(days=days)

        total_views = self.db.query(func.count(PageView.id)).filter(
            PageView.created_at >= since
        ).scalar() or 0

        platform_breakdown = self.db.query(
            PageView.platform,
            func.count(PageView.id).label('count')
        ).filter(
            PageView.created_at >= since
        ).group_by(PageView.platform).all()

        by_platform = {pv.platform: pv.count for pv in platform_breakdown}

        return {
            "total_views": total_views,
            "by_platform": by_platform,
            "period_days": days,
            "platforms_tracked": len(by_platform),
            "last_updated": datetime.utcnow().isoformat()
        }


def get_platform_analytics_service(db: Session) -> PlatformAnalyticsService:
    """Factory function to get platform analytics service instance."""
    return PlatformAnalyticsService(db)
