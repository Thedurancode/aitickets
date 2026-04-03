"""
Weather Intelligence API Endpoints

REST API for weather monitoring, forecasts, and alerts.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from app.database import get_db
from app.models import Event, AlertSeverity
from app.services.weather_intelligence import get_weather_intelligence_service


router = APIRouter(prefix="/api/weather", tags=["Weather Intelligence"])


@router.get("/events/{event_id}/forecast", response_model=Dict)
def get_event_weather_forecast(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get latest weather forecast for an event.

    Returns:
    - Forecast data with temperature, precipitation, wind, etc.
    - Returns 404 if no forecast exists yet
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    service = get_weather_intelligence_service(db)
    forecast = service.get_weather_forecast(event_id)

    if not forecast:
        raise HTTPException(
            status_code=404,
            detail="No weather forecast available. Run weather check first."
        )

    return {
        "event_id": event_id,
        "event_name": event.name,
        "forecast": forecast
    }


@router.post("/events/{event_id}/check", response_model=Dict)
def check_event_weather(
    event_id: int,
    days_ahead: int = Query(default=14, ge=1, le=30, description="Forecast days ahead"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger weather check for a specific event.

    - Fetches latest forecast from OpenWeather API
    - Detects significant changes vs previous forecast
    - Generates alerts if needed
    - Returns forecast and any alerts generated
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    service = get_weather_intelligence_service(db)

    try:
        result = service.check_weather_for_event(event_id, days_ahead)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking weather: {str(e)}"
        )


@router.post("/check-all", response_model=Dict)
def check_all_events_weather(
    background_tasks: BackgroundTasks,
    days_ahead: int = Query(default=14, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Check weather for ALL upcoming events.

    - Processes all events with dates in the next {days_ahead} days
    - Generates alerts for significant changes
    - Returns summary of checks performed

    Note: This can be run as a background task for scheduled daily checks.
    """
    service = get_weather_intelligence_service(db)

    try:
        result = service.check_weather_for_all_events(days_ahead)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking weather for all events: {str(e)}"
        )


@router.get("/events/{event_id}/alerts", response_model=List[Dict])
def get_event_weather_alerts(
    event_id: int,
    severity: Optional[str] = Query(default=None, description="Filter by severity: low, medium, high, critical"),
    unnotified_only: bool = Query(default=False, description="Only show unnotified alerts"),
    db: Session = Depends(get_db)
):
    """
    Get weather alerts for a specific event.

    Returns list of alerts with:
    - Alert type (temperature_change, precipitation_change, etc.)
    - Severity (low, medium, high, critical)
    - Message describing the change
    - Old and new values
    - Notification status
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Parse severity filter
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity[severity.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: low, medium, high, critical"
            )

    service = get_weather_intelligence_service(db)
    alerts = service.get_weather_alerts(
        event_id=event_id,
        severity=severity_enum,
        unnotified_only=unnotified_only
    )

    return alerts


@router.get("/alerts", response_model=List[Dict])
def get_all_weather_alerts(
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    unnotified_only: bool = Query(default=False, description="Only unnotified alerts"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get weather alerts across all events.

    Useful for:
    - Daily digest generation
    - Dashboard alert feed
    - Notification systems
    """
    # Parse severity filter
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity[severity.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: low, medium, high, critical"
            )

    service = get_weather_intelligence_service(db)
    alerts = service.get_weather_alerts(
        severity=severity_enum,
        unnotified_only=unnotified_only
    )

    # Apply limit
    return alerts[:limit]


@router.post("/alerts/mark-notified", response_model=Dict)
def mark_alerts_notified(
    alert_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Mark weather alerts as notified.

    Used after sending notifications to users to prevent duplicate alerts.
    """
    if not alert_ids:
        raise HTTPException(status_code=400, detail="alert_ids cannot be empty")

    service = get_weather_intelligence_service(db)
    count = service.mark_alerts_notified(alert_ids)

    return {
        "success": True,
        "marked_count": count,
        "alert_ids": alert_ids
    }


@router.get("/summary", response_model=Dict)
def get_weather_summary(
    days_ahead: int = Query(default=14, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get summary of weather monitoring status.

    Returns:
    - Number of events being monitored
    - Total alerts (by severity)
    - Events with critical weather warnings
    """
    from app.models import WeatherAlert
    from sqlalchemy import func, and_
    from datetime import date, timedelta

    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    # Count upcoming events
    upcoming_events = db.query(func.count(Event.id)).filter(
        and_(
            Event.date >= today,
            Event.date <= cutoff
        )
    ).scalar() or 0

    # Count alerts by severity
    alert_counts = db.query(
        WeatherAlert.severity,
        func.count(WeatherAlert.id).label('count')
    ).join(Event).filter(
        and_(
            Event.date >= today,
            Event.date <= cutoff
        )
    ).group_by(WeatherAlert.severity).all()

    by_severity = {severity.value: 0 for severity in AlertSeverity}
    for severity, count in alert_counts:
        by_severity[severity.value] = count

    total_alerts = sum(by_severity.values())

    # Get critical alerts
    service = get_weather_intelligence_service(db)
    critical_alerts = service.get_weather_alerts(
        severity=AlertSeverity.CRITICAL,
        unnotified_only=False
    )

    return {
        "upcoming_events": upcoming_events,
        "total_alerts": total_alerts,
        "alerts_by_severity": by_severity,
        "critical_alerts": len(critical_alerts),
        "monitoring_period_days": days_ahead
    }
