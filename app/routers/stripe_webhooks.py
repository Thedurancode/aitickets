"""
Stripe Webhook Handlers

Handles Stripe payment events for group purchases, affiliate payouts, and general payments.
"""
import logging
import os
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models_extensions import GroupPurchase, GroupContribution, GroupPurchaseStatus, AffiliatePayout
from app.audit import create_audit_logger, AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/stripe", tags=["Stripe Webhooks"])

# Stripe webhook secret - set in environment
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


async def verify_stripe_signature(request: Request) -> dict:
    """
    Verify Stripe webhook signature and parse event.

    Args:
        request: FastAPI request object

    Returns:
        Parsed Stripe event dict

    Raises:
        HTTPException: If signature verification fails
    """
    try:
        # In production, use actual Stripe library
        import stripe

        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not STRIPE_WEBHOOK_SECRET:
            logger.warning("Stripe webhook secret not configured - skipping signature verification")
            import json
            return json.loads(payload)

        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )

        return event

    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing error")


@router.post("/group-purchase")
async def handle_group_purchase_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhooks for group purchase payments.

    Processes payment_intent.succeeded and payment_intent.failed events.
    """
    event = await verify_stripe_signature(request)

    event_type = event.get("type")
    logger.info(f"Received Stripe webhook: {event_type}")

    try:
        if event_type == "payment_intent.succeeded":
            await handle_payment_success(event, db)
        elif event_type == "payment_intent.payment_failed":
            await handle_payment_failed(event, db)
        elif event_type == "charge.refunded":
            await handle_refund(event, db)
        else:
            logger.info(f"Unhandled event type: {event_type}")

        return {"success": True, "processed": event_type}

    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {e}")
        # Return 200 to prevent Stripe from retrying
        # Log the error for manual investigation
        return {"success": False, "error": str(e)}


async def handle_payment_success(event: dict, db: Session):
    """Handle successful payment_intent."""
    payment_intent = event["data"]["object"]
    payment_intent_id = payment_intent["id"]
    amount_received = payment_intent["amount_received"]

    logger.info(f"Payment succeeded: {payment_intent_id} for ${amount_received/100}")

    # Find the contribution associated with this payment
    contribution = db.query(GroupContribution).filter(
        GroupContribution.stripe_payment_intent_id == payment_intent_id
    ).first()

    if not contribution:
        logger.warning(f"No contribution found for payment intent {payment_intent_id}")
        return

    # Mark contribution as paid
    contribution.paid = True
    contribution.paid_at = datetime.utcnow()

    # Get the group purchase
    group = contribution.group_purchase

    # Recalculate group status
    total_paid = sum(
        c.amount for c in group.contributions if c.paid
    )

    group.amount_paid = total_paid
    group.amount_remaining = group.total_amount - total_paid

    if group.amount_remaining <= 0:
        group.status = GroupPurchaseStatus.COMPLETE
        group.completed_at = datetime.utcnow()

        # Trigger ticket creation
        from app.routers.group_buying import _create_group_tickets
        _create_group_tickets(group.id)

        logger.info(f"Group purchase {group.id} completed and tickets created")
    elif total_paid > 0:
        group.status = GroupPurchaseStatus.PARTIAL

    # Audit logging
    audit_logger = create_audit_logger(db)
    audit_logger.log_payment_event(
        action=AuditAction.PAYMENT_SUCCESS,
        payment_id=payment_intent_id,
        user_id=contribution.contributor_id,
        amount=amount_received,
        details=f"Group purchase {group.id} contribution"
    )

    db.commit()
    logger.info(f"Contribution {contribution.id} marked as paid")


async def handle_payment_failed(event: dict, db: Session):
    """Handle failed payment_intent."""
    payment_intent = event["data"]["object"]
    payment_intent_id = payment_intent["id"]
    failure_message = payment_intent.get("last_payment_error", {}).get("message", "Unknown error")

    logger.warning(f"Payment failed: {payment_intent_id} - {failure_message}")

    # Find the contribution
    contribution = db.query(GroupContribution).filter(
        GroupContribution.stripe_payment_intent_id == payment_intent_id
    ).first()

    if not contribution:
        logger.warning(f"No contribution found for failed payment {payment_intent_id}")
        return

    # Mark as unpaid (should already be False, but ensure)
    contribution.paid = False

    # Audit logging
    audit_logger = create_audit_logger(db)
    audit_logger.log_payment_event(
        action=AuditAction.PAYMENT_FAILED,
        payment_id=payment_intent_id,
        user_id=contribution.contributor_id,
        amount=contribution.amount,
        details=f"Payment failed: {failure_message}"
    )

    db.commit()

    # TODO: Send notification to user about failed payment
    logger.info(f"Payment failure recorded for contribution {contribution.id}")


async def handle_refund(event: dict, db: Session):
    """Handle charge.refunded event."""
    charge = event["data"]["object"]
    payment_intent_id = charge.get("payment_intent")
    refund_amount = charge["amount_refunded"]

    logger.info(f"Refund processed: {payment_intent_id} for ${refund_amount/100}")

    # Find the contribution
    contribution = db.query(GroupContribution).filter(
        GroupContribution.stripe_payment_intent_id == payment_intent_id
    ).first()

    if not contribution:
        logger.warning(f"No contribution found for refund {payment_intent_id}")
        return

    # Mark as refunded
    contribution.paid = False
    contribution.paid_at = None

    # Update group purchase
    group = contribution.group_purchase
    group.amount_paid -= contribution.amount
    group.amount_remaining += contribution.amount

    if group.status == GroupPurchaseStatus.COMPLETE:
        # Revert to partial or pending
        group.status = GroupPurchaseStatus.PARTIAL if group.amount_paid > 0 else GroupPurchaseStatus.PENDING
        group.completed_at = None

    # Audit logging
    audit_logger = create_audit_logger(db)
    audit_logger.log_payment_event(
        action=AuditAction.REFUND_ISSUED,
        payment_id=payment_intent_id,
        user_id=contribution.contributor_id,
        amount=refund_amount,
        details=f"Refund for group purchase {group.id}"
    )

    db.commit()
    logger.info(f"Refund processed for contribution {contribution.id}")


@router.post("/affiliate-payout")
async def handle_affiliate_payout_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhooks for affiliate payouts.

    Processes transfer.created and transfer.failed events.
    """
    event = await verify_stripe_signature(request)

    event_type = event.get("type")
    logger.info(f"Received affiliate payout webhook: {event_type}")

    try:
        if event_type == "transfer.created":
            await handle_transfer_created(event, db)
        elif event_type == "transfer.failed":
            await handle_transfer_failed(event, db)
        else:
            logger.info(f"Unhandled payout event type: {event_type}")

        return {"success": True, "processed": event_type}

    except Exception as e:
        logger.error(f"Error processing payout webhook {event_type}: {e}")
        return {"success": False, "error": str(e)}


