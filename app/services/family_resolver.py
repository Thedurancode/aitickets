"""
Family Resolver Service

Resolves family member references based on:
1. CustomerNotes containing family info
2. Shared ticket purchases (same event, same purchase time)
3. Email domain matching with name hints
"""

import json
import re
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import EventGoer, CustomerNote, Ticket, TicketTier, TicketStatus

logger = logging.getLogger(__name__)


def find_family_member(
    db: Session,
    customer_id: int,
    relation: str
) -> Optional[dict]:
    """
    Find a family member for a customer based on relationship type.

    Args:
        db: Database session
        customer_id: The primary customer's ID
        relation: Relationship type (wife, husband, son, daughter, etc.)

    Returns:
        Dict with family member info or None
    """
    customer = db.query(EventGoer).filter(EventGoer.id == customer_id).first()
    if not customer:
        return None

    # Strategy 1: Check customer notes for family info
    family_from_notes = _find_in_notes(db, customer_id, relation)
    if family_from_notes:
        return family_from_notes

    # Strategy 2: Find people who frequently purchase tickets with this customer
    family_from_purchases = _find_from_shared_purchases(db, customer_id, relation, customer)
    if family_from_purchases:
        return family_from_purchases

    # Strategy 3: Same email domain with relationship hints
    family_from_domain = _find_from_email_domain(db, customer, relation)
    if family_from_domain:
        return family_from_domain

    return None


def _find_in_notes(db: Session, customer_id: int, relation: str) -> Optional[dict]:
    """Search customer notes for family member references."""
    notes = db.query(CustomerNote).filter(
        CustomerNote.event_goer_id == customer_id,
        CustomerNote.note_type.in_(["family", "preference", "interaction"])
    ).all()

    # Patterns to match in notes
    relation_patterns = {
        "wife": [r"wife[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", r"married to ([A-Z][a-z]+)"],
        "husband": [r"husband[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", r"married to ([A-Z][a-z]+)"],
        "spouse": [r"spouse[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", r"partner[:\s]+([A-Z][a-z]+)"],
        "partner": [r"partner[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"],
        "son": [r"son[:\s]+([A-Z][a-z]+)", r"son named ([A-Z][a-z]+)"],
        "daughter": [r"daughter[:\s]+([A-Z][a-z]+)", r"daughter named ([A-Z][a-z]+)"],
        "child": [r"child[:\s]+([A-Z][a-z]+)", r"kid[:\s]+([A-Z][a-z]+)"],
        "brother": [r"brother[:\s]+([A-Z][a-z]+)"],
        "sister": [r"sister[:\s]+([A-Z][a-z]+)"],
        "mother": [r"mother[:\s]+([A-Z][a-z]+)", r"mom[:\s]+([A-Z][a-z]+)"],
        "father": [r"father[:\s]+([A-Z][a-z]+)", r"dad[:\s]+([A-Z][a-z]+)"],
    }

    patterns = relation_patterns.get(relation, [])

    for note in notes:
        for pattern in patterns:
            match = re.search(pattern, note.note, re.IGNORECASE)
            if match:
                name = match.group(1)
                # Try to find this person in the database
                family_member = db.query(EventGoer).filter(
                    EventGoer.name.ilike(f"%{name}%")
                ).first()

                if family_member:
                    return {
                        "id": family_member.id,
                        "name": family_member.name,
                        "email": family_member.email,
                        "relation": relation,
                        "confidence": "high",
                        "source": "customer_notes"
                    }
                else:
                    # Return just the name even if not in DB
                    return {
                        "id": None,
                        "name": name,
                        "email": None,
                        "relation": relation,
                        "confidence": "medium",
                        "source": "customer_notes"
                    }

    return None


