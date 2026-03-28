"""
Audit Logging Service

Records sensitive operations (refunds, campaign sends, check-ins, deletions)
to an immutable audit_logs table for compliance and incident investigation.
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger(__name__)


def log_audit(
    db: Session,
    action: str,
    actor: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Write an audit log entry.

    Args:
        db: Database session.
        action: What happened, e.g. "ticket.refunded", "campaign.sent".
        actor: Who did it, e.g. "admin", "mcp", "system", "scheduler".
        resource_type: Entity type, e.g. "ticket", "event", "campaign".
        resource_id: Primary key of the affected resource.
        detail: Extra context dict (serialised to JSON).
        ip_address: Client IP if available.
    """
    entry = AuditLog(
        action=action,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=json.dumps(detail, default=str) if detail else None,
        ip_address=ip_address,
    )
    try:
        db.add(entry)
        db.flush()  # flush but don't commit — let the caller's transaction decide
    except Exception:
        logger.exception("Failed to write audit log for action=%s", action)


def get_audit_logs(
    db: Session,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Query audit logs with optional filters."""
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        q = q.filter(AuditLog.action == action)
    if actor:
        q = q.filter(AuditLog.actor == actor)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        q = q.filter(AuditLog.resource_id == resource_id)

    rows = q.offset(offset).limit(limit).all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "actor": r.actor,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "detail": json.loads(r.detail) if r.detail else None,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
