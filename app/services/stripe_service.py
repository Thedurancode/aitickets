"""
Stripe Service Module

Simple Stripe service placeholder for the application.
"""
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class StripeService:
    """Stripe payment service."""

    def __init__(self):
        self.enabled = False  # Disabled by default for testing
        self.test_mode = True

    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        metadata: Optional[Dict] = None
    ):
        """Create a payment intent."""
        if not self.enabled:
            logger.info(f"Stripe disabled. Would create payment intent for ${amount/100}")
            return {
                "id": f"pi_test_{amount}",
                "amount": amount,
                "currency": currency,
                "status": "test"
            }

        # In production, use actual Stripe API
        logger.info(f"Creating payment intent for ${amount/100}")
        return {"id": "pi_123", "amount": amount}

    def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ):
        """Create a refund."""
        if not self.enabled:
            logger.info(f"Stripe disabled. Would refund {payment_intent_id}")
            return {"id": f"re_test_{payment_intent_id}", "status": "test"}

        # In production, use actual Stripe API
        logger.info(f"Creating refund for {payment_intent_id}")
        return {"id": "re_123", "status": "succeeded"}

    def create_transfer(
        self,
        amount: int,
        destination: str,
        metadata: Optional[Dict] = None
    ):
        """Create a transfer to connected account."""
        if not self.enabled:
            logger.info(f"Stripe disabled. Would transfer ${amount/100} to {destination}")
            return {"id": f"tr_test_{amount}", "status": "test"}

        # In production, use actual Stripe API
        logger.info(f"Transferring ${amount/100} to {destination}")
        return {"id": "tr_123", "status": "pending"}


# Global instance
stripe_service = StripeService()