async def handle_transfer_created(event: dict, db: Session):
    """Handle successful affiliate payout transfer."""
    transfer = event["data"]["object"]
    transfer_id = transfer["id"]
    amount = transfer["amount"]

    logger.info(f"Transfer created: {transfer_id} for ${amount/100}")

    # Find the payout record
    payout = db.query(AffiliatePayout).filter(
        AffiliatePayout.stripe_transfer_id == transfer_id
    ).first()

    if not payout:
        logger.warning(f"No payout found for transfer {transfer_id}")
        return

    # Mark as processed
    payout.status = "completed"
    payout.processed_at = datetime.utcnow()

    # Update affiliate's paid commission
    affiliate = payout.affiliate
    affiliate.commission_paid += payout.amount

    # Audit logging
    audit_logger = create_audit_logger(db)
    audit_logger.log(
        action=AuditAction.PROCESS_PAYOUT,
        entity_type="affiliate_payout",
        entity_id=payout.id,
        user_id=affiliate.event_goer_id,
        new_value={"amount": amount, "status": "completed"}
    )

    db.commit()
    logger.info(f"Payout {payout.id} marked as completed")


async def handle_transfer_failed(event: dict, db: Session):
    """Handle failed affiliate payout transfer."""
    transfer = event["data"]["object"]
    transfer_id = transfer["id"]
    failure_message = transfer.get("failure_message", "Unknown error")

    logger.warning(f"Transfer failed: {transfer_id} - {failure_message}")

    # Find the payout record
    payout = db.query(AffiliatePayout).filter(
        AffiliatePayout.stripe_transfer_id == transfer_id
    ).first()

    if not payout:
        logger.warning(f"No payout found for failed transfer {transfer_id}")
        return

    # Mark as failed
    payout.status = "failed"
    payout.failed_reason = failure_message

    # Restore affiliate's pending commission
    affiliate = payout.affiliate
    affiliate.commission_pending += payout.amount

    db.commit()

    # TODO: Send notification to affiliate about failed payout
    logger.info(f"Payout {payout.id} marked as failed")
