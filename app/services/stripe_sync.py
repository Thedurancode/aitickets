"""
Stripe Product/Price Sync Service

Automatically syncs ticket tiers to Stripe as products and prices.
This enables:
- Persistent product catalog in Stripe dashboard
- Better analytics and reporting
- Payment links from Stripe
- Consistent pricing across all channels
"""

import stripe
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models import TicketTier, Event

# Get settings
settings = get_settings()

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


def create_stripe_product_for_tier(
    db: Session,
    tier: TicketTier,
    event: Event,
) -> dict:
    """
    Create a Stripe product and price for a ticket tier.

    Returns dict with stripe_product_id and stripe_price_id.
    """
    if not settings.stripe_secret_key:
        return {"error": "Stripe not configured"}

    try:
        # Create the product
        product = stripe.Product.create(
            name=f"{event.name} - {tier.name}",
            description=tier.description or f"{tier.name} ticket for {event.name}",
            metadata={
                "event_id": str(event.id),
                "event_name": event.name,
                "event_date": event.event_date,
                "tier_id": str(tier.id),
                "tier_name": tier.name,
                "venue_id": str(event.venue_id),
            },
            images=[event.image_url] if event.image_url else [],
        )

        # Create the price
        price = stripe.Price.create(
            product=product.id,
            unit_amount=tier.price,  # Already in cents
            currency="usd",
            metadata={
                "event_id": str(event.id),
                "tier_id": str(tier.id),
            },
        )

        # Update the tier with Stripe IDs
        tier.stripe_product_id = product.id
        tier.stripe_price_id = price.id
        db.commit()

        return {
            "success": True,
            "stripe_product_id": product.id,
            "stripe_price_id": price.id,
            "product_name": product.name,
        }

    except stripe.error.StripeError as e:
        return {"error": str(e)}


def update_stripe_price_for_tier(
    db: Session,
    tier: TicketTier,
    new_price_cents: int,
) -> dict:
    """
    Update the price for a ticket tier in Stripe.

    Stripe prices are immutable, so we create a new price and archive the old one.
    """
    if not settings.stripe_secret_key:
        return {"error": "Stripe not configured"}

    if not tier.stripe_product_id:
        return {"error": "Tier not synced to Stripe yet"}

    try:
        # Archive the old price if it exists
        if tier.stripe_price_id:
            stripe.Price.modify(
                tier.stripe_price_id,
                active=False,
            )

        # Create new price
        price = stripe.Price.create(
            product=tier.stripe_product_id,
            unit_amount=new_price_cents,
            currency="usd",
            metadata={
                "event_id": str(tier.event_id),
                "tier_id": str(tier.id),
            },
        )

        # Update tier
        tier.stripe_price_id = price.id
        tier.price = new_price_cents
        db.commit()

        return {
            "success": True,
            "stripe_price_id": price.id,
            "new_price_cents": new_price_cents,
        }

    except stripe.error.StripeError as e:
        return {"error": str(e)}


def archive_stripe_product(tier: TicketTier) -> dict:
    """
    Archive a Stripe product when a tier is deleted.
    """
    if not settings.stripe_secret_key:
        return {"error": "Stripe not configured"}

    if not tier.stripe_product_id:
        return {"success": True, "message": "No Stripe product to archive"}

    try:
        # Archive the product (can't delete products with prices)
        stripe.Product.modify(
            tier.stripe_product_id,
            active=False,
        )

        # Archive the price too
        if tier.stripe_price_id:
            stripe.Price.modify(
                tier.stripe_price_id,
                active=False,
            )

        return {
            "success": True,
            "archived_product_id": tier.stripe_product_id,
        }

    except stripe.error.StripeError as e:
        return {"error": str(e)}


def sync_existing_tiers_to_stripe(db: Session, event_id: int = None) -> dict:
    """
    Sync all existing ticket tiers to Stripe.

    Useful for migrating existing data or re-syncing after issues.
    """
    if not settings.stripe_secret_key:
        return {"error": "Stripe not configured"}

    query = db.query(TicketTier).filter(TicketTier.stripe_product_id.is_(None))

    if event_id:
        query = query.filter(TicketTier.event_id == event_id)

    tiers = query.all()

    results = {
        "total": len(tiers),
        "synced": 0,
        "failed": 0,
        "details": [],
    }

    for tier in tiers:
        event = tier.event
        if not event:
            results["failed"] += 1
            results["details"].append({
                "tier_id": tier.id,
                "error": "Event not found",
            })
            continue

        result = create_stripe_product_for_tier(db, tier, event)

        if result.get("success"):
            results["synced"] += 1
            results["details"].append({
                "tier_id": tier.id,
                "tier_name": tier.name,
                "event_name": event.name,
                "stripe_product_id": result["stripe_product_id"],
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "tier_id": tier.id,
                "error": result.get("error"),
            })

    return results


def get_stripe_checkout_line_item(tier: TicketTier, quantity: int = 1) -> dict:
    """
    Get the line item for a Stripe checkout session.

    Uses the synced Stripe price if available, falls back to inline pricing.
    """
    if tier.stripe_price_id:
        # Use the synced Stripe price
        return {
            "price": tier.stripe_price_id,
            "quantity": quantity,
        }
    else:
        # Fall back to inline pricing (for tiers not yet synced)
        return {
            "price_data": {
                "currency": "usd",
                "unit_amount": tier.price,
                "product_data": {
                    "name": f"{tier.event.name} - {tier.name}",
                    "description": tier.description or f"Ticket for {tier.event.name}",
                },
            },
            "quantity": quantity,
        }
