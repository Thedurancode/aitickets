"""
Cross-Platform Ecosystem Intelligence
Aggregates intelligence from multiple platforms to make smarter decisions
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import aiohttp

from sqlalchemy.orm import Session
from app.models import Event, Artist, ArtistResearch
from app.config import get_settings


class PlatformSource(str, Enum):
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    TICKETMASTER = "ticketmaster"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    GOOGLE_TRENDS = "google_trends"
    WEATHER = "weather"
    TRAFFIC = "traffic"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    REDDIT = "reddit"
    NEWS = "news"


@dataclass
class PlatformSignal:
    """Signal from a platform"""
    source: PlatformSource
    signal_type: str  # trending, declining, stable, spike
    strength: float  # 0-1
    data: Dict
    timestamp: datetime
    confidence: float = 1.0


@dataclass
class EcosystemInsight:
    """Aggregated insight from multiple platforms"""
    insight_type: str
    recommendation: str
    confidence: float
    supporting_signals: List[PlatformSignal]
    impact_prediction: Dict
    timestamp: datetime


class PlatformConnector:
    """Base connector for platform integrations"""

    def __init__(self, platform: PlatformSource):
        self.platform = platform
        self.settings = get_settings()

    async def fetch_signals(self, query: str) -> Optional[PlatformSignal]:
        """Fetch signals from platform"""
        raise NotImplementedError


class SpotifyConnector(PlatformConnector):
    """Spotify platform connector"""

    def __init__(self):
        super().__init__(PlatformSource.SPOTIFY)

    async def fetch_signals(self, artist_name: str) -> Optional[PlatformSignal]:
        """Fetch Spotify signals for artist"""
        # In production, would use actual Spotify API
        # Simulating for demonstration

        signal = PlatformSignal(
            source=self.platform,
            signal_type="trending",
            strength=0.75,
            data={
                "monthly_listeners": 5000000,
                "monthly_growth": 0.15,  # 15% growth
                "viral_tracks": 2,
                "playlist_adds": 450,
                "popularity_score": 72
            },
            timestamp=datetime.utcnow(),
            confidence=0.9
        )

        return signal

    async def get_momentum_score(self, artist_name: str) -> float:
        """Calculate artist momentum on Spotify"""
        signal = await self.fetch_signals(artist_name)
        if not signal:
            return 0.0

        # Calculate momentum based on growth and virality
        growth = signal.data.get("monthly_growth", 0)
        viral = signal.data.get("viral_tracks", 0) / 10  # Normalize
        playlists = min(signal.data.get("playlist_adds", 0) / 1000, 1)  # Normalize

        momentum = (growth * 0.4) + (viral * 0.3) + (playlists * 0.3)
        return min(momentum, 1.0)


class TikTokConnector(PlatformConnector):
    """TikTok platform connector"""

    def __init__(self):
        super().__init__(PlatformSource.TIKTOK)

    async def fetch_signals(self, query: str) -> Optional[PlatformSignal]:
        """Fetch TikTok trending signals"""
        # Simulating TikTok API response

        signal = PlatformSignal(
            source=self.platform,
            signal_type="spike",
            strength=0.85,
            data={
                "hashtag_views": 25000000,
                "videos_created": 5000,
                "engagement_rate": 0.12,
                "trend_velocity": "explosive",
                "demographic": {"age_18_24": 0.6, "age_25_34": 0.3}
            },
            timestamp=datetime.utcnow(),
            confidence=0.85
        )

        return signal


class TicketmasterConnector(PlatformConnector):
    """Ticketmaster competitor intelligence"""

    def __init__(self):
        super().__init__(PlatformSource.TICKETMASTER)

    async def fetch_signals(self, event_type: str, location: str) -> Optional[PlatformSignal]:
        """Fetch competitor pricing and availability"""
        # Simulating competitor data

        signal = PlatformSignal(
            source=self.platform,
            signal_type="market_data",
            strength=0.7,
            data={
                "similar_events": 5,
                "avg_price": 65,
                "price_range": [45, 120],
                "sellout_rate": 0.7,
                "days_to_sellout": 12,
                "competitor_marketing": "heavy"
            },
            timestamp=datetime.utcnow(),
            confidence=0.8
        )

        return signal


class GoogleTrendsConnector(PlatformConnector):
    """Google Trends search data"""

    def __init__(self):
        super().__init__(PlatformSource.GOOGLE_TRENDS)

    async def fetch_signals(self, query: str) -> Optional[PlatformSignal]:
        """Fetch Google Trends data"""
        # Simulating Google Trends

        signal = PlatformSignal(
            source=self.platform,
            signal_type="search_interest",
            strength=0.65,
            data={
                "interest_over_time": [45, 48, 52, 61, 73, 89],  # Last 6 weeks
                "trend_direction": "rising",
                "related_queries": ["tour dates", "tickets", "new album"],
                "geographic_interest": {"Austin": 85, "Houston": 72, "Dallas": 68},
                "search_volume_increase": 0.98  # 98% increase
            },
            timestamp=datetime.utcnow(),
            confidence=0.9
        )

        return signal


class InstagramConnector(PlatformConnector):
    """Instagram social signals"""

    def __init__(self):
        super().__init__(PlatformSource.INSTAGRAM)

    async def fetch_signals(self, hashtag: str) -> Optional[PlatformSignal]:
        """Fetch Instagram engagement signals"""
        # Simulating Instagram data

        signal = PlatformSignal(
            source=self.platform,
            signal_type="social_engagement",
            strength=0.72,
            data={
                "posts_last_week": 2500,
                "total_engagement": 450000,
                "avg_likes": 180,
                "avg_comments": 25,
                "influencer_mentions": 12,
                "story_mentions": 8500,
                "reels_created": 350
            },
            timestamp=datetime.utcnow(),
            confidence=0.85
        )

        return signal


class WeatherConnector(PlatformConnector):
    """Weather intelligence for event planning"""

    def __init__(self):
        super().__init__(PlatformSource.WEATHER)

    async def fetch_signals(self, location: str, date: str) -> Optional[PlatformSignal]:
        """Fetch weather predictions"""
        # Simulating weather API

        signal = PlatformSignal(
            source=self.platform,
            signal_type="weather_forecast",
            strength=0.9,
            data={
                "temperature": 75,
                "precipitation_chance": 0.1,
                "conditions": "clear",
                "wind_speed": 5,
                "humidity": 0.6,
                "comfort_index": 0.85,
                "outdoor_favorability": 0.9
            },
            timestamp=datetime.utcnow(),
            confidence=0.75  # Weather predictions lose confidence over time
        )

        return signal


class NewsConnector(PlatformConnector):
    """News and media sentiment"""

    def __init__(self):
        super().__init__(PlatformSource.NEWS)

    async def fetch_signals(self, query: str) -> Optional[PlatformSignal]:
        """Fetch news sentiment and coverage"""
        # Simulating news analysis

        signal = PlatformSignal(
            source=self.platform,
            signal_type="media_coverage",
            strength=0.68,
            data={
                "articles_last_week": 15,
                "sentiment_score": 0.72,  # Positive
                "reach": 2500000,
                "top_outlets": ["Billboard", "Rolling Stone", "Complex"],
                "topics": ["new tour", "album release", "collaboration"],
                "controversy_score": 0.1  # Low controversy
            },
            timestamp=datetime.utcnow(),
            confidence=0.8
        )

        return signal


class EcosystemIntelligence:
    """Main ecosystem intelligence aggregator"""

    def __init__(self, db: Session):
        self.db = db
        self.connectors = {
            PlatformSource.SPOTIFY: SpotifyConnector(),
            PlatformSource.TIKTOK: TikTokConnector(),
            PlatformSource.TICKETMASTER: TicketmasterConnector(),
            PlatformSource.GOOGLE_TRENDS: GoogleTrendsConnector(),
            PlatformSource.INSTAGRAM: InstagramConnector(),
            PlatformSource.WEATHER: WeatherConnector(),
            PlatformSource.NEWS: NewsConnector()
        }
        self.insights: List[EcosystemInsight] = []

    async def gather_all_signals(self, query: str, location: str = None, date: str = None) -> Dict[PlatformSource, PlatformSignal]:
        """Gather signals from all platforms"""
        signals = {}

        # Gather from each platform in parallel
        tasks = []
        for source, connector in self.connectors.items():
            if source == PlatformSource.WEATHER and location and date:
                tasks.append(connector.fetch_signals(location, date))
            elif source == PlatformSource.TICKETMASTER and location:
                tasks.append(connector.fetch_signals(query, location))
            else:
                tasks.append(connector.fetch_signals(query))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for source, result in zip(self.connectors.keys(), results):
            if not isinstance(result, Exception) and result:
                signals[source] = result

        return signals

    def analyze_signals(self, signals: Dict[PlatformSource, PlatformSignal]) -> EcosystemInsight:
        """Analyze all signals and generate insight"""

        # Calculate weighted confidence
        total_strength = 0
        total_confidence = 0
        signal_count = 0

        trending_platforms = []
        declining_platforms = []

        for source, signal in signals.items():
            total_strength += signal.strength
            total_confidence += signal.confidence
            signal_count += 1

            if signal.signal_type in ["trending", "spike"]:
                trending_platforms.append(source)
            elif signal.signal_type == "declining":
                declining_platforms.append(source)

        avg_strength = total_strength / signal_count if signal_count > 0 else 0
        avg_confidence = total_confidence / signal_count if signal_count > 0 else 0

        # Generate recommendation based on signals
        if len(trending_platforms) >= 4 and avg_strength > 0.7:
            insight_type = "strong_opportunity"
            recommendation = "IMMEDIATE ACTION: Strong signals across multiple platforms. Book now before prices increase."
            impact = {"revenue_multiplier": 1.5, "sellout_probability": 0.85}
        elif len(trending_platforms) >= 2 and avg_strength > 0.5:
            insight_type = "growing_opportunity"
            recommendation = "GOOD OPPORTUNITY: Positive signals detected. Consider booking within 2 weeks."
            impact = {"revenue_multiplier": 1.2, "sellout_probability": 0.6}
        elif len(declining_platforms) >= 2:
            insight_type = "declining_interest"
            recommendation = "CAUTION: Declining interest detected. Consider postponing or reducing scale."
            impact = {"revenue_multiplier": 0.8, "sellout_probability": 0.3}
        else:
            insight_type = "stable"
            recommendation = "STABLE: Normal market conditions. Proceed with standard approach."
            impact = {"revenue_multiplier": 1.0, "sellout_probability": 0.5}

        insight = EcosystemInsight(
            insight_type=insight_type,
            recommendation=recommendation,
            confidence=avg_confidence,
            supporting_signals=list(signals.values()),
            impact_prediction=impact,
            timestamp=datetime.utcnow()
        )

        self.insights.append(insight)
        return insight

    async def get_pricing_recommendation(self, event_type: str, location: str, artist: str = None) -> Dict:
        """Get pricing recommendation based on ecosystem data"""
        signals = await self.gather_all_signals(artist or event_type, location)

        # Get competitor pricing
        ticketmaster_signal = signals.get(PlatformSource.TICKETMASTER)
        competitor_avg = ticketmaster_signal.data.get("avg_price", 50) if ticketmaster_signal else 50

        # Adjust based on momentum
        momentum_multiplier = 1.0

        if PlatformSource.SPOTIFY in signals:
            spotify_momentum = await self.connectors[PlatformSource.SPOTIFY].get_momentum_score(artist)
            momentum_multiplier += (spotify_momentum * 0.3)

        if PlatformSource.TIKTOK in signals:
            tiktok_strength = signals[PlatformSource.TIKTOK].strength
            momentum_multiplier += (tiktok_strength * 0.2)

        if PlatformSource.GOOGLE_TRENDS in signals:
            search_increase = signals[PlatformSource.GOOGLE_TRENDS].data.get("search_volume_increase", 0)
            momentum_multiplier += (search_increase * 0.1)

        recommended_price = competitor_avg * momentum_multiplier

        return {
            "competitor_average": competitor_avg,
            "momentum_multiplier": momentum_multiplier,
            "recommended_price": round(recommended_price, 0),
            "price_range": [
                round(recommended_price * 0.8, 0),
                round(recommended_price * 1.2, 0)
            ],
            "confidence": 0.75,
            "reasoning": f"Based on {len(signals)} platform signals with momentum factor of {momentum_multiplier:.2f}"
        }

    async def predict_optimal_date(self, event_type: str, location: str, date_range: List[str]) -> Dict:
        """Predict optimal date for event based on multiple factors"""
        date_scores = {}

        for date in date_range:
            # Get weather signal
            weather_signal = await self.connectors[PlatformSource.WEATHER].fetch_signals(location, date)
            weather_score = weather_signal.data.get("outdoor_favorability", 0.5) if weather_signal else 0.5

            # Check competitor events (would need real implementation)
            competition_score = 0.7  # Simulated - less competition = higher score

            # Day of week score
            from datetime import datetime as dt
            date_obj = dt.strptime(date, "%Y-%m-%d")
            day_name = date_obj.strftime("%A")
            day_score = 0.9 if day_name in ["Friday", "Saturday"] else 0.6 if day_name == "Thursday" else 0.4

            # Combined score
            total_score = (weather_score * 0.3) + (competition_score * 0.4) + (day_score * 0.3)
            date_scores[date] = {
                "score": total_score,
                "weather": weather_score,
                "competition": competition_score,
                "day_of_week": day_score,
                "day_name": day_name
            }

        # Find best date
        best_date = max(date_scores.keys(), key=lambda d: date_scores[d]["score"])

        return {
            "recommended_date": best_date,
            "score": date_scores[best_date]["score"],
            "all_dates": date_scores,
            "reasoning": f"Best combination of weather, low competition, and favorable day of week"
        }

    async def monitor_real_time(self, event_id: int) -> List[Dict]:
        """Monitor real-time signals for active event"""
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return []

        alerts = []

        # Get current signals
        artist_name = event.artist.name if event.artist else event.name
        signals = await self.gather_all_signals(artist_name)

        # Check for sudden spikes
        for source, signal in signals.items():
            if signal.signal_type == "spike" and signal.strength > 0.8:
                alerts.append({
                    "type": "opportunity",
                    "source": source.value,
                    "message": f"Viral spike detected on {source.value}! Consider increasing marketing spend.",
                    "action": "increase_marketing",
                    "urgency": "high"
                })

        # Check competitor actions
        if PlatformSource.TICKETMASTER in signals:
            competitor_data = signals[PlatformSource.TICKETMASTER].data
            if competitor_data.get("competitor_marketing") == "heavy":
                alerts.append({
                    "type": "competition",
                    "message": "Heavy competitor marketing detected. Boost campaigns to maintain visibility.",
                    "action": "boost_campaigns",
                    "urgency": "medium"
                })

        # Weather alerts
        if PlatformSource.WEATHER in signals:
            weather_data = signals[PlatformSource.WEATHER].data
            if weather_data.get("precipitation_chance", 0) > 0.6:
                alerts.append({
                    "type": "weather",
                    "message": "High chance of rain predicted. Consider indoor contingency messaging.",
                    "action": "weather_contingency",
                    "urgency": "low"
                })

        return alerts

    def get_ecosystem_summary(self) -> Dict:
        """Get summary of ecosystem intelligence"""
        if not self.insights:
            return {"status": "no_data"}

        recent_insights = self.insights[-10:]  # Last 10 insights

        insight_types = {}
        for insight in recent_insights:
            insight_types[insight.insight_type] = insight_types.get(insight.insight_type, 0) + 1

        avg_confidence = sum(i.confidence for i in recent_insights) / len(recent_insights)

        return {
            "total_insights": len(self.insights),
            "recent_insights": len(recent_insights),
            "insight_distribution": insight_types,
            "average_confidence": avg_confidence,
            "strongest_signal": max(recent_insights, key=lambda i: i.confidence).recommendation if recent_insights else None,
            "platforms_monitored": len(self.connectors)
        }