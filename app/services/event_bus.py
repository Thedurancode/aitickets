"""
Event-Driven Architecture Core
Real-time event bus using Redis Streams for immediate reactions to business events.

This replaces polling-based triggers with instant event-driven responses.
"""

import json
import asyncio
import logging
from enum import Enum
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class EventType(Enum):
    """All domain events that can trigger immediate actions"""

    # Ticket Events
    TICKET_SOLD = "ticket.sold"
    TICKET_REFUNDED = "ticket.refunded"
    TICKET_TRANSFERRED = "ticket.transferred"
    TICKET_CHECKED_IN = "ticket.checked_in"

    # Inventory Events
    INVENTORY_LOW = "inventory.low"  # <10% remaining
    INVENTORY_CRITICAL = "inventory.critical"  # <5 tickets
    INVENTORY_EXHAUSTED = "inventory.exhausted"  # Sold out
    TIER_SOLD_OUT = "tier.sold_out"
    EVENT_SOLD_OUT = "event.sold_out"

    # Pricing Events
    PRICE_CHANGED = "price.changed"
    DYNAMIC_PRICING_TRIGGERED = "pricing.dynamic_triggered"
    EARLY_BIRD_ENDING = "pricing.early_bird_ending"

    # Customer Events
    CUSTOMER_REGISTERED = "customer.registered"
    CUSTOMER_VIP_ACHIEVED = "customer.vip_achieved"
    CUSTOMER_CHURN_RISK = "customer.churn_risk"
    GROUP_BOOKING = "customer.group_booking"  # 5+ tickets

    # Marketing Events
    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_PAUSED = "campaign.paused"
    CAMPAIGN_RESUMED = "campaign.resumed"
    AD_PERFORMANCE_POOR = "ad.performance.poor"
    AD_PERFORMANCE_GOOD = "ad.performance.good"
    ROAS_THRESHOLD_BREACH = "ad.roas_breach"

    # Event Lifecycle
    EVENT_CREATED = "event.created"
    EVENT_UPDATED = "event.updated"
    EVENT_STARTING_SOON = "event.starting_soon"  # 24 hours
    EVENT_STARTED = "event.started"
    EVENT_ENDED = "event.ended"

    # Sales Velocity Events
    SALES_SPIKE = "sales.spike"  # Sudden increase
    SALES_STALLED = "sales.stalled"  # No sales in N hours
    CONVERSION_RATE_DROP = "sales.conversion_drop"

    # System Events
    WEBHOOK_FAILED = "system.webhook_failed"
    PAYMENT_FAILED = "system.payment_failed"
    SYSTEM_ALERT = "system.alert"


