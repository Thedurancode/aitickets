"""
Automated Marketing Trigger Service

Rule-based triggers that fire when event conditions are met:
- low_sell_through: sell-through below threshold with N days left
- almost_sold_out: sell-through above threshold (e.g. 90%)
- post_event_followup: event ended yesterday
- new_event_alert: new event created in last hour
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sqlfunc

from app.models import (
    AutoTrigger,
    Event,
    EventStatus,
    TicketTier,
    Ticket,
    TicketStatus,
    EventGoer,
    event_category_link,
)

logger = logging.getLogger(__name__)


def create_trigger(
    db: Session,
    name: str,
    trigger_type: str,
    action: str,
    event_id: int = None,
    threshold_value: int = None,
    threshold_days: int = None,
    action_config: dict = None,
) -> dict:
    """Create a new auto trigger."""
    valid_types = ["low_sell_through", "almost_sold_out", "post_event_followup", "new_event_alert"]
    if trigger_type not in valid_types:
        return {"error": f"Invalid trigger_type. Must be one of: {', '.join(valid_types)}"}

    valid_actions = ["send_promo", "send_campaign", "send_survey"]
    if action not in valid_actions:
        return {"error": f"Invalid action. Must be one of: {', '.join(valid_actions)}"}

    trigger = AutoTrigger(
        name=name,
        trigger_type=trigger_type,
        event_id=event_id,
        threshold_value=threshold_value,
        threshold_days=threshold_days,
        action=action,
        action_config=json.dumps(action_config) if action_config else None,
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)

    return {
        "success": True,
        "trigger_id": trigger.id,
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "message": f"Trigger '{name}' created. It will be evaluated every hour.",
    }


def list_triggers(db: Session) -> dict:
    """List all auto triggers."""
    triggers = db.query(AutoTrigger).order_by(AutoTrigger.created_at.desc()).all()
    return {
        "total": len(triggers),
        "triggers": [
            {
                "id": t.id,
                "name": t.name,
                "trigger_type": t.trigger_type,
                "event_id": t.event_id,
                "threshold_value": t.threshold_value,
                "threshold_days": t.threshold_days,
                "action": t.action,
                "action_config": json.loads(t.action_config) if t.action_config else None,
                "is_active": t.is_active,
                "fire_count": t.fire_count,
                "last_fired_at": t.last_fired_at.isoformat() if t.last_fired_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in triggers
        ],
    }


def delete_trigger(db: Session, trigger_id: int) -> dict:
    """Delete an auto trigger."""
    trigger = db.query(AutoTrigger).filter(AutoTrigger.id == trigger_id).first()
    if not trigger:
        return {"error": "Trigger not found"}
    name = trigger.name
    db.delete(trigger)
    db.commit()
    return {"success": True, "message": f"Trigger '{name}' deleted."}


def get_trigger_history(db: Session, trigger_id: int) -> dict:
    """Get details and fire history for a trigger."""
    trigger = db.query(AutoTrigger).filter(AutoTrigger.id == trigger_id).first()
    if not trigger:
        return {"error": "Trigger not found"}
    return {
        "id": trigger.id,
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "event_id": trigger.event_id,
        "threshold_value": trigger.threshold_value,
        "threshold_days": trigger.threshold_days,
        "action": trigger.action,
        "action_config": json.loads(trigger.action_config) if trigger.action_config else None,
        "is_active": trigger.is_active,
        "fire_count": trigger.fire_count,
        "last_fired_at": trigger.last_fired_at.isoformat() if trigger.last_fired_at else None,
        "created_at": trigger.created_at.isoformat() if trigger.created_at else None,
    }


def evaluate_triggers(db: Session) -> dict:
    """Check all active triggers and fire matching ones. Called by scheduler every hour."""
    now = datetime.now(timezone.utc)
    triggers = db.query(AutoTrigger).filter(AutoTrigger.is_active == True).all()  # noqa: E712

    fired = []
    skipped = []

    for trigger in triggers:
        # Cooldown: don't fire more than once per 24 hours
        if trigger.last_fired_at:
            lf = trigger.last_fired_at
            if lf.tzinfo is None:
                lf = lf.replace(tzinfo=timezone.utc)
            if (now - lf) < timedelta(hours=24):
                skipped.append({"id": trigger.id, "name": trigger.name, "reason": "cooldown"})
                continue

        try:
            result = _evaluate_single_trigger(db, trigger, now)
            if result.get("fired"):
                fired.append({"id": trigger.id, "name": trigger.name, "result": result})
            else:
                skipped.append({"id": trigger.id, "name": trigger.name, "reason": result.get("reason", "conditions not met")})
        except Exception as e:
            logger.error(f"Trigger {trigger.id} ({trigger.name}) evaluation failed: {e}")
            skipped.append({"id": trigger.id, "name": trigger.name, "reason": str(e)})

    return {"fired": fired, "skipped": skipped, "total_evaluated": len(triggers)}


def _evaluate_single_trigger(db: Session, trigger: AutoTrigger, now: datetime) -> dict:
    """Evaluate one trigger against current data."""
    if trigger.trigger_type == "low_sell_through":
        return _eval_low_sell_through(db, trigger, now)
    elif trigger.trigger_type == "almost_sold_out":
        return _eval_almost_sold_out(db, trigger, now)
    elif trigger.trigger_type == "post_event_followup":
        return _eval_post_event_followup(db, trigger, now)
    elif trigger.trigger_type == "new_event_alert":
        return _eval_new_event_alert(db, trigger, now)
    return {"fired": False, "reason": "unknown trigger type"}


def _eval_low_sell_through(db: Session, trigger: AutoTrigger, now: datetime) -> dict:
    """Fire if sell-through is below threshold with N days left."""
    threshold_pct = trigger.threshold_value or 30
    threshold_days = trigger.threshold_days or 7

    # Find matching events
    events_q = db.query(Event).filter(Event.status == EventStatus.SCHEDULED)
    if trigger.event_id:
        events_q = events_q.filter(Event.id == trigger.event_id)

    matching = []
    for event in events_q.all():
        try:
            event_dt = datetime.strptime(f"{event.event_date} {event.event_time or '23:59'}", "%Y-%m-%d %H:%M")
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        days_until = (event_dt - now).days
        if days_until < 0 or days_until > threshold_days:
            continue

        tiers = db.query(TicketTier).filter(TicketTier.event_id == event.id).all()
        total_avail = sum(t.quantity_available for t in tiers)
        total_sold = sum(t.quantity_sold for t in tiers)
        if total_avail == 0:
            continue

        sell_through = (total_sold / total_avail) * 100
        if sell_through < threshold_pct:
            matching.append(event)

    if not matching:
        return {"fired": False, "reason": f"No events with sell-through below {threshold_pct}% within {threshold_days} days"}

    _fire_trigger(db, trigger, matching, now)
    return {"fired": True, "events": [e.name for e in matching]}


def _eval_almost_sold_out(db: Session, trigger: AutoTrigger, now: datetime) -> dict:
    """Fire if sell-through exceeds threshold (e.g. 90%)."""
    threshold_pct = trigger.threshold_value or 90

    events_q = db.query(Event).filter(Event.status == EventStatus.SCHEDULED)
    if trigger.event_id:
        events_q = events_q.filter(Event.id == trigger.event_id)

    matching = []
    for event in events_q.all():
        try:
            event_dt = datetime.strptime(f"{event.event_date} {event.event_time or '23:59'}", "%Y-%m-%d %H:%M")
            event_dt = event_dt.replace(tzinfo=timezone.utc)
            if event_dt < now:
                continue
        except ValueError:
            continue

        tiers = db.query(TicketTier).filter(TicketTier.event_id == event.id).all()
        total_avail = sum(t.quantity_available for t in tiers)
        total_sold = sum(t.quantity_sold for t in tiers)
        if total_avail == 0:
            continue

        sell_through = (total_sold / total_avail) * 100
        if sell_through >= threshold_pct:
            matching.append(event)

    if not matching:
        return {"fired": False, "reason": f"No events above {threshold_pct}% sell-through"}

    _fire_trigger(db, trigger, matching, now)
    return {"fired": True, "events": [e.name for e in matching]}


def _eval_post_event_followup(db: Session, trigger: AutoTrigger, now: datetime) -> dict:
    """Fire for events that ended yesterday."""
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    events_q = db.query(Event).filter(Event.event_date == yesterday)
    if trigger.event_id:
        events_q = events_q.filter(Event.id == trigger.event_id)

    matching = events_q.all()
    if not matching:
        return {"fired": False, "reason": "No events ended yesterday"}

    _fire_trigger(db, trigger, matching, now)
    return {"fired": True, "events": [e.name for e in matching]}


def _eval_new_event_alert(db: Session, trigger: AutoTrigger, now: datetime) -> dict:
    """Fire for events created in the last hour."""
    one_hour_ago = now - timedelta(hours=1)

    events_q = db.query(Event).filter(
        Event.created_at >= one_hour_ago,
        Event.status == EventStatus.SCHEDULED,
    )
    if trigger.event_id:
        events_q = events_q.filter(Event.id == trigger.event_id)

    matching = events_q.all()
    if not matching:
        return {"fired": False, "reason": "No new events in the last hour"}

    _fire_trigger(db, trigger, matching, now)
    return {"fired": True, "events": [e.name for e in matching]}


def _fire_trigger(db: Session, trigger: AutoTrigger, events: list, now: datetime):
    """Execute the trigger's action for matching events."""
    config = json.loads(trigger.action_config) if trigger.action_config else {}

    for event in events:
        try:
            if trigger.action == "send_campaign":
                _fire_send_campaign(db, event, config)
            elif trigger.action == "send_promo":
                _fire_send_promo(db, event, config)
            elif trigger.action == "send_survey":
                _fire_send_survey(db, event)
        except Exception as e:
            logger.error(f"Trigger action failed for event {event.id}: {e}")

    trigger.last_fired_at = now
    trigger.fire_count = (trigger.fire_count or 0) + 1
    db.commit()


