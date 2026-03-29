"""
Real-Time Analytics Dashboard API

Provides comprehensive metrics and visualizations for:
- Campaign performance
- Alert activity
- Revenue trends
- Event performance
- Real-time updates via SSE
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Optional, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    Campaign, CampaignDelivery, CampaignType,
    Alert, AlertSeverity,
    Event, Ticket, EventGoer,
    ConversionTracking
)
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Store active SSE connections for real-time metrics
active_metric_streams: set[asyncio.Queue] = set()


# Pydantic schemas
class DashboardMetrics(BaseModel):
    """Overall dashboard metrics."""
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    tickets_sold_today: int
    tickets_sold_this_week: int
    tickets_sold_this_month: int
    active_campaigns: int
    unread_alerts: int
    critical_alerts: int
    conversion_rate: float


class CampaignPerformance(BaseModel):
    """Campaign performance summary."""
    campaign_id: int
    name: str
    type: str
    sent: int
    opened: int
    clicked: int
    converted: int
    revenue: float
    open_rate: float
    click_rate: float
    conversion_rate: float


class AlertActivity(BaseModel):
    """Alert activity summary."""
    total_alerts: int
    unread_alerts: int
    by_severity: Dict[str, int]
    recent_alerts: List[Dict]


class RevenueChart(BaseModel):
    """Revenue trend data for charts."""
    labels: List[str]
    revenue: List[float]
    tickets: List[int]


def format_sse_message(event: str, data: dict) -> str:
    """Format data as Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


# ============== Dashboard Metrics ==============