@dataclass
class DomainEvent:
    """Base event structure for all domain events"""
    event_type: EventType
    aggregate_id: str  # e.g., event_id, ticket_id
    aggregate_type: str  # e.g., "event", "ticket", "customer"
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
    causation_id: Optional[str] = None  # ID of event that caused this
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage"""
        return {
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "data": json.dumps(self.data),
            "metadata": json.dumps(self.metadata),
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id or "",
            "user_id": self.user_id or ""
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DomainEvent':
        """Reconstruct from Redis data"""
        return cls(
            event_type=EventType(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            data=json.loads(data["data"]),
            metadata=json.loads(data["metadata"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"] or None,
            user_id=data["user_id"] or None
        )


class EventBus:
    """
    Central event bus for publishing and consuming domain events.
    Uses Redis Streams for persistence and real-time delivery.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.consumer_group = "ai_tickets"
        self.consumer_name = f"consumer_{uuid4().hex[:8]}"
        self.running = False

    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=50
            )
            await self.redis.ping()
            logger.info("EventBus connected to Redis")
        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Clean up Redis connection"""
        if self.redis:
            await self.redis.close()

    async def publish(self, event: DomainEvent) -> str:
        """
        Publish event to Redis Stream.
        Returns the event ID from Redis.
        """
        if not self.redis:
            await self.connect()

        stream_key = f"events:{event.event_type.value}"

        # Add to main event stream
        event_id = await self.redis.xadd(
            stream_key,
            event.to_dict(),
            maxlen=10000  # Keep last 10k events per type
        )

        # Also add to aggregate stream for entity-specific history
        aggregate_stream = f"events:aggregate:{event.aggregate_type}:{event.aggregate_id}"
        await self.redis.xadd(
            aggregate_stream,
            event.to_dict(),
            maxlen=1000  # Keep last 1k events per entity
        )

        # Log for debugging
        logger.info(f"Published {event.event_type.value} event: {event_id}")

        # Update metrics
        await self._update_metrics(event)

        return event_id

    def subscribe(self, event_type: EventType):
        """Decorator to register event handlers"""
        def decorator(func: Callable):
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(func)
            logger.info(f"Registered handler {func.__name__} for {event_type.value}")
            return func
        return decorator

    async def start_consumer(self):
        """
        Start consuming events from Redis Streams.
        Creates consumer groups and processes events in real-time.
        """
        if not self.redis:
            await self.connect()

        self.running = True

        # Create consumer groups for all event types
        for event_type in EventType:
            stream_key = f"events:{event_type.value}"
            try:
                await self.redis.xgroup_create(
                    stream_key,
                    self.consumer_group,
                    id="0",
                    mkstream=True
                )
            except Exception:
                # Group already exists, that's fine
                pass

        logger.info(f"EventBus consumer started: {self.consumer_name}")

        # Start consuming
        while self.running:
            try:
                # Read from all event streams
                streams = {
                    f"events:{et.value}": ">"
                    for et in EventType
                    if et in self.handlers
                }

                if not streams:
                    await asyncio.sleep(1)
                    continue

                # Read with timeout to allow graceful shutdown
                messages = await self.redis.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    streams,
                    count=10,
                    block=1000  # 1 second timeout
                )

                for stream, stream_messages in messages:
                    event_type_str = stream.replace("events:", "")
                    event_type = EventType(event_type_str)

                    for message_id, data in stream_messages:
                        try:
                            # Reconstruct event
                            event = DomainEvent.from_dict(data)

                            # Call all handlers for this event type
                            if event_type in self.handlers:
                                for handler in self.handlers[event_type]:
                                    try:
                                        # Support both sync and async handlers
                                        if asyncio.iscoroutinefunction(handler):
                                            await handler(event)
                                        else:
                                            handler(event)
                                    except Exception as e:
                                        logger.error(
                                            f"Handler {handler.__name__} failed: {e}",
                                            exc_info=True
                                        )

                            # Acknowledge message
                            await self.redis.xack(stream, self.consumer_group, message_id)

                        except Exception as e:
                            logger.error(f"Failed to process message {message_id}: {e}")
                            # Message will be redelivered to another consumer

            except TimeoutError:
                # Normal timeout, continue
                continue
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(1)

    async def stop_consumer(self):
        """Gracefully stop the consumer"""
        self.running = False
        logger.info("EventBus consumer stopping...")

    async def get_event_history(
        self,
        aggregate_type: str,
        aggregate_id: str,
        limit: int = 100
    ) -> List[DomainEvent]:
        """Get event history for a specific entity"""
        if not self.redis:
            await self.connect()

        stream_key = f"events:aggregate:{aggregate_type}:{aggregate_id}"

        # Read events from oldest to newest
        messages = await self.redis.xrange(stream_key, count=limit)

        events = []
        for message_id, data in messages:
            try:
                event = DomainEvent.from_dict(data)
                events.append(event)
            except Exception as e:
                logger.error(f"Failed to parse event {message_id}: {e}")

        return events

    async def replay_events(
        self,
        event_type: EventType,
        from_time: datetime,
        to_time: datetime,
        handler: Callable
    ):
        """Replay historical events for recovery or analysis"""
        if not self.redis:
            await self.connect()

        stream_key = f"events:{event_type.value}"

        # Convert times to Redis timestamps
        from_ts = int(from_time.timestamp() * 1000)
        to_ts = int(to_time.timestamp() * 1000)

        messages = await self.redis.xrange(
            stream_key,
            min=from_ts,
            max=to_ts
        )

        for message_id, data in messages:
            try:
                event = DomainEvent.from_dict(data)
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Replay handler failed for {message_id}: {e}")

    async def _update_metrics(self, event: DomainEvent):
        """Track event metrics for monitoring"""
        # Increment event counter
        await self.redis.hincrby(
            "events:metrics:counts",
            event.event_type.value,
            1
        )

        # Update last event time
        await self.redis.hset(
            "events:metrics:last_seen",
            event.event_type.value,
            event.timestamp.isoformat()
        )

    async def get_metrics(self) -> dict:
        """Get event bus metrics"""
        if not self.redis:
            await self.connect()

        counts = await self.redis.hgetall("events:metrics:counts")
        last_seen = await self.redis.hgetall("events:metrics:last_seen")

        return {
            "event_counts": counts,
            "last_seen": last_seen,
            "consumer_group": self.consumer_group,
            "consumer_name": self.consumer_name
        }


# Global event bus instance
event_bus = EventBus()


# Helper functions for common event publishing patterns
async def publish_ticket_sold(
    ticket_id: int,
    event_id: int,
    customer_id: int,
    price_cents: int,
    tier_id: int,
    quantity: int = 1
) -> str:
    """Publish TICKET_SOLD event"""
    event = DomainEvent(
        event_type=EventType.TICKET_SOLD,
        aggregate_id=str(ticket_id),
        aggregate_type="ticket",
        data={
            "ticket_id": ticket_id,
            "event_id": event_id,
            "customer_id": customer_id,
            "price_cents": price_cents,
            "tier_id": tier_id,
            "quantity": quantity
        },
        metadata={
            "source": "ticket_service",
            "version": "1.0"
        },
        timestamp=datetime.now(timezone.utc),
        correlation_id=str(uuid4())
    )
    return await event_bus.publish(event)


async def publish_inventory_low(
    event_id: int,
    tier_id: int,
    remaining: int,
    total: int
) -> str:
    """Publish INVENTORY_LOW event"""
    event = DomainEvent(
        event_type=EventType.INVENTORY_LOW,
        aggregate_id=str(tier_id),
        aggregate_type="tier",
        data={
            "event_id": event_id,
            "tier_id": tier_id,
            "remaining": remaining,
            "total": total,
            "percentage": (remaining / total * 100) if total > 0 else 0
        },
        metadata={
            "source": "inventory_service",
            "version": "1.0"
        },
        timestamp=datetime.now(timezone.utc),
        correlation_id=str(uuid4())
    )
    return await event_bus.publish(event)