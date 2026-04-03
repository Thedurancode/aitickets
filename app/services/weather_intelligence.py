"""
Weather Intelligence Service

Monitors weather conditions for upcoming events and generates smart alerts.
Only alerts on significant changes to reduce noise.

Features:
- Daily weather monitoring for all upcoming events
- OpenWeather API integration
- Smart change detection (only significant changes)
- Severity-based alerting
- Historical tracking for learning
- Automatic contingency plan suggestions
"""
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Event, WeatherForecast, WeatherAlert, AlertSeverity
from app.config import get_settings

logger = logging.getLogger(__name__)


class WeatherIntelligenceService:
    """Service for intelligent weather monitoring and alerting."""

    # Thresholds for significant changes (to reduce alert noise)
    TEMP_CHANGE_THRESHOLD = 10.0  # °F
    PRECIP_PROB_CHANGE_THRESHOLD = 20.0  # percentage points
    PRECIP_AMOUNT_THRESHOLD = 0.1  # inches
    WIND_SPEED_THRESHOLD = 10.0  # mph

    # Severity thresholds
    SEVERE_PRECIP_PROB = 70.0  # % - high chance of rain
    SEVERE_TEMP_LOW = 40.0  # °F - very cold
    SEVERE_TEMP_HIGH = 95.0  # °F - very hot
    SEVERE_WIND_SPEED = 25.0  # mph - strong winds

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.api_key = self.settings.openweather_api_key

    def check_weather_for_event(
        self,
        event_id: int,
        days_ahead: int = 14
    ) -> Dict:
        """
        Check weather forecast for an event and detect significant changes.

        Args:
            event_id: Event ID to check weather for
            days_ahead: How many days ahead to forecast (default: 14)

        Returns:
            Dictionary with forecast data and any alerts generated
        """
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        if not event.date:
            logger.warning(f"Event {event_id} has no date, skipping weather check")
            return {
                "status": "skipped",
                "reason": "Event has no date"
            }

        # Check if event is in the past
        event_date = event.date if isinstance(event.date, date) else event.date.date()
        if event_date < date.today():
            logger.info(f"Event {event_id} is in the past, skipping weather check")
            return {
                "status": "skipped",
                "reason": "Event is in the past"
            }

        # Check if event is too far in the future (beyond forecast range)
        days_until_event = (event_date - date.today()).days
        if days_until_event > days_ahead:
            logger.info(f"Event {event_id} is {days_until_event} days away, beyond forecast range")
            return {
                "status": "skipped",
                "reason": f"Event is {days_until_event} days away (beyond {days_ahead} day forecast)"
            }

        # Get latest forecast for this event
        previous_forecast = self.db.query(WeatherForecast).filter(
            and_(
                WeatherForecast.event_id == event_id,
                WeatherForecast.forecast_date == event_date
            )
        ).order_by(WeatherForecast.created_at.desc()).first()

        # Fetch current forecast from OpenWeather API
        new_forecast_data = self._fetch_weather_forecast(event)
        if not new_forecast_data:
            return {
                "status": "error",
                "reason": "Failed to fetch weather data from API"
            }

        # Save new forecast
        new_forecast = self._save_forecast(event_id, event_date, new_forecast_data)

        # Detect significant changes and generate alerts
        alerts = []
        if previous_forecast:
            alerts = self._detect_significant_changes(
                event_id,
                previous_forecast,
                new_forecast
            )

        return {
            "status": "success",
            "event_id": event_id,
            "event_name": event.name,
            "event_date": event_date.isoformat(),
            "days_until_event": days_until_event,
            "forecast": self._format_forecast(new_forecast),
            "alerts_generated": len(alerts),
            "alerts": [self._format_alert(alert) for alert in alerts]
        }

    def check_weather_for_all_events(self, days_ahead: int = 14) -> Dict:
        """
        Check weather for all upcoming events.

        Args:
            days_ahead: How many days ahead to forecast

        Returns:
            Summary of all weather checks
        """
        # Get all upcoming events
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)

        upcoming_events = self.db.query(Event).filter(
            and_(
                Event.date >= today,
                Event.date <= cutoff
            )
        ).all()

        results = {
            "total_events": len(upcoming_events),
            "checked": 0,
            "skipped": 0,
            "errors": 0,
            "total_alerts": 0,
            "events": []
        }

        for event in upcoming_events:
            try:
                result = self.check_weather_for_event(event.id, days_ahead)
                results["events"].append(result)

                if result["status"] == "success":
                    results["checked"] += 1
                    results["total_alerts"] += result.get("alerts_generated", 0)
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                else:
                    results["errors"] += 1

            except Exception as e:
                logger.error(f"Error checking weather for event {event.id}: {e}")
                results["errors"] += 1
                results["events"].append({
                    "status": "error",
                    "event_id": event.id,
                    "error": str(e)
                })

        return results

    def _fetch_weather_forecast(self, event: Event) -> Optional[Dict]:
        """
        Fetch weather forecast from OpenWeather API.

        Args:
            event: Event object with location data

        Returns:
            Weather data dictionary or None if failed
        """
        if not self.api_key:
            logger.error("OpenWeather API key not configured")
            return None

        # Get location from event
        location = event.location or event.venue_name
        if not location:
            logger.warning(f"Event {event.id} has no location, cannot fetch weather")
            return None

        try:
            # First, geocode the location to get coordinates
            geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
            geocode_params = {
                "q": location,
                "limit": 1,
                "appid": self.api_key
            }

            geo_response = requests.get(geocode_url, params=geocode_params, timeout=10)
            geo_response.raise_for_status()
            geo_data = geo_response.json()

            if not geo_data:
                logger.warning(f"Could not geocode location: {location}")
                return None

            lat = geo_data[0]["lat"]
            lon = geo_data[0]["lon"]

            # Fetch forecast using coordinates
            forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
            forecast_params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "imperial"  # Fahrenheit
            }

            forecast_response = requests.get(forecast_url, params=forecast_params, timeout=10)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

            # Extract weather for event date
            event_date = event.date if isinstance(event.date, date) else event.date.date()
            event_weather = self._extract_event_day_weather(forecast_data, event_date)

            return event_weather

        except requests.RequestException as e:
            logger.error(f"Error fetching weather from OpenWeather API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching weather: {e}")
            return None

    def _extract_event_day_weather(self, forecast_data: Dict, event_date: date) -> Dict:
        """
        Extract weather data for specific event date from forecast response.

        Args:
            forecast_data: OpenWeather API forecast response
            event_date: Date of the event

        Returns:
            Aggregated weather data for the event day
        """
        event_day_forecasts = []

        for item in forecast_data.get("list", []):
            forecast_time = datetime.fromtimestamp(item["dt"])
            if forecast_time.date() == event_date:
                event_day_forecasts.append(item)

        if not event_day_forecasts:
            # If no exact match, use closest available forecast
            logger.warning(f"No forecast data for {event_date}, using closest available")
            event_day_forecasts = forecast_data.get("list", [])[:8]  # First day

        # Aggregate day's weather
        temps = [f["main"]["temp"] for f in event_day_forecasts]
        precip_probs = [f.get("pop", 0) * 100 for f in event_day_forecasts]  # Convert to %

        # Calculate precipitation amount (sum of rain + snow)
        precip_amount = 0
        for f in event_day_forecasts:
            precip_amount += f.get("rain", {}).get("3h", 0)
            precip_amount += f.get("snow", {}).get("3h", 0)
        precip_amount = precip_amount / 25.4  # Convert mm to inches

        # Get most common weather condition
        conditions = [f["weather"][0]["main"] for f in event_day_forecasts]
        most_common_condition = max(set(conditions), key=conditions.count)

        # Wind speed (max)
        wind_speeds = [f["wind"]["speed"] for f in event_day_forecasts]

        # Humidity (average)
        humidity_values = [f["main"]["humidity"] for f in event_day_forecasts]

        return {
            "temperature_high": max(temps) if temps else None,
            "temperature_low": min(temps) if temps else None,
            "precipitation_probability": max(precip_probs) if precip_probs else None,
            "precipitation_amount": precip_amount,
            "conditions": most_common_condition,
            "wind_speed": max(wind_speeds) if wind_speeds else None,
            "humidity": sum(humidity_values) / len(humidity_values) if humidity_values else None,
            "api_response": forecast_data
        }

    def _save_forecast(
        self,
        event_id: int,
        forecast_date: date,
        weather_data: Dict
    ) -> WeatherForecast:
        """
        Save weather forecast to database.

        Args:
            event_id: Event ID
            forecast_date: Date being forecasted
            weather_data: Weather data from API

        Returns:
            Created WeatherForecast object
        """
        import json

        forecast = WeatherForecast(
            event_id=event_id,
            forecast_date=forecast_date,
            temperature_high=weather_data.get("temperature_high"),
            temperature_low=weather_data.get("temperature_low"),
            precipitation_probability=weather_data.get("precipitation_probability"),
            precipitation_amount=weather_data.get("precipitation_amount"),
            conditions=weather_data.get("conditions"),
            wind_speed=weather_data.get("wind_speed"),
            humidity=weather_data.get("humidity"),
            api_response=json.dumps(weather_data.get("api_response", {}))
        )

        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)

        logger.info(f"Saved weather forecast for event {event_id} on {forecast_date}")
        return forecast

    def _detect_significant_changes(
        self,
        event_id: int,
        old_forecast: WeatherForecast,
        new_forecast: WeatherForecast
    ) -> List[WeatherAlert]:
        """
        Detect significant weather changes and generate alerts.

        Only creates alerts for changes that matter (reduce noise).

        Args:
            event_id: Event ID
            old_forecast: Previous forecast
            new_forecast: Current forecast

        Returns:
            List of generated alerts
        """
        alerts = []

        # Check temperature changes
        if (old_forecast.temperature_high and new_forecast.temperature_high and
            abs(new_forecast.temperature_high - old_forecast.temperature_high) >= self.TEMP_CHANGE_THRESHOLD):

            severity = self._determine_temp_severity(new_forecast.temperature_high)
            alert = self._create_alert(
                event_id=event_id,
                alert_type="temperature_change",
                severity=severity,
                old_value=old_forecast.temperature_high,
                new_value=new_forecast.temperature_high,
                message=f"Temperature forecast changed from {old_forecast.temperature_high:.1f}°F to {new_forecast.temperature_high:.1f}°F"
            )
            alerts.append(alert)

        # Check precipitation probability changes
        if (old_forecast.precipitation_probability is not None and
            new_forecast.precipitation_probability is not None and
            abs(new_forecast.precipitation_probability - old_forecast.precipitation_probability) >= self.PRECIP_PROB_CHANGE_THRESHOLD):

            severity = self._determine_precip_severity(new_forecast.precipitation_probability)
            alert = self._create_alert(
                event_id=event_id,
                alert_type="precipitation_change",
                severity=severity,
                old_value=old_forecast.precipitation_probability,
                new_value=new_forecast.precipitation_probability,
                message=f"Chance of rain changed from {old_forecast.precipitation_probability:.0f}% to {new_forecast.precipitation_probability:.0f}%"
            )
            alerts.append(alert)

        # Check for new significant precipitation
        if (new_forecast.precipitation_amount and
            new_forecast.precipitation_amount >= self.PRECIP_AMOUNT_THRESHOLD):

            if (not old_forecast.precipitation_amount or
                old_forecast.precipitation_amount < self.PRECIP_AMOUNT_THRESHOLD):

                alert = self._create_alert(
                    event_id=event_id,
                    alert_type="precipitation_expected",
                    severity=AlertSeverity.HIGH if new_forecast.precipitation_amount > 0.5 else AlertSeverity.MEDIUM,
                    old_value=old_forecast.precipitation_amount or 0,
                    new_value=new_forecast.precipitation_amount,
                    message=f"Precipitation now expected: {new_forecast.precipitation_amount:.2f} inches"
                )
                alerts.append(alert)

        # Check wind speed changes
        if (old_forecast.wind_speed and new_forecast.wind_speed and
            abs(new_forecast.wind_speed - old_forecast.wind_speed) >= self.WIND_SPEED_THRESHOLD):

            severity = self._determine_wind_severity(new_forecast.wind_speed)
            alert = self._create_alert(
                event_id=event_id,
                alert_type="wind_change",
                severity=severity,
                old_value=old_forecast.wind_speed,
                new_value=new_forecast.wind_speed,
                message=f"Wind speed forecast changed from {old_forecast.wind_speed:.1f} mph to {new_forecast.wind_speed:.1f} mph"
            )
            alerts.append(alert)

        # Check for severe weather conditions
        if new_forecast.conditions in ["Thunderstorm", "Snow", "Extreme"]:
            if old_forecast.conditions != new_forecast.conditions:
                alert = self._create_alert(
                    event_id=event_id,
                    alert_type="severe_weather",
                    severity=AlertSeverity.CRITICAL,
                    old_value=None,
                    new_value=None,
                    message=f"Severe weather alert: {new_forecast.conditions} conditions forecasted"
                )
                alerts.append(alert)

        return alerts

    def _create_alert(
        self,
        event_id: int,
        alert_type: str,
        severity: AlertSeverity,
        old_value: Optional[float],
        new_value: Optional[float],
        message: str
    ) -> WeatherAlert:
        """
        Create and save a weather alert.

        Args:
            event_id: Event ID
            alert_type: Type of alert
            severity: Alert severity
            old_value: Previous value
            new_value: New value
            message: Alert message

        Returns:
            Created WeatherAlert object
        """
        alert = WeatherAlert(
            event_id=event_id,
            alert_type=alert_type,
            severity=severity,
            old_value=old_value,
            new_value=new_value,
            message=message,
            notified=False
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Created {severity.value} weather alert for event {event_id}: {message}")
        return alert

    def _determine_temp_severity(self, temp: float) -> AlertSeverity:
        """Determine severity based on temperature."""
        if temp <= self.SEVERE_TEMP_LOW or temp >= self.SEVERE_TEMP_HIGH:
            return AlertSeverity.HIGH
        elif temp <= 50 or temp >= 85:
            return AlertSeverity.MEDIUM
        return AlertSeverity.LOW

    def _determine_precip_severity(self, precip_prob: float) -> AlertSeverity:
        """Determine severity based on precipitation probability."""
        if precip_prob >= self.SEVERE_PRECIP_PROB:
            return AlertSeverity.HIGH
        elif precip_prob >= 40:
            return AlertSeverity.MEDIUM
        return AlertSeverity.LOW

    def _determine_wind_severity(self, wind_speed: float) -> AlertSeverity:
        """Determine severity based on wind speed."""
        if wind_speed >= self.SEVERE_WIND_SPEED:
            return AlertSeverity.HIGH
        elif wind_speed >= 15:
            return AlertSeverity.MEDIUM
        return AlertSeverity.LOW

    def _format_forecast(self, forecast: WeatherForecast) -> Dict:
        """Format forecast for API response."""
        return {
            "date": forecast.forecast_date.isoformat(),
            "temperature": {
                "high": forecast.temperature_high,
                "low": forecast.temperature_low
            },
            "precipitation": {
                "probability": forecast.precipitation_probability,
                "amount": forecast.precipitation_amount
            },
            "conditions": forecast.conditions,
            "wind_speed": forecast.wind_speed,
            "humidity": forecast.humidity,
            "created_at": forecast.created_at.isoformat()
        }

    def _format_alert(self, alert: WeatherAlert) -> Dict:
        """Format alert for API response."""
        return {
            "id": alert.id,
            "type": alert.alert_type,
            "severity": alert.severity.value,
            "message": alert.message,
            "old_value": alert.old_value,
            "new_value": alert.new_value,
            "created_at": alert.created_at.isoformat(),
            "notified": alert.notified
        }

    def get_weather_forecast(self, event_id: int) -> Optional[Dict]:
        """
        Get latest weather forecast for an event.

        Args:
            event_id: Event ID

        Returns:
            Formatted forecast or None
        """
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event or not event.date:
            return None

        event_date = event.date if isinstance(event.date, date) else event.date.date()

        forecast = self.db.query(WeatherForecast).filter(
            and_(
                WeatherForecast.event_id == event_id,
                WeatherForecast.forecast_date == event_date
            )
        ).order_by(WeatherForecast.created_at.desc()).first()

        if not forecast:
            return None

        return self._format_forecast(forecast)

    def get_weather_alerts(
        self,
        event_id: Optional[int] = None,
        severity: Optional[AlertSeverity] = None,
        unnotified_only: bool = False
    ) -> List[Dict]:
        """
        Get weather alerts with optional filtering.

        Args:
            event_id: Filter by event ID (optional)
            severity: Filter by severity (optional)
            unnotified_only: Only return unnotified alerts

        Returns:
            List of formatted alerts
        """
        query = self.db.query(WeatherAlert)

        if event_id:
            query = query.filter(WeatherAlert.event_id == event_id)

        if severity:
            query = query.filter(WeatherAlert.severity == severity)

        if unnotified_only:
            query = query.filter(WeatherAlert.notified == False)

        alerts = query.order_by(WeatherAlert.created_at.desc()).all()
        return [self._format_alert(alert) for alert in alerts]

    def mark_alerts_notified(self, alert_ids: List[int]) -> int:
        """
        Mark alerts as notified.

        Args:
            alert_ids: List of alert IDs to mark

        Returns:
            Number of alerts marked
        """
        count = self.db.query(WeatherAlert).filter(
            WeatherAlert.id.in_(alert_ids)
        ).update({"notified": True}, synchronize_session=False)

        self.db.commit()
        logger.info(f"Marked {count} weather alerts as notified")
        return count


def get_weather_intelligence_service(db: Session) -> WeatherIntelligenceService:
    """Factory function to get weather intelligence service instance."""
    return WeatherIntelligenceService(db)