@router.get("/metrics", response_model=DashboardMetrics)
@limiter.limit("60/minute")
async def get_dashboard_metrics(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get overall dashboard metrics.

    **Returns:**
    - Revenue (today, this week, this month)
    - Tickets sold (today, this week, this month)
    - Active campaigns count
    - Unread alerts count
    - Critical alerts count
    - Overall conversion rate
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # Revenue calculations
    revenue_today = db.query(func.sum(Ticket.price_cents)).filter(
        Ticket.created_at >= today_start
    ).scalar() or 0

    revenue_week = db.query(func.sum(Ticket.price_cents)).filter(
        Ticket.created_at >= week_start
    ).scalar() or 0

    revenue_month = db.query(func.sum(Ticket.price_cents)).filter(
        Ticket.created_at >= month_start
    ).scalar() or 0

    # Tickets sold
    tickets_today = db.query(Ticket).filter(Ticket.created_at >= today_start).count()
    tickets_week = db.query(Ticket).filter(Ticket.created_at >= week_start).count()
    tickets_month = db.query(Ticket).filter(Ticket.created_at >= month_start).count()

    # Active campaigns (created in last 30 days)
    active_campaigns = db.query(Campaign).filter(
        Campaign.created_at >= now - timedelta(days=30)
    ).count()

    # Alerts
    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()
    critical_alerts = db.query(Alert).filter(
        and_(Alert.is_read == False, Alert.severity == AlertSeverity.CRITICAL)
    ).count()

    # Conversion rate (tickets / unique visitors)
    total_visits = db.query(ConversionTracking).count()
    total_conversions = db.query(ConversionTracking).filter(
        ConversionTracking.converted == True
    ).count()
    conversion_rate = (total_conversions / total_visits * 100) if total_visits > 0 else 0

    return DashboardMetrics(
        revenue_today=revenue_today / 100.0,
        revenue_this_week=revenue_week / 100.0,
        revenue_this_month=revenue_month / 100.0,
        tickets_sold_today=tickets_today,
        tickets_sold_this_week=tickets_week,
        tickets_sold_this_month=tickets_month,
        active_campaigns=active_campaigns,
        unread_alerts=unread_alerts,
        critical_alerts=critical_alerts,
        conversion_rate=round(conversion_rate, 2),
    )


# ============== Campaign Performance ==============

@router.get("/campaigns/performance", response_model=List[CampaignPerformance])
@limiter.limit("60/minute")
async def get_campaign_performance(
    request: Request,
    days: int = Query(30, le=365),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """
    Get top performing campaigns.

    **Query Parameters:**
    - `days`: Time period to analyze (default 30, max 365)
    - `limit`: Number of campaigns to return (default 10, max 50)

    **Returns:** List of campaigns sorted by revenue (highest first)
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    campaigns = (
        db.query(Campaign)
        .filter(Campaign.created_at >= since)
        .order_by(Campaign.revenue_cents.desc())
        .limit(limit)
        .all()
    )

    result = []
    for c in campaigns:
        open_rate = (c.opened_count / c.delivered_count * 100) if c.delivered_count > 0 else 0
        click_rate = (c.clicked_count / c.opened_count * 100) if c.opened_count > 0 else 0
        conversion_rate = (c.converted_count / c.clicked_count * 100) if c.clicked_count > 0 else 0

        result.append(CampaignPerformance(
            campaign_id=c.id,
            name=c.name,
            type=c.campaign_type.value,
            sent=c.sent_count,
            opened=c.opened_count,
            clicked=c.clicked_count,
            converted=c.converted_count,
            revenue=c.revenue_cents / 100.0,
            open_rate=round(open_rate, 2),
            click_rate=round(click_rate, 2),
            conversion_rate=round(conversion_rate, 2),
        ))

    return result


# ============== Alert Activity ==============

@router.get("/alerts/activity", response_model=AlertActivity)
@limiter.limit("60/minute")
async def get_alert_activity(
    request: Request,
    days: int = Query(7, le=90),
    db: Session = Depends(get_db),
):
    """
    Get alert activity summary.

    **Query Parameters:**
    - `days`: Time period to analyze (default 7, max 90)

    **Returns:**
    - Total alerts count
    - Unread alerts count
    - Alerts by severity breakdown
    - Recent alerts (last 10)
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_alerts = db.query(Alert).filter(Alert.created_at >= since).count()
    unread_alerts = db.query(Alert).filter(
        and_(Alert.created_at >= since, Alert.is_read == False)
    ).count()

    # By severity
    by_severity = {}
    for severity in AlertSeverity:
        count = db.query(Alert).filter(
            and_(Alert.created_at >= since, Alert.severity == severity)
        ).count()
        by_severity[severity.value] = count

    # Recent alerts
    recent = (
        db.query(Alert)
        .filter(Alert.created_at >= since)
        .order_by(Alert.created_at.desc())
        .limit(10)
        .all()
    )

    recent_alerts = [
        {
            "id": a.id,
            "title": a.title,
            "severity": a.severity.value if hasattr(a.severity, "value") else a.severity,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat(),
        }
        for a in recent
    ]

    return AlertActivity(
        total_alerts=total_alerts,
        unread_alerts=unread_alerts,
        by_severity=by_severity,
        recent_alerts=recent_alerts,
    )


# ============== Revenue Charts ==============

@router.get("/revenue/daily", response_model=RevenueChart)
@limiter.limit("60/minute")
async def get_daily_revenue(
    request: Request,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
):
    """
    Get daily revenue trend data for charts.

    **Query Parameters:**
    - `days`: Number of days to include (default 30, max 365)

    **Returns:**
    - labels: List of dates
    - revenue: Revenue per day
    - tickets: Tickets sold per day
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # Query daily aggregates
    daily_data = (
        db.query(
            func.date(Ticket.created_at).label('date'),
            func.sum(Ticket.price_cents).label('revenue'),
            func.count(Ticket.id).label('tickets'),
        )
        .filter(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
        .all()
    )

    labels = []
    revenue = []
    tickets = []

    for row in daily_data:
        labels.append(row.date.strftime('%Y-%m-%d'))
        revenue.append((row.revenue or 0) / 100.0)
        tickets.append(row.tickets or 0)

    return RevenueChart(
        labels=labels,
        revenue=revenue,
        tickets=tickets,
    )


@router.get("/revenue/hourly")
@limiter.limit("60/minute")
async def get_hourly_revenue(
    request: Request,
    hours: int = Query(24, le=168),
    db: Session = Depends(get_db),
):
    """
    Get hourly revenue trend (last 24 hours by default).

    **Query Parameters:**
    - `hours`: Number of hours to include (default 24, max 168)

    **Returns:** Hourly revenue and ticket sales data
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)

    # Query hourly aggregates
    hourly_data = (
        db.query(
            func.date_trunc('hour', Ticket.created_at).label('hour'),
            func.sum(Ticket.price_cents).label('revenue'),
            func.count(Ticket.id).label('tickets'),
        )
        .filter(Ticket.created_at >= since)
        .group_by(func.date_trunc('hour', Ticket.created_at))
        .order_by(func.date_trunc('hour', Ticket.created_at))
        .all()
    )

    labels = []
    revenue = []
    tickets = []

    for row in hourly_data:
        labels.append(row.hour.strftime('%Y-%m-%d %H:%M'))
        revenue.append((row.revenue or 0) / 100.0)
        tickets.append(row.tickets or 0)

    return {
        "labels": labels,
        "revenue": revenue,
        "tickets": tickets,
    }


# ============== Event Performance ==============

@router.get("/events/top-performing")
@limiter.limit("60/minute")
async def get_top_events(
    request: Request,
    days: int = Query(30, le=365),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """
    Get top performing events by ticket sales.

    **Query Parameters:**
    - `days`: Time period to analyze (default 30, max 365)
    - `limit`: Number of events to return (default 10, max 50)

    **Returns:** List of events sorted by revenue
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Aggregate ticket sales per event
    event_stats = (
        db.query(
            Event.id,
            Event.name,
            func.count(Ticket.id).label('tickets_sold'),
            func.sum(Ticket.price_cents).label('revenue'),
        )
        .join(Ticket, Ticket.event_id == Event.id)
        .filter(Ticket.created_at >= since)
        .group_by(Event.id, Event.name)
        .order_by(func.sum(Ticket.price_cents).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "event_id": row.id,
            "event_name": row.name,
            "tickets_sold": row.tickets_sold,
            "revenue": (row.revenue or 0) / 100.0,
        }
        for row in event_stats
    ]


# ============== Real-Time Metrics Stream ==============

async def metrics_stream_generator(
    request: Request,
    db: Session,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE stream of real-time dashboard metrics.

    Updates every 10 seconds with latest metrics.
    """
    queue: asyncio.Queue = asyncio.Queue()
    active_metric_streams.add(queue)

    try:
        # Send initial metrics
        initial_metrics = await get_dashboard_metrics(request, db)
        yield format_sse_message("metrics", initial_metrics.dict())

        # Send connected confirmation
        yield format_sse_message("connected", {
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep connection alive and send updates
        while True:
            if await request.is_disconnected():
                logger.info("Metrics stream client disconnected")
                break

            try:
                # Wait for updates (with timeout for periodic refresh)
                update = await asyncio.wait_for(queue.get(), timeout=10.0)
                yield format_sse_message("metrics", update)
            except asyncio.TimeoutError:
                # Periodic refresh - send latest metrics
                current_metrics = await get_dashboard_metrics(request, db)
                yield format_sse_message("metrics", current_metrics.dict())

                # Send heartbeat
                yield format_sse_message("heartbeat", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    finally:
        # Clean up connection
        active_metric_streams.discard(queue)
        logger.info(f"Metrics stream closed. Active: {len(active_metric_streams)}")


@router.get("/metrics/stream")
@limiter.limit("10/minute")
async def stream_metrics(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Real-time metrics stream via Server-Sent Events.

    Updates dashboard metrics every 10 seconds automatically.

    **Usage:**
    ```javascript
    const eventSource = new EventSource('/api/dashboard/metrics/stream');

    eventSource.addEventListener('metrics', (event) => {
        const metrics = JSON.parse(event.data);
        updateDashboard(metrics);
    });

    eventSource.addEventListener('connected', (event) => {
        console.log('Connected to metrics stream');
    });
    ```

    **Events:**
    - `metrics` - Updated metrics (every 10s)
    - `connected` - Initial connection established
    - `heartbeat` - Keep-alive ping
    """
    return StreamingResponse(
        metrics_stream_generator(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def broadcast_metric_update(metrics: Dict):
    """
    Broadcast metric update to all connected dashboard clients.

    Call this when significant events occur (new sale, new alert, etc.)
    """
    if not active_metric_streams:
        return

    for queue in active_metric_streams:
        try:
            queue.put_nowait(metrics)
        except asyncio.QueueFull:
            logger.warning("Metrics queue full, dropping update")


@router.get("/stats")
async def get_stream_stats():
    """Get dashboard stream statistics."""
    return {
        "active_metric_streams": len(active_metric_streams),
        "status": "operational",
    }
