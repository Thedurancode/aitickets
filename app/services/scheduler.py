"""
APScheduler service for auto-reminders.

Uses APScheduler 3.x with SQLAlchemyJobStore for persistence.
Jobs survive app restarts because they are stored in the database.
"""

import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger

from app.database import SessionLocal
from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level scheduler instance (singleton)
_scheduler = None


def get_scheduler():
    """Return the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return _scheduler


def init_scheduler():
    """
    Initialize and start the APScheduler.
    Called once during FastAPI startup.
    """
    global _scheduler
    if _scheduler is not None:
        return

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    jobstores = {
        "default": SQLAlchemyJobStore(url=db_url)
    }

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 3600,
        },
        timezone="UTC",
    )
    _scheduler.start()
    logger.info("APScheduler started with SQLAlchemy job store")


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler shut down")


def _make_job_id(event_id):
    """Generate a deterministic job ID for an event's auto-reminder."""
    return f"auto_reminder_event_{event_id}"


def _compute_reminder_time(event_date, event_time, hours_before):
    """
    Compute the UTC datetime when the reminder should fire.
    event_date: "YYYY-MM-DD", event_time: "HH:MM"
    """
    event_dt = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
    event_dt = event_dt.replace(tzinfo=timezone.utc)
    return event_dt - timedelta(hours=hours_before)


def _execute_reminder(event_id, hours_before, use_sms):
    """
    The actual job function that APScheduler calls.
    Creates its own DB session (jobs run in background threads).
    """
    from app.services.notifications import send_event_reminders
    from app.models import NotificationChannel

    db = SessionLocal()
    try:
        channels = [NotificationChannel.EMAIL]
        if use_sms:
            channels.append(NotificationChannel.SMS)

        result = send_event_reminders(
            db=db,
            event_id=event_id,
            hours_before=hours_before,
            channels=channels,
        )
        logger.info(f"Auto-reminder for event {event_id}: {result}")
    except Exception as e:
        logger.error(f"Auto-reminder failed for event {event_id}: {e}")
    finally:
        db.close()


def schedule_auto_reminder(event_id, event_date, event_time, hours_before=24, use_sms=False):
    """Schedule (or reschedule) an auto-reminder job for an event."""
    scheduler = get_scheduler()
    job_id = _make_job_id(event_id)
    reminder_time = _compute_reminder_time(event_date, event_time, hours_before)
    now = datetime.now(timezone.utc)

    if reminder_time <= now:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        return {
            "event_id": event_id,
            "scheduled": False,
            "reason": "Reminder time is in the past",
            "reminder_time": reminder_time.isoformat(),
        }

    scheduler.add_job(
        _execute_reminder,
        trigger=DateTrigger(run_date=reminder_time),
        id=job_id,
        replace_existing=True,
        args=[event_id, hours_before, use_sms],
        name=f"Auto-reminder: Event {event_id} ({hours_before}h before)",
    )

    return {
        "event_id": event_id,
        "scheduled": True,
        "reminder_time": reminder_time.isoformat(),
        "hours_before": hours_before,
        "use_sms": use_sms,
        "job_id": job_id,
    }


def cancel_auto_reminder(event_id):
    """Cancel a scheduled auto-reminder for an event."""
    scheduler = get_scheduler()
    job_id = _make_job_id(event_id)
    try:
        scheduler.remove_job(job_id)
        return {"event_id": event_id, "cancelled": True}
    except Exception:
        return {"event_id": event_id, "cancelled": False, "reason": "No scheduled reminder found"}


def get_scheduled_reminders():
    """List all currently scheduled auto-reminder jobs."""
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    result = []
    for job in jobs:
        if job.id.startswith("auto_reminder_event_"):
            event_id = int(job.id.replace("auto_reminder_event_", ""))
            result.append({
                "job_id": job.id,
                "event_id": event_id,
                "scheduled_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "name": job.name,
            })
    return result


def get_reminder_for_event(event_id):
    """Get the scheduled reminder info for a specific event, or None."""
    scheduler = get_scheduler()
    job_id = _make_job_id(event_id)
    job = scheduler.get_job(job_id)
    if job:
        return {
            "job_id": job.id,
            "event_id": event_id,
            "scheduled_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "name": job.name,
        }
    return None


def bootstrap_existing_reminders():
    """
    Scan future events and schedule reminders for any that have
    auto_reminder_hours set but no existing APScheduler job.
    Called once after scheduler init.
    """
    db = SessionLocal()
    try:
        from app.models import Event, EventStatus
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        future_events = (
            db.query(Event)
            .filter(Event.auto_reminder_hours.isnot(None))
            .filter(Event.event_date >= now_str)
            .filter(Event.status == EventStatus.SCHEDULED)
            .all()
        )
        count = 0
        for event in future_events:
            existing = get_reminder_for_event(event.id)
            if not existing:
                result = schedule_auto_reminder(
                    event_id=event.id,
                    event_date=event.event_date,
                    event_time=event.event_time,
                    hours_before=event.auto_reminder_hours,
                    use_sms=event.auto_reminder_use_sms or False,
                )
                if result.get("scheduled"):
                    count += 1
        logger.info(f"Bootstrapped {count} auto-reminders for existing events")
    except Exception as e:
        logger.warning(f"Bootstrap reminders failed: {e}")
    finally:
        db.close()