def _fire_send_campaign(db: Session, event: Event, config: dict):
    """Send a marketing campaign to past attendees or all opted-in customers."""
    from app.services.notifications import send_marketing_campaign
    from app.models import MarketingCampaign

    subject = config.get("subject", f"Don't miss {event.name}!")
    content = config.get("content", f"Tickets are going fast for {event.name} on {event.event_date}. Get yours now!")

    campaign = MarketingCampaign(
        name=f"Auto: {event.name}",
        subject=subject,
        content=content,
        target_event_id=event.id,
        target_all=not config.get("past_attendees_only", False),
        status="draft",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    send_marketing_campaign(db, campaign.id)
    logger.info(f"Auto-trigger sent campaign for event {event.id}: {event.name}")


def _fire_send_promo(db: Session, event: Event, config: dict):
    """Create and send a promo code to past attendees."""
    import secrets
    from app.models import PromoCode

    discount = config.get("discount_percent", 15)
    code = config.get("code", f"SAVE{discount}-{secrets.token_hex(3).upper()}")

    existing = db.query(PromoCode).filter(PromoCode.code == code).first()
    if not existing:
        promo = PromoCode(
            code=code,
            event_id=event.id,
            discount_percent=discount,
            max_uses=config.get("max_uses", 100),
            is_active=True,
        )
        db.add(promo)
        db.commit()

    # Send campaign about the promo
    _fire_send_campaign(db, event, {
        "subject": f"Special offer: {discount}% off {event.name}!",
        "content": f"Use code <strong>{code}</strong> for {discount}% off tickets to {event.name} on {event.event_date}. Don't miss out!",
    })
    logger.info(f"Auto-trigger created promo {code} for event {event.id}")


def _fire_send_survey(db: Session, event: Event):
    """Send post-event survey to attendees."""
    try:
        from app.services.surveys import create_survey_tokens, send_event_survey
        create_survey_tokens(db, event.id)
        send_event_survey(db, event.id)
        logger.info(f"Auto-trigger sent survey for event {event.id}: {event.name}")
    except Exception as e:
        logger.error(f"Auto-trigger survey failed for event {event.id}: {e}")


def run_trigger_evaluation_job():
    """Scheduled job: evaluate all active triggers."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        result = evaluate_triggers(db)
        fired_count = len(result.get("fired", []))
        if fired_count > 0:
            logger.info(f"Trigger evaluation: {fired_count} trigger(s) fired")
    except Exception as e:
        logger.error(f"Trigger evaluation job failed: {e}")
    finally:
        db.close()
