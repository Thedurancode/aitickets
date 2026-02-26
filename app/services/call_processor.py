"""
Voice Call Campaign Processor

Processes scheduled voice call campaigns by:
1. Finding calls scheduled to run
2. Initiating calls via Telnyx
3. Tracking outcomes and retrying failed calls
4. Respecting calling hours and compliance rules

Run this as a scheduled task (cron) every few minutes:
*/5 * * * * cd /path/to/ai-tickets && python -m app.services.call_processor
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, case

from app.database import SessionLocal
from app.models import VoiceCall, VoiceCallCampaign, EventGoer, CustomerNote
from app.services.voice_call import TelnyxClient, normalize_phone
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def should_call_now(campaign: VoiceCallCampaign) -> bool:
    """Check if we should be calling right now based on campaign calling hours."""
    if not campaign.start_calling_after or not campaign.stop_calling_before:
        return True  # No restrictions

    now = datetime.now(timezone.utc)

    # Parse calling hours
    try:
        start_hour, start_min = map(int, campaign.start_calling_after.split(':'))
        end_hour, end_min = map(int, campaign.stop_calling_before.split(':'))
    except ValueError:
        logger.warning(f"Invalid calling hours for campaign {campaign.id}")
        return True

    # Get current time in campaign timezone
    # For simplicity, using UTC - in production, convert to campaign timezone
    current_hour = now.hour
    current_min = now.minute

    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    current_minutes = current_hour * 60 + current_min

    return start_minutes <= current_minutes < end_minutes


def get_eligible_customers_for_campaign(campaign: VoiceCallCampaign, db):
    """Get customers who should receive calls from this campaign."""
    query = db.query(EventGoer).filter(EventGoer.phone.isnot(None), EventGoer.phone != "")

    # Exclude do-not-call
    # Check for do_not_call notes
    do_not_call_ids = db.query(EventGoer.id).join(
        EventGoer.notes
    ).filter(
        CustomerNote.note_type == "preference",
        CustomerNote.note.like("%do not call%")
    ).all()
    do_not_call_ids = [id[0] for id in do_not_call_ids]

    if do_not_call_ids:
        query = query.filter(EventGoer.id.notin_(do_not_call_ids))

    # If respecting recently called
    if campaign.skip_recently_called and campaign.skip_days_since_last_call:
        cutoff = datetime.utcnow() - timedelta(days=campaign.skip_days_since_last_call)
        recently_called = db.query(VoiceCall.event_goer_id).filter(
            VoiceCall.created_at >= cutoff,
            VoiceCall.status.in_(["completed", "answered"])
        ).distinct()
        query = query.filter(EventGoer.id.notin_(recently_called))

    # Target specific event attendees
    if campaign.target_event_id:
        from app.models import Ticket
        attendee_ids = db.query(Ticket.event_goer_id).filter(
            Ticket.event_id == campaign.target_event_id
        ).distinct()
        query = query.filter(EventGoer.id.in_(attendee_ids))

    return query.all()


def process_campaign(campaign: VoiceCallCampaign, db):
    """Process a single campaign by making pending calls."""
    logger.info(f"Processing campaign {campaign.id}: {campaign.name}")

    if not should_call_now(campaign):
        logger.info(f"Campaign {campaign.id} outside calling hours, skipping")
        return

    # Get pending calls for this campaign
    pending_calls = db.query(VoiceCall).filter(
        VoiceCall.campaign_id == campaign.id,
        VoiceCall.status.in_(["scheduled", "pending"]),
        VoiceCall.scheduled_for <= datetime.utcnow()
    ).limit(campaign.max_concurrent_calls).all()

    if not pending_calls:
        logger.info(f"No pending calls for campaign {campaign.id}")
        return

    client = TelnyxClient()

    for call in pending_calls:
        logger.info(f"Initiating call {call.id} to {call.phone_number}")

        # Update call status
        call.status = "dialing"
        call.started_at = datetime.utcnow()
        db.commit()

        # Initiate the call via Telnyx
        result = client.initiate_call_sync(
            to_phone=call.phone_number,
            text=call.call_script,
            max_duration_seconds=120,
        )

        if result.get("success"):
            call.telnyx_call_id = result.get("call_id")
            call.telnyx_status = result.get("status")
            db.commit()

            campaign.calls_initiated += 1
            logger.info(f"Call {call.id} initiated successfully: {result.get('call_id')}")
        else:
            call.status = "failed"
            call.outcome = "failed"
            campaign.calls_failed += 1
            db.commit()

            logger.error(f"Call {call.id} failed: {result.get('error')}")

        # Check if we need a delay between calls
        if campaign.time_between_calls_seconds and campaign.time_between_calls_seconds > 0:
            import time
            time.sleep(campaign.time_between_calls_seconds)

    db.commit()


def process_retry_calls(db):
    """Process calls that need to be retried."""
    now = datetime.utcnow()

    # Find calls that need retry
    retry_calls = db.query(VoiceCall).filter(
        VoiceCall.status.in_(["failed", "busy", "no_answer"]),
        VoiceCall.attempt_number < VoiceCall.max_retries,
        VoiceCall.next_retry_at <= now
    ).limit(10).all()

    client = TelnyxClient()

    for call in retry_calls:
        logger.info(f"Retrying call {call.id} (attempt {call.attempt_number + 1})")

        call.attempt_number += 1
        call.status = "dialing"
        call.started_at = now

        result = client.initiate_call_sync(
            to_phone=call.phone_number,
            text=call.call_script,
            max_duration_seconds=120,
        )

        if result.get("success"):
            call.telnyx_call_id = result.get("call_id")
            call.telnyx_status = result.get("status")
            logger.info(f"Retry call {call.id} initiated successfully")
        else:
            call.status = "failed"
            call.outcome = "failed"
            # Schedule next retry
            from app.services.voice_call import CallStatus
            campaign = db.query(VoiceCallCampaign).filter(VoiceCallCampaign.id == call.campaign_id).first()
            if campaign and call.attempt_number < call.max_retries:
                call.next_retry_at = now + timedelta(minutes=campaign.retry_delay_minutes)
            logger.error(f"Retry call {call.id} failed: {result.get('error')}")

        db.commit()


def update_campaign_stats(db):
    """Update campaign statistics based on call results."""
    campaigns = db.query(VoiceCallCampaign).filter(
        VoiceCallCampaign.status.in_(["running", "scheduled"])
    ).all()

    for campaign in campaigns:
        # Update stats
        completed_count = db.query(func.count(VoiceCall.id)).filter(
            VoiceCall.campaign_id == campaign.id,
            VoiceCall.status == "completed"
        ).scalar()

        answered_count = db.query(func.count(VoiceCall.id)).filter(
            VoiceCall.campaign_id == campaign.id,
            VoiceCall.outcome == "answered"
        ).scalar()

        failed_count = db.query(func.count(VoiceCall.id)).filter(
            VoiceCall.campaign_id == campaign.id,
            VoiceCall.status == "failed"
        ).scalar()

        total_count = db.query(func.count(VoiceCall.id)).filter(
            VoiceCall.campaign_id == campaign.id
        ).scalar()

        campaign.calls_initiated = total_count or 0
        campaign.calls_completed = completed_count or 0
        campaign.calls_answered = answered_count or 0
        campaign.calls_failed = failed_count or 0

        # Check if campaign is complete
        pending_count = db.query(func.count(VoiceCall.id)).filter(
            VoiceCall.campaign_id == campaign.id,
            VoiceCall.status.in_(["scheduled", "pending", "dialing", "in_progress"])
        ).scalar()

        if pending_count == 0 and campaign.calls_initiated > 0:
            campaign.status = "completed"
            campaign.completed_at = datetime.utcnow()
            logger.info(f"Campaign {campaign.id} marked as complete")

    db.commit()


def main():
    """Main entry point for the call processor."""
    logger.info("Starting voice call processor")

    db = SessionLocal()
    try:
        # Find campaigns to process
        campaigns = db.query(VoiceCallCampaign).filter(
            VoiceCallCampaign.status.in_(["scheduled", "running"]),
            VoiceCallCampaign.scheduled_for <= datetime.utcnow()
        ).all()

        if not campaigns:
            logger.info("No campaigns to process")
        else:
            logger.info(f"Found {len(campaigns)} campaigns to process")

            for campaign in campaigns:
                if campaign.status == "scheduled":
                    campaign.status = "running"
                    campaign.started_at = datetime.utcnow()
                    db.commit()

                try:
                    process_campaign(campaign, db)
                except Exception as e:
                    logger.error(f"Error processing campaign {campaign.id}: {e}", exc_info=True)

        # Process retries
        process_retry_calls(db)

        # Update campaign stats
        update_campaign_stats(db)

        logger.info("Voice call processor completed")

    except Exception as e:
        logger.error(f"Error in call processor: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
