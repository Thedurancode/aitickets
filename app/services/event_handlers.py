"""
Event Handlers for Real-Time Reactions
Handles domain events immediately when they occur.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import (
    Event, Ticket, TicketTier, EventGoer, TicketStatus,
    MetaAdCampaign, MetaAdStatus, Notification, NotificationChannel,
    WaitlistEntry, WaitlistStatus, PromoCode, DiscountType
)
from app.services.event_bus import event_bus, EventType, DomainEvent
from app.services.notifications import send_notification_batch
from app.services.sms import send_sms_batch
from app.services.email import send_email_batch
from app.services.meta_ads import pause_campaign, increase_campaign_budget
from app.services.social_media import post_to_social

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session for handlers"""
    return SessionLocal()


# ================ INVENTORY HANDLERS ================

@event_bus.subscribe(EventType.INVENTORY_LOW)
async def handle_inventory_low(event: DomainEvent):
    """
    React immediately when inventory drops below 10%.
    Triggers urgency campaigns and increases ad spend.
    """
    db = get_db()
    try:
        event_id = event.data["event_id"]
        tier_id = event.data["tier_id"]
        remaining = event.data["remaining"]
        percentage = event.data["percentage"]

        logger.info(f"INVENTORY LOW: Event {event_id}, Tier {tier_id} - {remaining} left ({percentage:.1f}%)")

        # Get event and tier details
        event_obj = db.query(Event).filter(Event.id == event_id).first()
        tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()

        if not event_obj or not tier:
            return

        # 1. Send urgency notifications to interested customers
        message = f"🔥 HURRY! Only {remaining} {tier.name} tickets left for {event_obj.name}! Get yours now before they're gone!"

        # Get customers who viewed but didn't buy (would come from analytics)
        recent_viewers = (
            db.query(EventGoer)
            .join(Ticket, Ticket.event_goer_id == EventGoer.id)
            .filter(
                Ticket.event_id == event_id,
                Ticket.status == TicketStatus.CART
            )
            .limit(100)
            .all()
        )

        if recent_viewers:
            phone_numbers = [v.phone for v in recent_viewers if v.phone]
            if phone_numbers:
                await send_sms_batch(phone_numbers, message)

        # 2. Increase ad spend for final push
        active_campaigns = (
            db.query(MetaAdCampaign)
            .filter(
                MetaAdCampaign.event_id == event_id,
                MetaAdCampaign.status == MetaAdStatus.ACTIVE
            )
            .all()
        )

        for campaign in active_campaigns:
            # Increase budget by 50% for urgency
            new_budget = int(campaign.budget_cents * 1.5)
            campaign.budget_cents = new_budget
            logger.info(f"Increased campaign {campaign.id} budget to ${new_budget/100:.2f}")

        # 3. Create time-limited promo code for urgency
        promo_code = PromoCode(
            code=f"LAST{remaining}",
            event_id=event_id,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10,  # 10% off
            max_uses=remaining,  # Limited to remaining tickets
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=2),  # 2 hour flash sale
            description=f"Flash sale - only {remaining} uses!"
        )
        db.add(promo_code)

        # 4. Update website with urgency banner (via webhook or direct update)
        event_obj.metadata = event_obj.metadata or {}
        event_obj.metadata["show_urgency_banner"] = True
        event_obj.metadata["urgency_message"] = f"⚡ Only {remaining} tickets left!"

        # 5. Post to social media
        social_message = f"🚨 ALMOST SOLD OUT! 🚨\n\nOnly {remaining} tickets remaining for {event_obj.name}!\n\nDon't miss out: {event_obj.url}\n\n#AlmostSoldOut #LastChance #{event_obj.name.replace(' ', '')}"
        await post_to_social("twitter", social_message)
        await post_to_social("instagram", social_message, image_url=event_obj.image_url)

        db.commit()
        logger.info(f"Successfully handled low inventory for Event {event_id}")

    except Exception as e:
        logger.error(f"Error handling inventory low: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@event_bus.subscribe(EventType.EVENT_SOLD_OUT)
async def handle_event_sold_out(event: DomainEvent):
    """
    React immediately when event sells out completely.
    Pause all ads, activate waitlist, notify everyone.
    """
    db = get_db()
    try:
        event_id = event.data["event_id"]

        logger.info(f"EVENT SOLD OUT: Event {event_id}")

        event_obj = db.query(Event).filter(Event.id == event_id).first()
        if not event_obj:
            return

        # 1. IMMEDIATELY pause all ad campaigns (stop wasting money!)
        campaigns = (
            db.query(MetaAdCampaign)
            .filter(
                MetaAdCampaign.event_id == event_id,
                MetaAdCampaign.status.in_([MetaAdStatus.ACTIVE, MetaAdStatus.RUNNING])
            )
            .all()
        )

        for campaign in campaigns:
            campaign.status = MetaAdStatus.PAUSED
            campaign.paused_reason = "Event sold out"
            logger.info(f"Paused campaign {campaign.id} - event sold out")

        # 2. Update event status
        event_obj.status = "sold_out"
        event_obj.sold_out_at = datetime.now(timezone.utc)

        # 3. Activate waitlist
        event_obj.waitlist_enabled = True

        # 4. Send celebration notification to all ticket holders
        ticket_holders = (
            db.query(EventGoer)
            .join(Ticket, Ticket.event_goer_id == EventGoer.id)
            .filter(
                Ticket.event_id == event_id,
                Ticket.status == TicketStatus.CONFIRMED
            )
            .distinct()
            .all()
        )

        celebration_message = f"🎉 {event_obj.name} is OFFICIALLY SOLD OUT! You're one of the lucky ones with a ticket! See you there!"

        for holder in ticket_holders:
            notification = Notification(
                event_goer_id=holder.id,
                event_id=event_id,
                channel=NotificationChannel.EMAIL,
                subject="You're In! Event is Sold Out!",
                message=celebration_message,
                scheduled_for=datetime.now(timezone.utc)
            )
            db.add(notification)

        # 5. Update all social media
        sold_out_message = f"🎊 SOLD OUT! 🎊\n\n{event_obj.name} is officially SOLD OUT!\n\nThank you to everyone who got tickets. For those who missed out, join the waitlist for any last-minute releases.\n\n#SoldOut #{event_obj.name.replace(' ', '')}"

        await post_to_social("twitter", sold_out_message)
        await post_to_social("instagram", sold_out_message, image_url=event_obj.image_url)
        await post_to_social("facebook", sold_out_message)

        # 6. Update website
        event_obj.metadata = event_obj.metadata or {}
        event_obj.metadata["sold_out"] = True
        event_obj.metadata["show_waitlist"] = True

        db.commit()
        logger.info(f"Successfully handled sold out event {event_id}")

    except Exception as e:
        logger.error(f"Error handling sold out event: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


# ================ SALES VELOCITY HANDLERS ================

@event_bus.subscribe(EventType.SALES_SPIKE)
async def handle_sales_spike(event: DomainEvent):
    """
    React to sudden increase in sales velocity.
    Increase ad spend and send social proof notifications.
    """
    db = get_db()
    try:
        event_id = event.data["event_id"]
        sales_per_minute = event.data["sales_per_minute"]
        previous_rate = event.data.get("previous_rate", 0)

        logger.info(f"SALES SPIKE: Event {event_id} - {sales_per_minute} sales/min (was {previous_rate})")

        event_obj = db.query(Event).filter(Event.id == event_id).first()
        if not event_obj:
            return

        # 1. Increase ad spend to ride the wave
        campaigns = (
            db.query(MetaAdCampaign)
            .filter(
                MetaAdCampaign.event_id == event_id,
                MetaAdCampaign.status == MetaAdStatus.ACTIVE
            )
            .all()
        )

        for campaign in campaigns:
            # Increase budget by 25% during spike
            campaign.budget_cents = int(campaign.budget_cents * 1.25)
            logger.info(f"Increased campaign {campaign.id} budget during sales spike")

        # 2. Send social proof notifications
        social_proof_message = f"🔥 {event_obj.name} tickets are flying! {int(sales_per_minute * 60)} people bought tickets in the last hour. Don't miss out!"

        # Get recent website visitors (would come from analytics)
        # For now, get a sample of customers
        potential_customers = (
            db.query(EventGoer)
            .limit(50)
            .all()
        )

        for customer in potential_customers:
            if customer.phone:
                # Send SMS about the rush
                await send_sms_batch(
                    [customer.phone],
                    social_proof_message
                )

        # 3. Update website with live counter
        event_obj.metadata = event_obj.metadata or {}
        event_obj.metadata["show_live_sales"] = True
        event_obj.metadata["sales_message"] = f"🔥 {int(sales_per_minute * 60)} people bought tickets in the last hour!"

        db.commit()
        logger.info(f"Successfully handled sales spike for Event {event_id}")

    except Exception as e:
        logger.error(f"Error handling sales spike: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@event_bus.subscribe(EventType.SALES_STALLED)
async def handle_sales_stalled(event: DomainEvent):
    """
    React when sales have stalled (no sales in N hours).
    Create promotional campaigns to restart momentum.
    """
    db = get_db()
    try:
        event_id = event.data["event_id"]
        hours_stalled = event.data["hours_stalled"]

        logger.info(f"SALES STALLED: Event {event_id} - no sales for {hours_stalled} hours")

        event_obj = db.query(Event).filter(Event.id == event_id).first()
        if not event_obj:
            return

        # Calculate days until event
        days_until = (event_obj.date - datetime.now(timezone.utc).date()).days

        if days_until > 7:
            # 1. Create flash sale promo code
            promo_code = PromoCode(
                code=f"FLASH{event_id}",
                event_id=event_id,
                discount_type=DiscountType.PERCENTAGE,
                discount_value=15,  # 15% off
                max_uses=50,
                valid_from=datetime.now(timezone.utc),
                valid_until=datetime.now(timezone.utc) + timedelta(hours=24),
                description="24-hour flash sale!"
            )
            db.add(promo_code)

            # 2. Send promotional email/SMS
            message = f"⚡ FLASH SALE! 15% off {event_obj.name} tickets for the next 24 hours only! Use code FLASH{event_id}"

            # Get past customers who haven't bought for this event
            past_customers = (
                db.query(EventGoer)
                .join(Ticket, Ticket.event_goer_id == EventGoer.id)
                .filter(
                    Ticket.status == TicketStatus.CONFIRMED,
                    ~EventGoer.id.in_(
                        db.query(Ticket.event_goer_id)
                        .filter(Ticket.event_id == event_id)
                    )
                )
                .distinct()
                .limit(200)
                .all()
            )

            for customer in past_customers:
                if customer.email:
                    await send_email_batch(
                        [customer.email],
                        f"Flash Sale: {event_obj.name}",
                        message
                    )

            # 3. Boost ad campaigns
            campaigns = (
                db.query(MetaAdCampaign)
                .filter(
                    MetaAdCampaign.event_id == event_id,
                    MetaAdCampaign.status == MetaAdStatus.ACTIVE
                )
                .all()
            )

            for campaign in campaigns:
                campaign.budget_cents = int(campaign.budget_cents * 1.5)
                logger.info(f"Boosted campaign {campaign.id} to restart sales")

        else:
            # Event is soon - more aggressive tactics
            # Create bigger discount
            promo_code = PromoCode(
                code=f"FINAL{event_id}",
                event_id=event_id,
                discount_type=DiscountType.PERCENTAGE,
                discount_value=25,  # 25% off
                max_uses=100,
                valid_from=datetime.now(timezone.utc),
                valid_until=event_obj.date,
                description="Final chance - 25% off!"
            )
            db.add(promo_code)

        db.commit()
        logger.info(f"Successfully handled stalled sales for Event {event_id}")

    except Exception as e:
        logger.error(f"Error handling stalled sales: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


# ================ CUSTOMER HANDLERS ================

@event_bus.subscribe(EventType.CUSTOMER_VIP_ACHIEVED)
async def handle_vip_achieved(event: DomainEvent):
    """
    React when customer reaches VIP status.
    Send congratulations and special perks.
    """
    db = get_db()
    try:
        customer_id = event.data["customer_id"]
        total_spent = event.data["total_spent_cents"]
        ticket_count = event.data["ticket_count"]

        logger.info(f"VIP ACHIEVED: Customer {customer_id} - ${total_spent/100:.2f} spent")

        customer = db.query(EventGoer).filter(EventGoer.id == customer_id).first()
        if not customer:
            return

        # 1. Update customer status
        customer.metadata = customer.metadata or {}
        customer.metadata["vip"] = True
        customer.metadata["vip_since"] = datetime.now(timezone.utc).isoformat()

        # 2. Create VIP promo code
        promo_code = PromoCode(
            code=f"VIP{customer_id}",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=20,  # 20% VIP discount
            max_uses=10,
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=365),
            description=f"VIP discount for {customer.first_name}",
            metadata={"customer_id": customer_id, "vip_only": True}
        )
        db.add(promo_code)

        # 3. Send VIP welcome message
        vip_message = f"""
        🌟 Congratulations {customer.first_name}! 🌟

        You've achieved VIP status! As a valued customer, you now enjoy:

        ✅ 20% off all events (code: VIP{customer_id})
        ✅ Early access to new events
        ✅ Priority customer support
        ✅ Exclusive VIP-only events

        Thank you for being amazing!
        """

        if customer.email:
            await send_email_batch(
                [customer.email],
                "Welcome to VIP Status! 🌟",
                vip_message
            )

        if customer.phone:
            await send_sms_batch(
                [customer.phone],
                f"🌟 {customer.first_name}, you're now a VIP! Enjoy 20% off all events with code VIP{customer_id}"
            )

        db.commit()
        logger.info(f"Successfully upgraded customer {customer_id} to VIP")

    except Exception as e:
        logger.error(f"Error handling VIP achievement: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@event_bus.subscribe(EventType.GROUP_BOOKING)
async def handle_group_booking(event: DomainEvent):
    """
    React to group bookings (5+ tickets).
    Send special thanks and offer group perks.
    """
    db = get_db()
    try:
        ticket_ids = event.data["ticket_ids"]
        event_id = event.data["event_id"]
        customer_id = event.data["customer_id"]
        group_size = event.data["group_size"]

        logger.info(f"GROUP BOOKING: {group_size} tickets for Event {event_id}")

        customer = db.query(EventGoer).filter(EventGoer.id == customer_id).first()
        event_obj = db.query(Event).filter(Event.id == event_id).first()

        if not customer or not event_obj:
            return

        # 1. Send group booking confirmation
        group_message = f"""
        🎉 Group Booking Confirmed! 🎉

        Thank you {customer.first_name} for bringing {group_size} people to {event_obj.name}!

        Your group benefits:
        ✅ Priority check-in lane
        ✅ Group seating arrangement
        ✅ Complimentary group photo at the event

        We've notified our event staff about your group arrival.
        """

        if customer.email:
            await send_email_batch(
                [customer.email],
                f"Group Booking Confirmed - {event_obj.name}",
                group_message
            )

        # 2. Note for event staff
        event_obj.metadata = event_obj.metadata or {}
        event_obj.metadata["group_bookings"] = event_obj.metadata.get("group_bookings", [])
        event_obj.metadata["group_bookings"].append({
            "customer_id": customer_id,
            "customer_name": f"{customer.first_name} {customer.last_name}",
            "group_size": group_size,
            "ticket_ids": ticket_ids
        })

        # 3. Update customer profile
        customer.metadata = customer.metadata or {}
        customer.metadata["group_organizer"] = True
        customer.metadata["total_group_tickets"] = customer.metadata.get("total_group_tickets", 0) + group_size

        db.commit()
        logger.info(f"Successfully processed group booking for Event {event_id}")

    except Exception as e:
        logger.error(f"Error handling group booking: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


# ================ AD CAMPAIGN HANDLERS ================

@event_bus.subscribe(EventType.AD_PERFORMANCE_POOR)
async def handle_poor_ad_performance(event: DomainEvent):
    """
    React immediately to poor performing ads.
    Pause or adjust campaigns in real-time.
    """
    db = get_db()
    try:
        campaign_id = event.data["campaign_id"]
        roas = event.data["roas"]
        spend_cents = event.data["spend_cents"]
        conversions = event.data["conversions"]

        logger.info(f"POOR AD PERFORMANCE: Campaign {campaign_id} - ROAS {roas}")

        campaign = db.query(MetaAdCampaign).filter(MetaAdCampaign.id == campaign_id).first()
        if not campaign:
            return

        if roas < 0.5:
            # Very poor performance - pause immediately
            campaign.status = MetaAdStatus.PAUSED
            campaign.paused_reason = f"Poor ROAS: {roas:.2f}"
            logger.warning(f"Paused campaign {campaign_id} due to ROAS {roas}")

        elif roas < 1.0:
            # Below break-even - reduce budget
            campaign.budget_cents = int(campaign.budget_cents * 0.5)
            logger.info(f"Reduced budget for campaign {campaign_id} to ${campaign.budget_cents/100:.2f}")

            # Try different targeting
            campaign.metadata = campaign.metadata or {}
            campaign.metadata["needs_optimization"] = True

        # Notify marketing team
        # In production, this would send to Slack or email
        logger.info(f"Alert: Campaign {campaign_id} needs attention - ROAS {roas}")

        db.commit()

    except Exception as e:
        logger.error(f"Error handling poor ad performance: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@event_bus.subscribe(EventType.AD_PERFORMANCE_GOOD)
async def handle_good_ad_performance(event: DomainEvent):
    """
    React to well-performing ads.
    Increase budget and replicate successful strategies.
    """
    db = get_db()
    try:
        campaign_id = event.data["campaign_id"]
        roas = event.data["roas"]

        logger.info(f"GOOD AD PERFORMANCE: Campaign {campaign_id} - ROAS {roas}")

        campaign = db.query(MetaAdCampaign).filter(MetaAdCampaign.id == campaign_id).first()
        if not campaign:
            return

        if roas > 3.0:
            # Excellent performance - increase budget
            campaign.budget_cents = min(
                int(campaign.budget_cents * 1.5),
                50000  # Cap at $500/day
            )
            logger.info(f"Increased budget for high-performing campaign {campaign_id}")

            # Mark as template for future campaigns
            campaign.metadata = campaign.metadata or {}
            campaign.metadata["high_performer"] = True
            campaign.metadata["template_worthy"] = True

        db.commit()

    except Exception as e:
        logger.error(f"Error handling good ad performance: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()