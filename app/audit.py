"""
Audit Logging System

Tracks all administrative actions and critical operations for compliance and forensics.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Session

from app.database import Base
from app.models import EventGoer

logger = logging.getLogger(__name__)


class AuditLog(Base):
    """Audit log table for tracking all administrative and critical actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("event_goers.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class AuditLogger:
    """Service for creating audit log entries."""

    def __init__(self, db: Session, default_user_id: Optional[int] = None):
        """Initialize audit logger with database session and optional default user."""
        self.db = db
        self.default_user_id = default_user_id

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: Action performed (e.g., "approve_affiliate", "override_points")
            entity_type: Type of entity affected (e.g., "affiliate", "loyalty_account")
            entity_id: ID of affected entity
            user_id: ID of user who performed the action (defaults to default_user_id from constructor)
            old_value: Previous state (dict/JSON)
            new_value: New state (dict/JSON)
            ip_address: Client IP address
            user_agent: Client user agent string
            details: Additional details about the action

        Returns:
            Created AuditLog instance
        """
        try:
            # Use provided user_id or fall back to default_user_id
            effective_user_id = user_id if user_id is not None else self.default_user_id

            audit_entry = AuditLog(
                user_id=effective_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )

            self.db.add(audit_entry)
            self.db.flush()  # Get ID without committing

            logger.info(
                f"Audit log created: {action} on {entity_type}#{entity_id} by user {effective_user_id}"
            )

            return audit_entry

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Don't fail the main operation if audit logging fails
            return None

    def log_affiliate_action(
        self,
        action: str,
        affiliate_id: int,
        admin_user_id: int,
        old_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
        details: Optional[str] = None
    ):
        """Log affiliate-related administrative actions."""
        return self.log(
            action=action,
            entity_type="affiliate",
            entity_id=affiliate_id,
            user_id=admin_user_id,
            old_value=old_data,
            new_value=new_data,
            details=details
        )

    def log_points_adjustment(
        self,
        loyalty_account_id: int,
        admin_user_id: int,
        points_before: int,
        points_after: int,
        reason: str
    ):
        """Log loyalty points adjustments."""
        return self.log(
            action="adjust_points",
            entity_type="loyalty_account",
            entity_id=loyalty_account_id,
            user_id=admin_user_id,
            old_value={"points": points_before},
            new_value={"points": points_after},
            details=reason
        )

    def log_commission_change(
        self,
        affiliate_id: int,
        admin_user_id: int,
        old_rate: float,
        new_rate: float
    ):
        """Log affiliate commission rate changes."""
        return self.log(
            action="update_commission_rate",
            entity_type="affiliate",
            entity_id=affiliate_id,
            user_id=admin_user_id,
            old_value={"commission_rate": old_rate},
            new_value={"commission_rate": new_rate}
        )

    def log_group_purchase_action(
        self,
        action: str,
        group_id: int,
        user_id: int,
        details: Optional[str] = None
    ):
        """Log group purchase administrative actions."""
        return self.log(
            action=action,
            entity_type="group_purchase",
            entity_id=group_id,
            user_id=user_id,
            details=details
        )

    def log_payment_event(
        self,
        action: str,
        payment_id: str,
        user_id: Optional[int],
        amount: int,
        details: Optional[str] = None
    ):
        """Log payment-related events."""
        return self.log(
            action=action,
            entity_type="payment",
            user_id=user_id,
            new_value={"payment_id": payment_id, "amount": amount},
            details=details
        )

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int],
        ip_address: Optional[str],
        details: str
    ):
        """Log security-related events."""
        return self.log(
            action=event_type,
            entity_type="security",
            user_id=user_id,
            ip_address=ip_address,
            details=details
        )


def create_audit_logger(db: Session, user_id: Optional[int] = None) -> AuditLogger:
    """
    Factory function to create audit logger instance.

    Args:
        db: Database session
        user_id: Optional default user ID to use for all logs

    Returns:
        AuditLogger instance
    """
    return AuditLogger(db, default_user_id=user_id)


# Audit action constants
class AuditAction:
    """Constants for audit action types."""

    # Affiliate actions
    APPROVE_AFFILIATE = "approve_affiliate"
    SUSPEND_AFFILIATE = "suspend_affiliate"
    UPDATE_COMMISSION = "update_commission_rate"
    PROCESS_PAYOUT = "process_affiliate_payout"

    # Loyalty actions
    ADJUST_POINTS = "adjust_points"
    REDEEM_POINTS = "redeem_points"
    AWARD_BADGE = "award_badge"

    # Group purchase actions
    CREATE_GROUP = "create_group_purchase"
    CANCEL_GROUP = "cancel_group_purchase"
    COMPLETE_GROUP = "complete_group_purchase"

    # Payment actions
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    REFUND_ISSUED = "refund_issued"

    # Security actions
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"