"""
Email Service Module

Simple email service placeholder for the application.
"""
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications."""

    def __init__(self):
        self.enabled = False  # Disabled by default for testing

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        attachments: Optional[List] = None
    ):
        """Send an email."""
        if not self.enabled:
            logger.info(f"Email service disabled. Would send to {to}: {subject}")
            return {"success": True, "mock": True}

        # In production, implement actual email sending here
        logger.info(f"Sending email to {to}: {subject}")
        return {"success": True}

    def send_template_email(
        self,
        to: str,
        template: str,
        context: dict,
        subject: Optional[str] = None
    ):
        """Send a templated email."""
        if not self.enabled:
            logger.info(f"Email service disabled. Would send template {template} to {to}")
            return {"success": True, "mock": True}

        # In production, render template and send
        logger.info(f"Sending template {template} to {to}")
        return {"success": True}


# Global instance
email_service = EmailService()