def _find_from_shared_purchases(
    db: Session,
    customer_id: int,
    relation: str,
    customer: EventGoer
) -> Optional[dict]:
    """Find family members based on shared ticket purchases."""

    # Get events this customer has tickets for
    customer_tickets = db.query(Ticket).filter(
        Ticket.event_goer_id == customer_id,
        Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN])
    ).all()

    if not customer_tickets:
        return None

    event_ids = list(set(t.ticket_tier.event_id for t in customer_tickets))

    # Find other customers who have tickets to the same events
    # and whose tickets were created close in time
    potential_family = {}

    for ticket in customer_tickets:
        # Find tickets for same event created within 5 minutes
        nearby_tickets = db.query(Ticket).join(TicketTier).filter(
            TicketTier.event_id == ticket.ticket_tier.event_id,
            Ticket.event_goer_id != customer_id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            Ticket.created_at.between(
                ticket.created_at - func.cast('5 minutes', func.text('interval')),
                ticket.created_at + func.cast('5 minutes', func.text('interval'))
            ) if 'postgresql' in str(db.bind.url) else True  # SQLite doesn't support interval
        ).all()

        for nearby in nearby_tickets:
            other_id = nearby.event_goer_id
            if other_id not in potential_family:
                potential_family[other_id] = 0
            potential_family[other_id] += 1

    # Find person with most co-purchases
    if not potential_family:
        return None

    most_likely_id = max(potential_family.items(), key=lambda x: x[1])[0]
    co_purchase_count = potential_family[most_likely_id]

    # Need at least 2 co-purchases to be confident
    if co_purchase_count < 2:
        return None

    family_member = db.query(EventGoer).filter(EventGoer.id == most_likely_id).first()
    if not family_member:
        return None

    # Infer relation based on name patterns if not specified generically
    inferred_relation = _infer_relation(customer.name, family_member.name, relation)

    return {
        "id": family_member.id,
        "name": family_member.name,
        "email": family_member.email,
        "relation": inferred_relation or relation,
        "confidence": "medium",
        "source": "shared_purchases",
        "co_purchase_count": co_purchase_count
    }


def _find_from_email_domain(
    db: Session,
    customer: EventGoer,
    relation: str
) -> Optional[dict]:
    """Find family members based on same email domain."""
    if not customer.email or "@" not in customer.email:
        return None

    domain = customer.email.split("@")[1]

    # Skip common public domains
    public_domains = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "aol.com", "icloud.com", "mail.com", "protonmail.com"
    }
    if domain.lower() in public_domains:
        return None

    # Find others with same domain
    same_domain = db.query(EventGoer).filter(
        EventGoer.id != customer.id,
        EventGoer.email.ilike(f"%@{domain}")
    ).all()

    if not same_domain:
        return None

    # Score by name similarity or relation hints
    customer_last_name = customer.name.split()[-1].lower() if customer.name else ""

    for person in same_domain:
        person_last_name = person.name.split()[-1].lower() if person.name else ""

        # Same last name = likely family
        if customer_last_name and person_last_name == customer_last_name:
            return {
                "id": person.id,
                "name": person.name,
                "email": person.email,
                "relation": relation,
                "confidence": "low",
                "source": "email_domain"
            }

    return None


def _infer_relation(customer_name: str, other_name: str, hint: str) -> Optional[str]:
    """Try to infer relation based on names."""
    if not customer_name or not other_name:
        return hint

    # Same last name suggests spouse or sibling
    customer_parts = customer_name.split()
    other_parts = other_name.split()

    if len(customer_parts) > 1 and len(other_parts) > 1:
        if customer_parts[-1].lower() == other_parts[-1].lower():
            # Same last name - could be spouse, sibling, parent, or child
            return hint  # Use the provided hint

    return hint


def find_family_members(db: Session, customer_id: int) -> list[dict]:
    """
    Find all known family members for a customer.

    Args:
        db: Database session
        customer_id: The customer's ID

    Returns:
        List of family member dicts
    """
    relations = ["wife", "husband", "spouse", "partner", "son", "daughter", "child",
                 "brother", "sister", "mother", "father"]

    members = []
    seen_ids = set()

    for relation in relations:
        member = find_family_member(db, customer_id, relation)
        if member and member.get("id") and member["id"] not in seen_ids:
            members.append(member)
            seen_ids.add(member["id"])

    return members
