"""
Unified secure token utility.

Consolidates token generation, validation, and lifecycle management
used across 7+ token systems (magic links, media sharing, surveys,
image updates, flyer templates, style pickers).

Usage::

    from app.services.secure_token import SecureToken

    # Generate
    token_value = SecureToken.generate()

    # Validate any token model
    record = SecureToken.validate(db, EventImageUpdateToken, token_value)

    # Mark one-time-use token as consumed
    SecureToken.mark_used(db, record)

    # Check if expired
    if SecureToken.is_expired(record):
        ...
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, TypeVar, Type

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SecureToken:
    """Centralised token operations for all magic-link / share-token models."""

    DEFAULT_BYTES = 32  # 256-bit tokens
    DEFAULT_EXPIRY_HOURS = 24

    @staticmethod
    def generate(nbytes: int = 32) -> str:
        """Generate a cryptographically secure URL-safe token."""
        return secrets.token_urlsafe(nbytes)

    @staticmethod
    def expiry(hours: int = 24) -> datetime:
        """Return a UTC-aware expiration datetime *hours* from now."""
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    @staticmethod
    def is_expired(record, *, field: str = "expires_at") -> bool:
        """Check whether a token record has expired.

        Handles both timezone-aware and naive datetime columns.
        """
        expires_at = getattr(record, field, None)
        if expires_at is None:
            return False  # No expiry = never expires
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= now

    @staticmethod
    def is_used(record, *, field: str = "used_at") -> bool:
        """Check whether a one-time-use token has already been consumed."""
        return getattr(record, field, None) is not None

    @classmethod
    def validate(
        cls,
        db: Session,
        model: Type[T],
        token_value: str,
        *,
        token_column: str = "token",
        check_expiry: bool = True,
        check_used: bool = True,
    ) -> Optional[T]:
        """Look up and validate a token record.

        Returns the record if valid, ``None`` if not found / expired / used.
        Works with *any* SQLAlchemy model that has a token column.
        """
        column = getattr(model, token_column, None)
        if column is None:
            raise ValueError(f"{model.__name__} has no column '{token_column}'")

        record = db.query(model).filter(column == token_value).first()
        if record is None:
            return None

        if check_expiry and cls.is_expired(record):
            return None

        if check_used and cls.is_used(record):
            return None

        return record

    @staticmethod
    def mark_used(db: Session, record, *, field: str = "used_at", commit: bool = True) -> None:
        """Stamp a one-time-use token as consumed."""
        setattr(record, field, datetime.now(timezone.utc))
        if commit:
            db.commit()

    @classmethod
    def create_and_save(
        cls,
        db: Session,
        model: Type[T],
        *,
        expires_hours: int = 24,
        token_column: str = "token",
        expiry_column: str = "expires_at",
        extra_fields: dict = None,
        commit: bool = True,
    ) -> T:
        """Create a new token record, save it, and return the instance.

        ``extra_fields`` should contain all non-token, non-expiry columns
        (e.g. ``event_id``, ``phone``).
        """
        token_value = cls.generate()
        expires_at = cls.expiry(expires_hours)

        fields = {
            token_column: token_value,
            expiry_column: expires_at,
        }
        if extra_fields:
            fields.update(extra_fields)

        record = model(**fields)
        db.add(record)
        if commit:
            db.commit()
            db.refresh(record)
        return record
