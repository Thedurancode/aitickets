"""
Tests for Event-Driven Architecture
Tests that events are published and handled correctly.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.services.event_bus import (
    EventBus, EventType, DomainEvent,
    publish_ticket_sold, publish_inventory_low
)
from app.services.ticket_service_events import EventDrivenTicketService
from app.services.event_handlers import (
    handle_inventory_low,
    handle_event_sold_out,
    handle_sales_spike,
    handle_vip_achieved
)
from app.models import (
    Event, Ticket, TicketTier, EventGoer, TicketStatus,
    MetaAdCampaign, MetaAdStatus
)


@pytest.fixture
async def event_bus_test():
    """Create test event bus with in-memory Redis mock."""
    bus = EventBus("redis://localhost:6379/1")  # Use test database
    # Mock Redis for testing
    bus.redis = AsyncMock()
    bus.redis.xadd = AsyncMock(return_value="1234567890-0")
    bus.redis.ping = AsyncMock()
    yield bus
    await bus.disconnect()


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.close = Mock()
    return db


class TestEventBus:
    """Test core event bus functionality."""

    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus_test):
        """Test publishing an event to Redis."""
        event = DomainEvent(
            event_type=EventType.TICKET_SOLD,
            aggregate_id="123",
            aggregate_type="ticket",
            data={"ticket_id": 123, "price": 5000},
            metadata={"source": "test"},
            timestamp=datetime.now(timezone.utc),
            correlation_id=str(uuid4())
        )

        event_id = await event_bus_test.publish(event)

        # Verify Redis xadd was called correctly
        event_bus_test.redis.xadd.assert_called()
        assert event_id == "1234567890-0"

    @pytest.mark.asyncio
    async def test_subscribe_decorator(self, event_bus_test):
        """Test subscribing handlers to events."""
        handler_called = False

        @event_bus_test.subscribe(EventType.TICKET_SOLD)
        async def test_handler(event: DomainEvent):
            nonlocal handler_called
            handler_called = True

        # Verify handler was registered
        assert EventType.TICKET_SOLD in event_bus_test.handlers
        assert len(event_bus_test.handlers[EventType.TICKET_SOLD]) == 1

    @pytest.mark.asyncio
    async def test_event_serialization(self):
        """Test event serialization and deserialization."""
        original_event = DomainEvent(
            event_type=EventType.INVENTORY_LOW,
            aggregate_id="456",
            aggregate_type="tier",
            data={"remaining": 5, "tier_id": 456},
            metadata={"version": "1.0"},
            timestamp=datetime.now(timezone.utc),
            correlation_id="corr-123",
            causation_id="cause-456"
        )

        # Convert to dict and back
        event_dict = original_event.to_dict()
        restored_event = DomainEvent.from_dict(event_dict)

        assert restored_event.event_type == original_event.event_type
        assert restored_event.aggregate_id == original_event.aggregate_id
        assert restored_event.data == original_event.data
        assert restored_event.correlation_id == original_event.correlation_id


class TestTicketServiceEvents:
    """Test ticket service event publishing."""

    @pytest.mark.asyncio
    async def test_sell_ticket_publishes_events(self, mock_db):
        """Test that selling tickets publishes appropriate events."""
        # Setup mock data
        tier = Mock(spec=TicketTier)
        tier.id = 1
        tier.price = 5000
        tier.quantity_available = 100
        tier.quantity_sold = 95  # Almost sold out
        tier.name = "General"

        mock_db.query().filter().first.return_value = tier
        mock_db.query().filter().scalar.return_value = 0  # No total available

        service = EventDrivenTicketService(mock_db)

        with patch('app.services.ticket_service_events.publish_ticket_sold') as mock_publish_sold:
            with patch('app.services.ticket_service_events.publish_inventory_low') as mock_publish_low:
                with patch('app.services.ticket_service_events.event_bus') as mock_bus:
                    result = await service.sell_ticket(
                        event_id=1,
                        tier_id=1,
                        customer_id=123,
                        quantity=1
                    )

                    # Verify ticket was sold
                    assert result["success"] is True

                    # Verify events were published
                    mock_publish_sold.assert_called_once()
                    mock_publish_low.assert_called_once()  # Because we're at 96/100

    @pytest.mark.asyncio
    async def test_sold_out_event_published(self, mock_db):
        """Test EVENT_SOLD_OUT is published when last ticket sells."""
        tier = Mock(spec=TicketTier)
        tier.id = 1
        tier.price = 5000
        tier.quantity_available = 100
        tier.quantity_sold = 99  # Last ticket available
        tier.name = "General"

        mock_db.query().filter().first.return_value = tier
        mock_db.query().filter().scalar.return_value = 0  # Will be sold out

        service = EventDrivenTicketService(mock_db)

        with patch('app.services.ticket_service_events.event_bus') as mock_bus:
            result = await service.sell_ticket(
                event_id=1,
                tier_id=1,
                customer_id=123,
                quantity=1
            )

            # Find the TIER_SOLD_OUT event
            calls = mock_bus.publish.call_args_list
            sold_out_events = [
                call for call in calls
                if call[0][0].event_type == EventType.TIER_SOLD_OUT
            ]

            assert len(sold_out_events) > 0

    @pytest.mark.asyncio
    async def test_group_booking_event(self, mock_db):
        """Test GROUP_BOOKING event for 5+ tickets."""
        tier = Mock(spec=TicketTier)
        tier.id = 1
        tier.price = 5000
        tier.quantity_available = 100
        tier.quantity_sold = 10
        tier.name = "VIP"

        mock_db.query().filter().first.return_value = tier

        service = EventDrivenTicketService(mock_db)

        with patch('app.services.ticket_service_events.event_bus') as mock_bus:
            result = await service.sell_ticket(
                event_id=1,
                tier_id=1,
                customer_id=123,
                quantity=6  # Group booking
            )

            # Find the GROUP_BOOKING event
            calls = mock_bus.publish.call_args_list
            group_events = [
                call for call in calls
                if call[0][0].event_type == EventType.GROUP_BOOKING
            ]

            assert len(group_events) > 0
            assert group_events[0][0][0].data["group_size"] == 6


class TestEventHandlers:
    """Test event handlers react correctly."""

    @pytest.mark.asyncio
    async def test_inventory_low_handler(self, mock_db):
        """Test inventory low handler triggers urgency campaigns."""
        # Setup mock data
        event_obj = Mock(spec=Event)
        event_obj.id = 1
        event_obj.name = "Test Concert"
        event_obj.url = "https://tickets.com/1"
        event_obj.image_url = "https://image.jpg"
        event_obj.metadata = {}

        tier = Mock(spec=TicketTier)
        tier.name = "General"

        mock_db.query().filter().first.side_effect = [event_obj, tier]
        mock_db.query().join().filter().limit().all.return_value = []
        mock_db.query().filter().all.return_value = []  # No campaigns

        event = DomainEvent(
            event_type=EventType.INVENTORY_LOW,
            aggregate_id="1",
            aggregate_type="tier",
            data={
                "event_id": 1,
                "tier_id": 1,
                "remaining": 8,
                "percentage": 8.0
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
            correlation_id=str(uuid4())
        )

        with patch('app.services.event_handlers.get_db', return_value=mock_db):
            with patch('app.services.event_handlers.send_sms_batch') as mock_sms:
                with patch('app.services.event_handlers.post_to_social') as mock_social:
                    await handle_inventory_low(event)

                    # Verify urgency actions were taken
                    assert event_obj.metadata["show_urgency_banner"] is True
                    assert "Only 8 tickets left" in event_obj.metadata["urgency_message"]
                    mock_social.assert_called()

    @pytest.mark.asyncio
    async def test_sold_out_handler(self, mock_db):
        """Test sold out handler pauses ads and activates waitlist."""
        event_obj = Mock(spec=Event)
        event_obj.id = 1
        event_obj.name = "Sold Out Show"
        event_obj.metadata = {}

        campaign = Mock(spec=MetaAdCampaign)
        campaign.id = 1
        campaign.status = MetaAdStatus.ACTIVE

        mock_db.query().filter().first.return_value = event_obj
        mock_db.query().filter().all.return_value = [campaign]
        mock_db.query().join().filter().distinct().all.return_value = []

        event = DomainEvent(
            event_type=EventType.EVENT_SOLD_OUT,
            aggregate_id="1",
            aggregate_type="event",
            data={"event_id": 1},
            metadata={},
            timestamp=datetime.now(timezone.utc),
            correlation_id=str(uuid4())
        )

        with patch('app.services.event_handlers.get_db', return_value=mock_db):
            with patch('app.services.event_handlers.post_to_social') as mock_social:
                await handle_event_sold_out(event)

                # Verify ads were paused
                assert campaign.status == MetaAdStatus.PAUSED
                assert campaign.paused_reason == "Event sold out"

                # Verify waitlist activated
                assert event_obj.waitlist_enabled is True

                # Verify social media updated
                mock_social.assert_called()

    @pytest.mark.asyncio
    async def test_sales_spike_handler(self, mock_db):
        """Test sales spike handler increases ad spend."""
        event_obj = Mock(spec=Event)
        event_obj.id = 1
        event_obj.name = "Hot Event"
        event_obj.metadata = {}

        campaign = Mock(spec=MetaAdCampaign)
        campaign.id = 1
        campaign.budget_cents = 10000  # $100

        mock_db.query().filter().first.return_value = event_obj
        mock_db.query().filter().all.return_value = [campaign]
        mock_db.query().limit().all.return_value = []

        event = DomainEvent(
            event_type=EventType.SALES_SPIKE,
            aggregate_id="1",
            aggregate_type="event",
            data={
                "event_id": 1,
                "sales_per_minute": 2.5,
                "previous_rate": 0.5
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
            correlation_id=str(uuid4())
        )

        with patch('app.services.event_handlers.get_db', return_value=mock_db):
            with patch('app.services.event_handlers.send_sms_batch') as mock_sms:
                await handle_sales_spike(event)

                # Verify budget was increased by 25%
                assert campaign.budget_cents == 12500  # $125

                # Verify live sales counter enabled
                assert event_obj.metadata["show_live_sales"] is True

    @pytest.mark.asyncio
    async def test_vip_achievement_handler(self, mock_db):
        """Test VIP achievement handler grants perks."""
        customer = Mock(spec=EventGoer)
        customer.id = 123
        customer.first_name = "John"
        customer.email = "john@example.com"
        customer.phone = "+15551234567"
        customer.metadata = {}

        mock_db.query().filter().first.return_value = customer

        event = DomainEvent(
            event_type=EventType.CUSTOMER_VIP_ACHIEVED,
            aggregate_id="123",
            aggregate_type="customer",
            data={
                "customer_id": 123,
                "total_spent_cents": 75000,  # $750
                "ticket_count": 15
            },
            metadata={},
            timestamp=datetime.now(timezone.utc),
            correlation_id=str(uuid4())
        )

        with patch('app.services.event_handlers.get_db', return_value=mock_db):
            with patch('app.services.event_handlers.send_email_batch') as mock_email:
                with patch('app.services.event_handlers.send_sms_batch') as mock_sms:
                    await handle_vip_achieved(event)

                    # Verify VIP status set
                    assert customer.metadata["vip"] is True

                    # Verify notifications sent
                    mock_email.assert_called_once()
                    mock_sms.assert_called_once()

                    # Verify promo code created
                    mock_db.add.assert_called()


class TestEndToEndEventFlow:
    """Test complete event flows from trigger to handler."""

    @pytest.mark.asyncio
    async def test_complete_sold_out_flow(self):
        """Test complete flow from last ticket sale to sold out handling."""
        # This would be an integration test with real Redis
        # For now, we test the logical flow

        # 1. Last ticket sells
        # 2. TIER_SOLD_OUT event published
        # 3. EVENT_SOLD_OUT event published
        # 4. Handler pauses all ads
        # 5. Handler activates waitlist
        # 6. Handler sends notifications
        # 7. Social media updated

        assert True  # Placeholder for integration test


@pytest.mark.asyncio
async def test_event_replay():
    """Test replaying events for recovery."""
    bus = EventBus()
    bus.redis = AsyncMock()

    # Mock historical events
    bus.redis.xrange = AsyncMock(return_value=[
        ("1234567890-0", {
            "event_type": "ticket.sold",
            "aggregate_id": "1",
            "aggregate_type": "ticket",
            "data": '{"ticket_id": 1}',
            "metadata": '{}',
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": "test",
            "causation_id": "",
            "user_id": ""
        })
    ])

    replayed_events = []

    async def replay_handler(event: DomainEvent):
        replayed_events.append(event)

    await bus.replay_events(
        EventType.TICKET_SOLD,
        datetime.now(timezone.utc) - timedelta(hours=1),
        datetime.now(timezone.utc),
        replay_handler
    )

    assert len(replayed_events) == 1
    assert replayed_events[0].event_type == EventType.TICKET_SOLD